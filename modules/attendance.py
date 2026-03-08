import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn):
    # ==========================================
    # 1. CSS 정의 (가로 인쇄 최적화 및 줄바꿈 UI)
    # ==========================================
    st.markdown("""
        <style>
        /* [화면용] 표 폰트 크기 및 상세사유 줄바꿈 보조 */
        [data-testid="stDataFrame"] {
            font-size: 12px !important;
        }

        /* [인쇄 최적화] @media print */
        @media print {
            /* A4 가로 설정 및 여백 최적화 */
            @page {
                size: A4 landscape;
                margin: 10mm;
            }
            
            /* 인쇄 시 불필요한 Streamlit UI 요소 모두 숨김 */
            header, [data-testid="stHeader"], [data-testid="stSidebar"], 
            .stButton, div[data-testid="stForm"], .stTabs [role="tablist"],
            hr, [data-testid="stDecoration"], .stInfo, .stSubheader, .stTitle {
                display: none !important;
            }
            
            /* 화면용 데이터프레임 숨기고 인쇄 전용 테이블 표시 */
            div[data-testid="stDataFrame"] {
                display: none !important;
            }

            .print-only-table {
                display: table !important;
                width: 100% !important;
                border-collapse: collapse !important;
                font-size: 11px !important;
                color: black !important;
            }

            .print-only-table th, .print-only-table td {
                border: 1px solid #333 !important;
                padding: 8px !important;
                text-align: center !important;
                word-break: break-all !important;
                white-space: normal !important; /* 줄바꿈 허용 */
            }

            /* 상세사유(비고) 칸은 왼쪽 정렬 및 넓은 너비 */
            .print-only-table td.remark-cell {
                text-align: left !important;
                min-width: 250px !important;
            }

            /* 미제출 항목 강조 */
            .print-row-unsubmitted {
                background-color: #FFEBEE !important;
                -webkit-print-color-adjust: exact;
            }

            /* 인쇄 시 컨테이너 너비 제한 해제 */
            .main .block-container {
                max-width: 100% !important;
                padding: 0 !important;
            }
        }

        /* [화면용] 인쇄 전용 테이블은 평소에 숨김 */
        .print-only-table {
            display: none;
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🤖 스마트 서류 크로스체크")
    st.info("특이사항 기록 시 날짜를 바꾸면 자동으로 해당 요일의 전체 범위가 선택됩니다.")

    # 2. 데이터 로드
    try:
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[~df_students['이름'].isin(['교사', '관리자', '테스트계정'])].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{row['번호']}번 {row['이름']}" for _, row in df_students.iterrows()]

        try: df_absence_reports = conn.read(worksheet="결석명부", ttl=0)
        except: df_absence_reports = pd.DataFrame()

        try: df_special = conn.read(worksheet="출결특이사항", ttl=0)
        except: df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"])
    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}"); return

    # ---------------------------------------------------------
    # PART 1: 특이사항 기록 추가
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")

    if 'prev_date' not in st.session_state:
        st.session_state.prev_date = get_kst().date()

    target_date = st.date_input("발생 날짜 선택", value=st.session_state.prev_date)

    weekday = target_date.weekday()
    period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
    if weekday == 1: period_options.append("7교시")
    period_options.append("종례")

    if target_date != st.session_state.prev_date:
        st.session_state.slider_val = (period_options[0], period_options[-1])
        st.session_state.prev_date = target_date

    if 'slider_val' not in st.session_state:
        st.session_state.slider_val = (period_options[0], period_options[-1])

    with st.form("add_special_form", clear_on_submit=True):
        c1, c2 = st.columns([1.5, 1])
        with c1: selected_student = st.selectbox("학생 선택", student_list)
        with c2: category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과", "외출"])

        c3, c4 = st.columns([1, 2.5])
        with c3: reason_type = st.selectbox("사유", ["질병", "인정", "미인정", "기타"])
        with c4: remark = st.text_input("비고 (나이스 입력용 사유 등)", placeholder="예: 감기 증상으로 인한 병원 방문")

        st.write("")
        slider_value = (period_options[0], period_options[-1]) if category == "결석" else st.session_state.slider_val
        selected_range = st.select_slider("⏰ 교시 범위 선택", options=period_options, value=slider_value, key="range_slider")

        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            period_str = selected_range[0] if selected_range[0] == selected_range[1] else f"{selected_range[0]} ~ {selected_range[1]}"
            
            new_row = pd.DataFrame([{
                "날짜": target_date.strftime("%Y-%m-%d"), "번호": s_num, "이름": s_name,
                "종류": category, "사유": reason_type, "교시": period_str, "비고": remark
            }])
            
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.session_state.slider_val = (period_options[0], period_options[-1])
            st.cache_data.clear(); st.success("저장 완료!"); st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 서류 대조 현황 및 가로 인쇄
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 대조 현황")

    if not df_special.empty:
        # 데이터 가공
        def check_submission_robust(row, reports):
            if reports.empty: return "미제출(X)"
            try:
                target_name, target_dt = str(row['이름']).strip(), datetime.strptime(str(row['날짜']).strip(), "%Y-%m-%d")
                curr_year = target_dt.year
                student_reports = reports[reports['이름'].astype(str).str.strip() == target_name]
                if student_reports.empty: return "미제출(X)"
                for _, rep in student_reports.iterrows():
                    period = str(rep['결석기간']).strip()
                    if not period or period == 'nan': continue
                    try:
                        if '~' in period:
                            start_str, end_str = period.split('~')
                            start_dt = datetime.strptime(f"{curr_year}-{start_str.strip()}", "%Y-%m-%d")
                            end_dt = datetime.strptime(f"{curr_year}-{end_str.strip()}", "%Y-%m-%d")
                        else:
                            dt = datetime.strptime(f"{curr_year}-{period}", "%Y-%m-%d")
                            start_dt = end_dt = dt
                        if start_dt <= target_dt <= end_dt: return "제출완료(O)"
                    except: continue
                return "미제출(X)"
            except: return "미제출(X)"

        df_view = df_special.copy()
        df_view['제출여부'] = df_view.apply(lambda r: check_submission_robust(r, df_absence_reports) if r['종류'] == '결석' else "-", axis=1)
        df_view['날짜_dt'] = pd.to_datetime(df_view['날짜'])
        df_view['3/8형식'] = df_view['날짜_dt'].dt.strftime('%m/%d').str.replace('0', '', 1).str.replace('/0', '/')
        df_view['학생명'] = df_view['이름'] + "(" + df_view['번호'].astype(str).str.split('.').str[0] + ")"
        df_view['교시표시'] = df_view.apply(lambda r: "결석" if r['종류'] == '결석' else str(r['교시']).replace(" ~ ", "-"), axis=1)
        df_view['월'] = df_view['날짜_dt'].dt.month
        df_view = df_view.sort_values(by=['날짜_dt', '번호'], ascending=[False, True])
        
        display_df = df_view[["3/8형식", "학생명", "종류", "사유", "교시표시", "비고", "제출여부", "월"]]

        def style_rows(row):
            if row['제출여부'] == "미제출(X)": return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row)
            return [''] * len(row)

        month_labels = [f"{m}월" for m in range(3, 13)]
        tabs = st.tabs(month_labels)

        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                month_df = display_df[display_df['월'] == current_month].drop(columns=['월'])
                if month_df.empty:
                    st.write(f"📅 {current_month}월 기록 없음")
                else:
                    c_title, c_print = st.columns([4, 1])
                    with c_title: st.markdown(f"#### 📑 {current_month}월 출결 현황 리스트")
                    with c_print:
                        components.html(f"""
                            <button onclick="window.parent.print()" style="
                                width: 100%; padding: 8px; background-color: #1E3A8A; 
                                color: white; border: none; border-radius: 5px; cursor: pointer;
                                font-weight: bold; font-size: 12px;">🖨️ 가로 인쇄</button>
                        """, height=45)
                    
                    # --- [인쇄 전용 HTML 테이블 생성 영역] ---
                    # 상세사유 줄바꿈 및 인쇄 시 잘림 방지를 위해 HTML로 직접 테이블 생성
                    html_table = f"""
                    <div class="print-only-table-container">
                        <h2 style="text-align: center;">{current_month}월 출결 현황 및 서류 대조표</h2>
                        <table class="print-only-table">
                            <thead>
                                <tr>
                                    <th>날짜</th><th>학생명</th><th>종류</th><th>사유</th><th>교시</th><th style="width:30%">상세사유(비고)</th><th>서류</th>
                                </tr>
                            </thead>
                            <tbody>
                    """
                    for _, row in month_df.iterrows():
                        row_class = "print-row-unsubmitted" if row['제출여부'] == "미제출(X)" else ""
                        html_table += f"""
                                <tr class="{row_class}">
                                    <td>{row['3/8형식']}</td>
                                    <td>{row['학생명']}</td>
                                    <td>{row['종류']}</td>
                                    <td>{row['사유']}</td>
                                    <td>{row['교시표시']}</td>
                                    <td class="remark-cell">{row['비고']}</td>
                                    <td>{row['제출여부']}</td>
                                </tr>
                        """
                    html_table += "</tbody></table></div>"
                    st.markdown(html_table, unsafe_allow_html=True)
                    # --- [인쇄 영역 끝] ---

                    # [화면용 데이터프레임]
                    st.dataframe(
                        month_df.style.apply(style_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "3/8형식": st.column_config.TextColumn("날짜", width=40),
                            "학생명": st.column_config.TextColumn("학생명", width=80),
                            "교시표시": st.column_config.TextColumn("교시", width=80),
                            "제출여부": st.column_config.TextColumn("서류", width=70),
                            "비고": st.column_config.TextColumn("상세사유(비고)", width="large")
                        }
                    )
        
        with st.expander("🗑️ 기록 초기화"):
            if st.button("전체 삭제"):
                conn.update(worksheet="출결특이사항", data=pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"]))
                st.cache_data.clear(); st.rerun()
