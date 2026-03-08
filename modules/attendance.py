import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn):
    # ==========================================
    # 1. 인쇄 최적화 및 UI 개선 CSS
    # ==========================================
    st.markdown("""
        <style>
        /* [기본 UI] 표 글자 크기 조정 */
        [data-testid="stDataFrame"] {
            font-size: 13px !important;
        }
        
        /* [인쇄 최적화] @media print */
        @media print {
            /* 1. 용지 설정 (A4 가로 방향) */
            @page {
                size: A4 landscape;
                margin: 15mm 10mm 10mm 10mm;
            }

            /* 2. 인쇄 시 불필요한 모든 상단 요소 숨김 */
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer, [data-testid="stDecoration"] {
                display: none !important;
            }

            /* 타이틀, 안내문구(Notification), 폼(Form), 날짜입력, 구분선 숨김 */
            [data-testid="stTitle"], 
            [data-testid="stNotification"], 
            [data-testid="stForm"], 
            [data-testid="stDateInput"],
            [data-testid="stDivider"],
            .stButton {
                display: none !important;
            }

            /* 첫 번째 소제목 (+ 기록 추가) 숨김 */
            /* 월별 서류 현황 제목은 살리기 위해 정밀하게 선택 */
            div[data-testid="stVerticalBlock"] > div:nth-child(1),
            div[data-testid="stVerticalBlock"] > div:nth-child(2),
            div[data-testid="stVerticalBlock"] > div:nth-child(3),
            div[data-testid="stVerticalBlock"] > div:nth-child(4),
            div[data-testid="stVerticalBlock"] > div:nth-child(5) {
                display: none !important;
            }

            /* 탭 메뉴의 버튼바(3월, 4월...) 숨김 - 표 내용만 출력 */
            .stTabs [role="tablist"] {
                display: none !important;
            }

            /* 3. 인쇄용 표 스타일 (내용이 잘리지 않게 설정) */
            .main .block-container {
                max-width: 100% !important;
                padding: 0 !important;
                margin: 0 !important;
            }

            /* 비고란 내용이 길어도 줄바꿈되어 다 보이도록 설정 */
            div[data-testid="stDataFrame"] {
                width: 100% !important;
                height: auto !important;
            }
            
            /* 표 배경색 유지 */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("🤖 출석체크")
    st.info("특이사항을 기록하면 학생들이 제출한 결석계와 대조하여 서류 제출 여부를 실시간 판별합니다.")

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
    st.subheader("➕ 기록 추가")

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
        with c4: remark = st.text_input("비고 (상세 사유 등)", placeholder="예: 감기 증상으로 인한 병원 방문")

        st.write("")
        slider_value = (period_options[0], period_options[-1]) if category == "결석" else st.session_state.slider_val
        selected_range = st.select_slider("⏰ 교시 선택", options=period_options, value=slider_value)

        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            period_str = selected_range[0] if selected_range[0] == selected_range[1] else f"{selected_range[0]}-{selected_range[1]}"
            
            new_row = pd.DataFrame([{
                "날짜": target_date.strftime("%Y-%m-%d"), "번호": s_num, "이름": s_name,
                "종류": category, "사유": reason_type, "교시": period_str, "비고": remark
            }])
            
            # 최신 날짜가 아래로 가도록 저장
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            updated_special = updated_special.sort_values(by=['날짜', '번호'], ascending=[True, True])
            
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.session_state.slider_val = (period_options[0], period_options[-1]) 
            st.cache_data.clear(); st.success(f"✅ {s_name} 학생 추가 완료!"); st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 서류 현황 (인쇄 섹션)
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 현황")

    if df_special.empty:
        st.info("기록된 특이사항이 없습니다.")
    else:
        # 가공 로직
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
        df_view['날짜'] = df_view['날짜_dt'].dt.strftime('%m/%d').str.replace('0', '', 1).str.replace('/0', '/')
        df_view['학생명'] = df_view['이름'] + "(" + df_view['번호'].astype(str).str.split('.').str[0] + ")"
        df_view['교시'] = df_view.apply(lambda r: "결석" if r['종류'] == '결석' else str(r['교시']), axis=1)
        df_view['비고'] = df_view['비고'].fillna('') # 이미지에 보이던 'None' 제거
        df_view['월'] = df_view['날짜_dt'].dt.month
        
        # 날짜순 정렬 (최신이 아래)
        df_view = df_view.sort_values(by=['날짜_dt', '번호'], ascending=[True, True])
        
        display_df = df_view[["날짜", "학생명", "종류", "사유", "교시", "비고", "제출여부", "월"]]

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
                                font-weight: bold; font-size: 12px;">🖨️ 인쇄</button>
                        """, height=45)
                    
                    st.dataframe(
                        month_df.style.apply(style_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "날짜": st.column_config.TextColumn("날짜", width=45),
                            "학생명": st.column_config.TextColumn("학생명", width=85),
                            "종류": st.column_config.TextColumn("종류", width=50),
                            "교시": st.column_config.TextColumn("교시", width=85),
                            "제출여부": st.column_config.TextColumn("서류", width=70),
                            "비고": st.column_config.TextColumn("상세사유(비고)", width="large")
                        }
                    )
        
        with st.expander("🗑️ 기록 초기화"):
            if st.button("전체 삭제"):
                conn.update(worksheet="출결특이사항", data=pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"]))
                st.cache_data.clear(); st.rerun()
