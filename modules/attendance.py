import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn):
    st.title("🤖 스마트 서류 크로스체크")
    st.info("특이사항을 기록하면 학생들이 제출한 결석계와 대조하여 서류 제출 여부를 실시간 판별합니다.")

    # 1. 데이터 로드 및 전처리
    try:
        # 학생명부 로드 (관리자 계정 제외 및 번호 정렬)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[~df_students['이름'].isin(['교사', '관리자', '테스트계정'])].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{row['번호']}번 {row['이름']}" for _, row in df_students.iterrows()]

        # 결석명부 (학생들이 제출한 증빙 데이터)
        try:
            df_absence_reports = conn.read(worksheet="결석명부", ttl=0)
        except:
            df_absence_reports = pd.DataFrame()

        # 출결특이사항 (교사가 직접 기록한 데이터)
        try:
            df_special = conn.read(worksheet="출결특이사항", ttl=0)
        except:
            df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"])

    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (상단 고정 입력부)
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")

    # [교시 리스트 생성 로직] 요일별 자동 반영 (화요일 7교시 그외 6교시)
    # 현재 선택된 날짜 기준으로 옵션을 미리 계산하여 세션 상태와 연동
    temp_date = get_kst().date()
    weekday_init = temp_date.weekday()
    period_options_init = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
    if weekday_init == 1: period_options_init.append("7교시")
    period_options_init.append("종례")

    # [상태 관리] 슬라이더 기본값을 '조회 ~ 종례' 전체로 고정
    if 'slider_val' not in st.session_state:
        st.session_state.slider_val = (period_options_init[0], period_options_init[-1])

    with st.form("add_special_form", clear_on_submit=True):
        # [첫 번째 줄] 기본 정보 (3열)
        r1_c1, r1_c2, r1_c3 = st.columns([1, 1.5, 1.2])
        with r1_c1:
            target_date = st.date_input("발생 날짜", value=temp_date)
        with r1_c2:
            selected_student = st.selectbox("학생 선택", student_list)
        with r1_c3:
            category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과", "외출"])

        # [두 번째 줄] 사유 및 비고 (2열)
        r2_c1, r2_c2 = st.columns([1, 2.7])
        with r2_c1:
            reason_type = st.selectbox("사유", ["질병", "인정", "미인정", "기타"])
        with r2_c2:
            remark = st.text_input("비고 (상세 사유 등)", placeholder="행정 기록용 사유를 입력하세요.")

        # [세 번째 줄] 교시 슬라이더 (범위 선택)
        st.write("")
        st.markdown("##### ⏰ 교시(시간) 범위 선택")
        
        # 날짜 변경에 따른 옵션 재계산
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
        period_options.append("종례")

        # 종류가 '결석'일 경우 자동으로 전체 범위 지정, 아닐 경우 세션 상태 유지
        current_slider_val = (period_options[0], period_options[-1]) if category == "결석" else st.session_state.slider_val

        selected_range = st.select_slider(
            "마우스로 범위를 드래그하세요",
            options=period_options,
            value=current_slider_val,
            key="range_slider_widget"
        )

        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            
            # 범위 데이터 포맷팅
            if selected_range[0] == selected_range[1]:
                period_str = selected_range[0]
            else:
                period_str = f"{selected_range[0]} ~ {selected_range[1]}"
            
            new_row = pd.DataFrame([{
                "날짜": target_date.strftime("%Y-%m-%d"),
                "번호": s_num, "이름": s_name,
                "종류": category, "사유": reason_type, 
                "교시": period_str, "비고": remark
            }])
            
            # 데이터 업데이트
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            conn.update(worksheet="출결특이사항", data=updated_special)
            
            # 성공 후 상태 초기화 및 페이지 리프레시
            st.session_state.slider_val = (period_options[0], period_options[-1])
            st.cache_data.clear()
            st.success(f"✅ {s_name} 학생 기록이 추가되었습니다.")
            st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 서류 대조 현황 및 인쇄 (관리자 UI)
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 대조 현황")

    if df_special.empty:
        st.info("기록된 특이사항이 아직 없습니다.")
    else:
        # [Helper] 자동 판별 함수
        def check_submission_robust(row, reports):
            if reports.empty: return "미제출(X)"
            try:
                target_name = str(row['이름']).strip()
                target_dt = datetime.strptime(str(row['날짜']).strip(), "%Y-%m-%d")
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

        # [Pandas 데이터 가공]
        df_view = df_special.copy()
        
        # 1. 제출여부 판별 (결석일 때만 체크)
        df_view['제출여부'] = df_view.apply(
            lambda r: check_submission_robust(r, df_absence_reports) if r['종류'] == '결석' else "-", axis=1
        )
        
        # 2. 날짜/이름 포맷팅
        df_view['날짜_dt'] = pd.to_datetime(df_view['날짜'])
        df_view['표시날짜'] = df_view['날짜_dt'].dt.strftime('%m/%d').str.replace('0', '', 1).str.replace('/0', '/')
        df_view['이름(번호)'] = df_view['이름'] + "(" + df_view['번호'].astype(str).str.split('.').str[0] + ")"
        
        # 3. 교시 포맷팅
        df_view['교시표시'] = df_view.apply(
            lambda r: "결석" if r['종류'] == '결석' else str(r['교시']).replace(" ~ ", "-"), axis=1
        )
        
        # 4. 정렬 및 컬럼 구성
        df_view['월'] = df_view['날짜_dt'].dt.month
        df_view = df_view.sort_values(by=['날짜_dt', '번호'], ascending=[False, True])
        display_df = df_view[["표시날짜", "이름(번호)", "종류", "사유", "교시표시", "비고", "제출여부", "월"]]

        # [Style] 미제출 빨간색 강조
        def style_rows(row):
            if row['제출여부'] == "미제출(X)":
                return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row)
            return [''] * len(row)

        # [탭 렌더링]
        month_labels = [f"{m}월" for m in range(3, 13)]
        tabs = st.tabs(month_labels)

        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                month_df = display_df[display_df['월'] == current_month].drop(columns=['월'])
                
                if month_df.empty:
                    st.info(f"📅 {current_month}월에 기록된 특이사항이 없습니다.")
                else:
                    # 인쇄 헤더 및 버튼
                    c_title, c_print = st.columns([4, 1])
                    with c_title:
                        st.markdown(f"#### 📑 {current_month}월 서류 대조 및 출결 현황")
                    with c_print:
                        components.html("""
                            <button onclick="window.print()" style="
                                width: 100%; padding: 8px; background-color: #1E3A8A; 
                                color: white; border: none; border-radius: 5px; cursor: pointer;
                                font-weight: bold; font-size: 13px;">🖨️ 현황 인쇄</button>
                        """, height=45)
                    
                    # 테이블 출력
                    st.dataframe(
                        month_df.style.apply(style_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "표시날짜": st.column_config.TextColumn("날짜", width="small"),
                            "이름(번호)": st.column_config.TextColumn("학생명", width="medium"),
                            "제출여부": st.column_config.TextColumn("📑 서류제출", width="medium"),
                            "비고": st.column_config.TextColumn("상세 사유", width="large")
                        }
                    )
        
        # 관리 기능
        with st.expander("🗑️ 데이터 관리"):
            if st.button("출결 기록 전체 초기화 (주의)"):
                empty_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"])
                conn.update(worksheet="출결특이사항", data=empty_df)
                st.cache_data.clear()
                st.success("데이터가 초기화되었습니다.")
                st.rerun()
