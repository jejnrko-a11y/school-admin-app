import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn):
    # ==========================================
    # 1. 고도화된 인쇄 및 UI 스타일 정의 (CSS)
    # ==========================================
    st.markdown("""
        <style>
        /* [전체 화면 설정] */
        .main .block-container { padding-top: 2rem; }

        /* [인쇄 전용 스타일] */
        @media print {
            /* A4 가로 설정 및 여백 최적화 */
            @page { 
                size: A4 landscape; 
                margin: 10mm; 
            }
            
            /* 인쇄 시 숨길 항목들 (제목, 폼, 사이드바, 탭, 버튼 등) */
            header, [data-testid="stHeader"], [data-testid="stSidebar"], 
            [data-testid="stForm"], .stTabs [role="tablist"], 
            .stButton, .stInfo, .stTitle, hr, [data-testid="stDecoration"] {
                display: none !important;
            }

            /* 배경색 및 텍스트 색상 유지 */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }

            /* 인쇄용 컨테이너 확장 */
            .main .block-container {
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            /* 인쇄용 표 디자인 */
            .print-table {
                width: 100% !important;
                border-collapse: collapse !important;
                font-size: 11px !important;
                table-layout: fixed !important; /* 너비 고정 */
            }
            .print-table th {
                background-color: #f0f2f6 !important;
                border: 1px solid #000 !important;
                padding: 8px !important;
                font-weight: bold !important;
                text-align: center !important;
            }
            .print-table td {
                border: 1px solid #000 !important;
                padding: 6px !important;
                word-break: keep-all !important; /* 단어 단위 줄바꿈 */
                white-space: normal !important; /* 자동 높이 조절 핵심 */
                vertical-align: middle !important;
            }
            
            /* 컬럼별 너비 지정 (인쇄용) */
            .col-date { width: 45px; text-align: center; }
            .col-name { width: 85px; text-align: center; }
            .col-type { width: 50px; text-align: center; }
            .col-reason { width: 50px; text-align: center; }
            .col-period { width: 80px; text-align: center; }
            .col-remark { width: auto; } /* 비고란은 유동적 */
            .col-doc { width: 65px; text-align: center; }

            /* 미제출 빨간색 강조 */
            .unsubmitted { background-color: #FFEBEE !important; color: #D32F2F !important; font-weight: bold !important; }
        }
        
        /* [화면용 스타일] */
        .print-only-title { display: none; }
        @media print {
            .print-only-title { display: block; text-align: center; margin-bottom: 20px; }
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
        st.error(f"데이터 로드 실패: {e}"); return

    # ---------------------------------------------------------
    # PART 1: 특이사항 기록 추가 (자동 초기화 및 슬라이더)
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")

    if 'prev_date' not in st.session_state:
        st.session_state.prev_date = get_kst().date()

    target_date = st.date_input("발생 날짜 선택", value=st.session_state.prev_date)

    # 요일/옵션 계산
    weekday = target_date.weekday()
    period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
    if weekday == 1: period_options.append("7교시")
    period_options.append("종례")

    # 날짜 변경 시 슬라이더 리셋
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
        with c4: remark = st.text_input("비고 (나이스 입력용 사유 등)", placeholder="예: 병원 진료로 인한 3~4교시 외출")

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
            
            conn.update(worksheet="출결특이사항", data=pd.concat([df_special, new_row], ignore_index=True))
            st.session_state.slider_val = (period_options[0], period_options[-1])
            st.cache_data.clear(); st.success("성공적으로 저장되었습니다."); st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 서류 대조 현황 (인쇄 및 가로 최적화)
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 대조 현황")

    if not df_special.empty:
        # [데이터 가공]
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
        df_view['날짜(3/8)'] = df_view['날짜_dt'].dt.strftime('%m/%d').str.replace('0', '', 1).str.replace('/0', '/')
        df_view['학생명(번호)'] = df_view['이름'] + "(" + df_view['번호'].astype(str).str.split('.').str[0] + ")"
        df_view['교시표시'] = df_view.apply(lambda r: "결석" if r['종류'] == '결석' else str(r['교시']).replace(" ~ ", "-"), axis=1)
        df_view['월'] = df_view['날짜_dt'].dt.month
        df_view = df_view.sort_values(by=['날짜_dt', '번호'], ascending=[False, True])
        
        display_df = df_view[["날짜(3/8)", "학생명(번호)", "종류", "사유", "교시표시", "비고", "제출여부", "월"]]

        tabs = st.tabs([f"{m}월" for m in range(3, 13)])
        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                month_df = display_df[display_df['월'] == current_month].drop(columns=['월'])
                if month_df.empty:
                    st.write(f"📅 {current_month}월 기록 없음")
                else:
                    # 인쇄 버튼 및 헤더
                    c_title, c_print = st.columns([4, 1])
                    with c_title: st.markdown(f"#### 📑 {current_month}월 출결 현황 리스트")
                    with c_print:
                        components.html("""
                            <button onclick="window.parent.print()" style="
                                width: 100%; padding: 8px; background-color: #1E3A8A; 
                                color: white; border: none; border-radius: 5px; cursor: pointer;
                                font-weight: bold; font-size: 13px;">🖨️ 현황 인쇄</button>
                        """, height=45)
                    
                    # [인쇄용 HTML 생성] - 비고란 자동 높이 조절을 위해 인쇄 시에는 HTML 테이블로 대체
                    html_table = f"<div class='print-only-title'><h2>📅 {current_month}월 출결 및 서류 대조 현황</h2></div>"
                    html_table += "<table class='print-table'><thead><tr>"
                    html_table += "<th class='col-date'>날짜</th><th class='col-name'>학생명(번호)</th><th class='col-type'>종류</th>"
                    html_table += "<th class='col-reason'>사유</th><th class='col-period'>교시</th><th class='col-remark'>상세사유(비고)</th><th class='col-doc'>서류</th></tr></thead><tbody>"
                    
                    for _, row in month_df.iterrows():
                        row_class = "unsubmitted" if row['제출여부'] == "미제출(X)" else ""
                        html_table += f"<tr class='{row_class}'>"
                        html_table += f"<td class='col-date'>{row['날짜(3/8)']}</td><td class='col-name'>{row['학생명(번호)']}</td>"
                        html_table += f"<td class='col-type'>{row['종류']}</td><td class='col-reason'>{row['사유']}</td>"
                        html_table += f"<td class='col-period'>{row['교시표시']}</td><td class='col-remark'>{row['비고']}</td>"
                        html_table += f"<td class='col-doc'>{row['제출여부']}</td></tr>"
                    html_table += "</tbody></table>"
                    
                    # 화면에는 Streamlit DataFrame, 인쇄 시에는 위 HTML이 보이도록 처리
                    st.markdown(f"<div class='print-only'>{html_table}</div>", unsafe_allow_html=True)
                    
                    # 화면용 테이블 (정교한 설정)
                    st.dataframe(
                        month_df,
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "날짜(3/8)": st.column_config.TextColumn("날짜", width=45),
                            "학생명(번호)": st.column_config.TextColumn("학생명(번호)", width=90),
                            "교시표시": st.column_config.TextColumn("교시", width=90),
                            "제출여부": st.column_config.TextColumn("서류", width=70),
                            "비고": st.column_config.TextColumn("상세사유(비고)")
                        }
                    )
