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
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{row['번호']}번 {row['이름']}" for _, row in df_students.iterrows()]

        # 결석명부 (증빙 데이터)
        try:
            df_absence_reports = conn.read(worksheet="결석명부", ttl=0)
        except:
            df_absence_reports = pd.DataFrame()

        # 출결특이사항 (교사 기록 데이터)
        try:
            df_special = conn.read(worksheet="출결특이사항", ttl=0)
        except:
            df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])

    except Exception as e:
        st.error(f"데이터 로드 중 오류 발생: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (상단 고정 입력부)
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")
    with st.form("add_special_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1, 1.5, 1])
        with c1:
            target_date = st.date_input("발생 날짜", value=get_kst().date())
        with c2:
            selected_student = st.selectbox("학생 선택", student_list)
        with c3:
            category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과"])

        c4, c5 = st.columns([1.5, 2.5])
        with c4:
            reason_type = st.selectbox("사유", ["질병", "미인정", "기타"])
        with c5:
            remark = st.text_input("비고 (나이스 입력용 사유 등)")

        if st.form_submit_button("기록 추가", use_container_width=True):
            s_num = int(selected_student.split('번')[0])
            s_name = selected_student.split(' ')[1]
            
            new_row = pd.DataFrame([{
                "날짜": target_date.strftime("%Y-%m-%d"),
                "번호": s_num, 
                "이름": s_name,
                "종류": category, 
                "사유": reason_type, 
                "비고": remark
            }])
            
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.success(f"✅ {s_name} 학생의 기록이 추가되었습니다.")
            st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 월별 탭 구성 및 자동 판별 (하단 확인부)
    # ---------------------------------------------------------
    st.subheader("📋 월별 서류 대조 현황")

    if df_special.empty:
        st.info("기록된 특이사항이 아직 없습니다.")
    else:
        # [Helper] 자동 판별 함수 (기존 로직 유지)
        def check_submission_robust(row, reports):
            if reports.empty: return "미제출(X)"
            try:
                target_name = str(row['이름']).strip()
                target_dt = datetime.strptime(str(row['날짜']).strip(), "%Y-%m-%d")
                curr_year = target_dt.year
                
                # 학생명 일치 서류 필터링
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

        # 데이터 가공: 번호 정수화 및 서류 판별
        df_processed = df_special.copy()
        df_processed['번호'] = pd.to_numeric(df_processed['번호'], errors='coerce').fillna(0).astype(int)
        
        with st.spinner("서류 대조 중..."):
            df_processed['서류제출'] = df_processed.apply(lambda r: check_submission_robust(r, df_absence_reports), axis=1)
            # 날짜 컬럼에서 월(Month) 정보 추출
            df_processed['월'] = pd.to_datetime(df_processed['날짜']).dt.month
        
        # 월별 탭 생성 (3월 ~ 12월)
        month_labels = [f"{m}월" for m in range(3, 13)]
        tabs = st.tabs(month_labels)

        for i, tab in enumerate(tabs):
            current_month = i + 3
            with tab:
                # 해당 월 데이터 필터링
                month_df = df_processed[df_processed['월'] == current_month].copy()
                
                if month_df.empty:
                    st.write(f"📅 {current_month}월에 기록된 특이사항이 없습니다.")
                else:
                    # 최신순 정렬
                    month_df = month_df.sort_values(by=['날짜', '번호'], ascending=[False, True])
                    
                    # 불필요한 '월' 컬럼은 제거하고 표시
                    display_cols = ["날짜", "번호", "이름", "종류", "사유", "서류제출", "비고"]
                    
                    st.dataframe(
                        month_df[display_cols].style.apply(style_rows, axis=1),
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            "번호": st.column_config.NumberColumn("번호", format="%d", width="small"),
                            "날짜": st.column_config.TextColumn("특이사항 날짜", width="medium"),
                            "서류제출": st.column_config.TextColumn("📑 제출여부", width="medium"),
                            "비고": st.column_config.TextColumn("상세 사유", width="large")
                        }
                    )
        
        # 관리 기능
        with st.expander("🗑️ 데이터 관리"):
            if st.button("출결 기록 전체 초기화 (주의)"):
                empty_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])
                conn.update(worksheet="출결특이사항", data=empty_df)
                st.success("데이터가 초기화되었습니다.")
                st.rerun()
