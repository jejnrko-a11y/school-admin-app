import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("🤖 스마트 서류 크로스체크")
    st.info("기록된 특이사항 날짜가 학생들이 제출한 결석계 기간에 포함되는지 자동으로 대조합니다.")

    # 1. 데이터 로드
    try:
        # 학생명부 (입력 시 필요)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = df_students['번호'].apply(lambda x: int(float(x)))
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{int(row['번호'])}번 {row['이름']}" for _, row in df_students.iterrows()]

        # 결석명부 (증빙 데이터 - 크로스체크 핵심)
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
            reason_type = st.selectbox("사유", ["질병", "인정", "기타"])
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
        # [핵심] 자동 판별 함수
        def check_submission_robust(row, reports):
            if reports.empty: return "미제출(X)"
            
            try:
                # 1. 이름 매칭 (공백 제거 및 타입 변환)
                target_name = str(row['이름']).strip()
                target_dt = datetime.strptime(str(row['날짜']).strip(), "%Y-%m-%d")
                curr_year = target_dt.year
                
                # 해당 학생의 서류만 필터링
                student_reports = reports[reports['이름'].astype(str).str.strip() == target_name]
                if student_reports.empty: return "미제출(X)"
                
                for _, rep in student_reports.iterrows():
                    period = str(rep['결석기간']).strip()
                    if not period or period == 'nan': continue
                    
                    try:
                        # 2. 결석기간 파싱 (MM-DD 또는 MM-DD~MM-DD)
                        if '~' in period:
                            start_str, end_str = period.split('~')
                            start_dt = datetime.strptime(f"{curr_year}-{start_str.strip()}", "%Y-%m-%d")
                            end_dt = datetime.strptime(f"{curr_year}-{end_str.strip()}", "%Y-%m-%d")
                        else:
                            # 단일 날짜인 경우
                            dt = datetime.strptime(f"{curr_year}-{period}", "%Y-%m-%d")
                            start_dt = end_dt = dt
                        
                        # 3. 날짜 범위 포함 여부 검사
                        if start_dt <= target_dt <= end_dt:
                            return "제출완료(O)"
                    except Exception:
                        continue # 파싱 에러 시 다음 서류로 넘어감
                        
                return "미제출(X)"
            except Exception as e:
                return f"에러: {e}"

        # 데이터 가공
        df_display = df_special.copy()
        
        with st.spinner("서류 대조 중..."):
            df_display['서류제출'] = df_display.apply(lambda r: check_submission_robust(r, df_absence_reports), axis=1)
        
        # 최신순 정렬
        df_display = df_display.sort_values(by=['날짜', '번호'], ascending=[False, True])

        # 미제출자 하이라이트 스타일
        def style_rows(row):
            if row['서류제출'] == "미제출(X)":
                return ['background-color: #FFEBEE; color: #D32F2F; font-weight: bold'] * len(row)
            return [''] * len(row)

        # 결과 출력
        st.write("💡 학생이 제출한 결석계의 '결석기간'과 교사가 기록한 '날짜'를 실시간 대조합니다.")
        st.dataframe(
            df_display.style.apply(style_rows, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "날짜": st.column_config.TextColumn("특이사항 날짜"),
                "이름": st.column_config.TextColumn("성명"),
                "서류제출": st.column_config.TextColumn("📑 제출여부", help="학생이 결석계를 제출하면 자동으로 O로 변경됩니다.")
            }
        )
        
        # 관리용 섹션
        with st.expander("🗑️ 데이터 관리"):
            if st.button("출결 기록 전체 초기화 (주의)"):
                empty_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])
                conn.update(worksheet="출결특이사항", data=empty_df)
                st.success("데이터가 초기화되었습니다.")
                st.rerun()
