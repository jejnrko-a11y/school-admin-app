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
    # PART 1: 특이사항 학생 추가 (상단 고정 입력부) - UI 최적화 버전
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")
    with st.form("add_special_form", clear_on_submit=True):
        # [첫 번째 줄] 기본 정보 입력 (3열 구성)
        r1_c1, r1_c2, r1_c3 = st.columns([1, 1.5, 1])
        with r1_c1:
            target_date = st.date_input("발생 날짜", value=get_kst().date())
        with r1_c2:
            selected_student = st.selectbox("학생 선택", student_list)
        with r1_c3:
            category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과", "외출"])

        # [교시 선택 로직] 요일별 자동 반영 (화요일 7교시 그외 6교시)
        weekday = target_date.weekday() # 0:월, 1:화, 2:수, 3:목, 4:금, 5:토, 6:일
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: # 화요일(1)일 때만 7교시 추가
            period_options.append("7교시")
        period_options.append("종례")

        # [두 번째 줄] 상세 정보 및 교시 다중 선택 (3열 구성)
        r2_c1, r2_c2, r2_c3 = st.columns([1, 1.8, 2.2])
        with r2_c1:
            reason_type = st.selectbox("사유", ["질병", "인정", "미인정", "기타"])
        with r2_c2:
            selected_periods = st.multiselect("교시(시간) 선택", period_options, help="여러 교시를 선택할 수 있습니다.")
        with r2_c3:
            remark = st.text_input("비고 (상세 사유 등)", placeholder="예: 감기 증상으로 인한 병원 방문")

        # 제출 버튼
        if st.form_submit_button("기록 추가", use_container_width=True):
            if not selected_periods:
                st.error("⚠️ 교시를 최소 하나 이상 선택해 주세요.")
            else:
                s_num = int(selected_student.split('번')[0])
                s_name = selected_student.split(' ')[1]
                
                # 다중 선택된 교시를 문자열로 결합
                period_str = ", ".join(selected_periods)
                
                new_row = pd.DataFrame([{
                    "날짜": target_date.strftime("%Y-%m-%d"),
                    "번호": s_num, 
                    "이름": s_name,
                    "종류": category, 
                    "사유": reason_type, 
                    "교시": period_str, # 교시 정보 저장
                    "비고": remark
                }])
                
                updated_special = pd.concat([df_special, new_row], ignore_index=True)
                conn.update(worksheet="출결특이사항", data=updated_special)
                st.success(f"✅ {s_name} 학생의 기록이 추가되었습니다. ({period_str})")
                st.cache_data.clear() # 데이터 갱신을 위해 캐시 삭제
                st.rerun()

    st.divider()

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
