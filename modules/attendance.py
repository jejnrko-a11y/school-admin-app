import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("🤖 스마트 서류 크로스체크")
    st.info("특이사항을 기록하면 학생들이 제출한 결석계와 대조하여 서류 제출 여부를 실시간 판별합니다.")

    # 1. 데이터 로드 및 전처리
    try:
        # 학생명부 로드 및 번호 정수화
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
            # 컬럼이 없을 경우 초기화 (신규 '교시' 컬럼 포함)
            df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "교시", "비고"])

    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (상단 고정 입력부) - 슬라이더 업그레이드
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")

    # [로직] '종류' 선택에 따른 슬라이더 자동 설정을 위해 폼 외부 또는 세션 상태 활용
    if 'temp_category' not in st.session_state:
        st.session_state.temp_category = "결석"

    with st.form("add_special_form", clear_on_submit=True):
        # [첫 번째 줄] 기본 정보 (3열)
        r1_c1, r1_c2, r1_c3 = st.columns([1, 1.5, 1.2])
        with r1_c1:
            target_date = st.date_input("발생 날짜", value=get_kst().date())
        with r1_c2:
            selected_student = st.selectbox("학생 선택", student_list)
        with r1_c3:
            # 종류 선택 (결석 선택 시 로직 처리를 위해 변수 저장)
            category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과", "외출"], key="category_select")

        # [교시 리스트 생성]
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
        period_options.append("종례")

        # [두 번째 줄] 사유 및 비고 (2열)
        r2_c1, r2_c2 = st.columns([1, 2.7])
        with r2_c1:
            reason_type = st.selectbox("사유", ["질병", "인정", "미인정", "기타"])
        with r2_c2:
            remark = st.text_input("비고 (상세 사유 등)", placeholder="사유를 상세히 입력하세요.")

        st.write("") # 간격 조절
        st.markdown("##### ⏰ 교시(시간) 범위 선택")
        
        # [슬라이더 자동 설정 로직]
        # '결석'일 경우 전체 범위[조회~종례], 아닐 경우 기본값[조회] 혹은 마지막 선택 유지
        slider_default = (period_options[0], period_options[-1]) if category == "결석" else (period_options[0], period_options[0])
        
        # [세 번째 줄] 교시 슬라이더 (너비 확보를 위해 단독 배치 또는 넓은 컬럼)
        selected_range = st.select_slider(
            "마우스로 드래그하여 범위를 선택하세요",
            options=period_options,
            value=slider_default,
            help="'결석' 선택 시 자동으로 전체 범위가 지정됩니다."
        )

        # 제출 버튼
        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            
            # 범위 데이터 처리 (시작~종료)
            if selected_range[0] == selected_range[1]:
                period_str = selected_range[0] # 단일 교시
            else:
                period_str = f"{selected_range[0]} ~ {selected_range[1]}" # 범위 표시
            
            new_row = pd.DataFrame([{
                "날짜": target_date.strftime("%Y-%m-%d"),
                "번호": s_num, "이름": s_name,
                "종류": category, "사유": reason_type, 
                "교시": period_str, "비고": remark
            }])
            
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.success(f"✅ {s_name} 학생 기록 추가 완료 ({period_str})")
            st.cache_data.clear()
            st.rerun()

    # ---------------------------------------------------------
    # PART 2: 월별 탭 구성 및 자동 판별 (하단 확인부)
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
                        
                        if start_dt <= target_dt <= end_dt:
                            return "제출완료(O)"
                    except: continue
                return "미제출(X)"
            except: return "미제출(X)"

        # [Helper] 미제출 하이라이트 스타일
        def style_rows(row):
            if row['서류제출'] == "미제출(X)":
                return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row)
            return [''] * len(row)

        # 데이터 가공
        df_processed = df_special.copy()
        df_processed['번호'] = pd.to_numeric(df_processed['번호'], errors='coerce').fillna(0).astype(int)
        
        with st.spinner("서류 대조 중..."):
            df_processed['서류제출'] = df_processed.apply(lambda r: check_submission_robust(r, df_absence_reports), axis=1)
            df_processed['월'] = pd.to_datetime(df_processed['날짜']).dt.month
        
        # 월별 탭 생성
        month_labels = [f"{m}월" for m in range(3, 13)]
        tabs = st.tabs(month_labels)

        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                month_df = df_processed[df_processed['월'] == current_month].copy()
                
                if month_df.empty:
                    st.write(f"📅 {current_month}월에 기록된 특이사항이 없습니다.")
                else:
                    month_df = month_df.sort_values(by=['날짜', '번호'], ascending=[False, True])
                    
                    # '교시' 컬럼을 포함하여 표시
                    display_cols = ["날짜", "번호", "이름", "종류", "사유", "교시", "서류제출", "비고"]
                    
                    st.dataframe(
                        month_df[display_cols].style.apply(style_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "번호": st.column_config.NumberColumn("번호", format="%d", width="small"),
                            "날짜": st.column_config.TextColumn("날짜", width="medium"),
                            "교시": st.column_config.TextColumn("⏰ 교시", width="medium"),
                            "서류제출": st.column_config.TextColumn("📑 제출여부", width="medium"),
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
