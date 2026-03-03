import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("🤖 스마트 서류 크로스체크")
    st.info("기록된 특이사항 날짜가 학생들이 제출한 결석계 기간에 포함되는지 자동으로 대조합니다.")

    # 1. 데이터 로드
    try:
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        
        # [수정] 번호 데이터 타입 정수 변환 (NaN 방지 포함)
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{row['번호']}번 {row['이름']}" for _, row in df_students.iterrows()]

        try:
            df_absence_reports = conn.read(worksheet="결석명부", ttl=0)
        except:
            df_absence_reports = pd.DataFrame()

        try:
            df_special = conn.read(worksheet="출결특이사항", ttl=0)
        except:
            df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])

    except Exception as e:
        st.error(f"데이터 로드 중 오류가 발생했습니다: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (입력부)
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
    # PART 2: 서류 미제출자 자동 판별 로직 (확인부)
    # ---------------------------------------------------------
    st.subheader("📋 출결 기록 및 서류 대조 현황")

    if df_special.empty:
        st.info("기록된 특이사항이 아직 없습니다.")
    else:
        # [핵심] 자동 판별 함수 (날짜 및 이름 매칭 강화)
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

        # 데이터 가공
        df_display = df_special.copy()
        
        # [수정] 출력용 데이터프레임의 '번호' 컬럼 소수점 제거
        df_display['번호'] = pd.to_numeric(df_display['번호'], errors='coerce').fillna(0).astype(int)
        
        with st.spinner("서류 대조 중..."):
            df_display['서류제출'] = df_display.apply(lambda r: check_submission_robust(r, df_absence_reports), axis=1)
        
        # 최신순 정렬
        df_display = df_display.sort_values(by=['날짜', '번호'], ascending=[False, True])

        # 스타일 적용 함수
        def style_rows(row):
            if row['서류제출'] == "미제출(X)":
                return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row)
            return [''] * len(row)

        # [수정] 결과 표 출력 부분 (Column Config 적용)
        st.write("💡 학생이 제출한 결석계 기간과 교사가 기록한 날짜를 실시간 대조합니다.")
        st.dataframe(
            df_display.style.apply(style_rows, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "번호": st.column_config.NumberColumn("번호", format="%d", width="small"), # %d로 정수 출력 강제
                "날짜": st.column_config.TextColumn("특이사항 날짜", width="medium"),
                "이름": st.column_config.TextColumn("성명", width="small"),
                "종류": st.column_config.TextColumn("구분", width="small"),
                "서류제출": st.column_config.TextColumn("📑 제출여부", width="medium")
            }
        )
        
        with st.expander("🗑️ 데이터 관리"):
            if st.button("출결 기록 전체 초기화 (주의)"):
                empty_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])
                conn.update(worksheet="출결특이사항", data=empty_df)
                st.success("데이터가 초기화되었습니다.")
                st.rerun()
