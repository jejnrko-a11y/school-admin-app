import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn):
    # ==========================================
    # 1. 인쇄 최적화 핵심 CSS (선택자 정밀 수정)
    # ==========================================
    st.markdown("""
        <style>
        /* 화면용: 표 글자 크기 및 비고란 가독성 */
        [data-testid="stDataFrame"] {
            font-size: 13px !important;
        }
        
        @media print {
            /* 1. 용지 설정 (A4 가로 방향) */
            @page {
                size: A4 landscape;
                margin: 15mm 10mm 10mm 10mm;
            }

            /* 2. 인쇄 시 불필요한 Streamlit 기본 UI 제거 */
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer, [data-testid="stDecoration"] {
                display: none !important;
            }

            /* 3. [핵심] "월별 서류 현황" 이전의 모든 요소를 개별적으로 숨김 */
            /* 메인 타이틀, 안내 박스, 입력 폼, 구분선(hr), 날짜 입력 위젯 */
            [data-testid="stTitle"], 
            [data-testid="stNotification"], 
            [data-testid="stForm"], 
            [data-testid="stDivider"],
            [data-testid="stDateInput"],
            .stButton {
                display: none !important;
            }

            /* 4. 특정 텍스트를 포함한 컨테이너(기록 추가 섹션) 숨김 */
            /* "기록 추가"라는 글자가 들어간 모든 요소를 인쇄에서 제외 */
            div.element-container:has(h3:contains("기록 추가")),
            div.element-container:has(h3:contains("➕")),
            div.element-container:has(label:contains("발생 날짜 선택")) {
                display: none !important;
            }

            /* 5. 탭 메뉴 버튼(3월, 4월...) 숨김 - 선택된 내용만 나오게 함 */
            .stTabs [role="tablist"] {
                display: none !important;
            }

            /* 6. 인쇄 레이아웃 확장 */
            .main .block-container {
                max-width: 100% !important;
                padding-top: 0 !important;
                margin-top: 0 !important;
            }

            /* 데이터프레임이 잘리지 않고 전체 너비를 사용하도록 설정 */
            div[data-testid="stDataFrame"] {
                width: 100% !important;
            }
            
            /* 배경색 및 미제출 강조색 유지 */
            * {
                -webkit-print-color-adjust: exact !important;
                print-color-adjust: exact !important;
            }
        }
        </style>
    """, unsafe_allow_html=True)

    # 상단부 (인쇄 시 숨겨짐)
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
        st.error(f"데이터 로드 실패: {e}"); return

    # ---------------------------------------------------------
    # PART 1: 기록 추가 (인쇄 시 숨겨짐)
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
        with c4: remark = st.text_input("비고 (나이스용)", placeholder="사유 입력")

        slider_value = (period_options[0], period_options[-1]) if category == "결석" else st.session_state.slider_val
        selected_range = st.select_slider("⏰ 교시", options=period_options, value=slider_value)

        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            p_str = selected_range[0] if selected_range[0] == selected_range[1] else f"{selected_range[0]} ~ {selected_range[1]}"
            
            new_row = pd.DataFrame([{"날짜": target_date.strftime("%Y-%m-%d"), "번호": s_num, "이름": s_name, "종류": category, "사유": reason_type, "교시": p_str, "비고": remark}])
            updated_special = pd.concat([df_special, new_row], ignore_index=True).sort_values(by=['날짜', '번호'], ascending=[True, True])
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.session_state.slider_val = (period_options[0], period_options[-1]) 
            st.cache_data.clear(); st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 서류 현황 (여기서부터 인쇄 시작)
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 현황")

    if not df_special.empty:
        # 가공 로직
        def check_sub(row, reports):
            if reports.empty: return "미제출(X)"
            try:
                name, dt = str(row['이름']).strip(), datetime.strptime(str(row['날짜']).strip(), "%Y-%m-%d")
                curr_year = dt.year
                r_filtered = reports[reports['이름'].astype(str).str.strip() == name]
                for _, r in r_filtered.iterrows():
                    period = str(r['결석기간']).strip()
                    if '~' in period:
                        s, e = period.split('~')
                        sd, ed = datetime.strptime(f"{curr_year}-{s.strip()}", "%Y-%m-%d"), datetime.strptime(f"{curr_year}-{e.strip()}", "%Y-%m-%d")
                        if sd <= dt <= ed: return "제출완료(O)"
                    else:
                        if datetime.strptime(f"{curr_year}-{period}", "%Y-%m-%d") == dt: return "제출완료(O)"
                return "미제출(X)"
            except: return "미제출(X)"

        df_view = df_special.copy()
        df_view['제출여부'] = df_view.apply(lambda r: check_sub(r, df_absence_reports) if r['종류'] == '결석' else "-", axis=1)
        df_view['날짜_dt'] = pd.to_datetime(df_view['날짜'])
        df_view['날짜'] = df_view['날짜_dt'].dt.strftime('%m/%d').str.replace('0', '', 1).str.replace('/0', '/')
        df_view['학생명'] = df_view['이름'] + "(" + df_view['번호'].astype(str).str.split('.').str[0] + ")"
        df_view['교시'] = df_view.apply(lambda r: "결석" if r['종류'] == '결석' else str(r['교시']).replace(" ~ ", "~"), axis=1)
        df_view['비고'] = df_view['비고'].fillna('')
        df_view['월'] = df_view['날짜_dt'].dt.month
        df_view = df_view.sort_values(by=['날짜_dt', '번호'], ascending=[True, True])
        
        display_df = df_view[["날짜", "학생명", "종류", "사유", "교시", "비고", "제출여부", "월"]]

        def style_r(row):
            return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row) if row['제출여부'] == "미제출(X)" else [''] * len(row)

        tabs = st.tabs([f"{m}월" for m in range(3, 13)])
        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                m_df = display_df[display_df['월'] == current_month].drop(columns=['월'])
                if m_df.empty:
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
                        m_df.style.apply(style_r, axis=1),
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
