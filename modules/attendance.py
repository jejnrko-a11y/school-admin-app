import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("🤖 스마트 서류 크로스체크")
    st.info("특이사항 기록 시, 학생들이 제출한 결석계와 대조하여 서류 제출 여부를 자동으로 판별합니다.")

    # 1. 데이터 로드 (학생명부, 결석명부, 출결특이사항)
    try:
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = df_students['번호'].apply(lambda x: int(float(x)))
        df_students = df_students.sort_values(by='번호')
        student_list = [f"{int(row['번호'])}번 {row['이름']}" for _, row in df_students.iterrows()]

        # 결석명부 (증빙 데이터)
        try:
            df_absence_reports = conn.read(worksheet="결석명부", ttl=0)
        except:
            df_absence_reports = pd.DataFrame()

        # 출결특이사항 (기록 데이터)
        try:
            df_special = conn.read(worksheet="출결특이사항", ttl=0)
        except:
            df_special = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])

    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (입력부)
    # ---------------------------------------------------------
    st.subheader("➕ 오늘 특이사항 기록")
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
                "번호": s_num, "이름": s_name,
                "종류": category, "사유": reason_type, "비고": remark
            }])
            
            updated_special = pd.concat([df_special, new_row], ignore_index=True)
            conn.update(worksheet="출결특이사항", data=updated_special)
            st.success(f"✅ {s_name} 기록 완료")
            st.rerun()

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 서류 미제출자 자동 판별 (확인부)
    # ---------------------------------------------------------
    st.subheader("📋 출결 기록 및 서류 대조 현황")

    if df_special.empty:
        st.info("기록된 특이사항이 없습니다.")
    else:
        # 2-1. 자동 판별 함수 정의
        def check_submission(row, reports):
            if reports.empty: return "미제출(X)"
            
            # 해당 학생의 서류만 필터링
            student_reports = reports[reports['이름'] == row['이름']]
            if student_reports.empty: return "미제출(X)"
            
            target_dt = datetime.strptime(row['날짜'], "%Y-%m-%d")
            curr_year = target_dt.year
            
            for _, rep in student_reports.iterrows():
                try:
                    # '03-12~03-14' 형태 파싱
                    period = str(rep['결석기간'])
                    if '~' in period:
                        start_str, end_str = period.split('~')
                        start_dt = datetime.strptime(f"{curr_year}-{start_str}", "%Y-%m-%d")
                        end_dt = datetime.strptime(f"{curr_year}-{end_str}", "%Y-%m-%d")
                        
                        # 타겟 날짜가 기간 내에 포함되는지 확인
                        if start_dt <= target_dt <= end_dt:
                            return "제출완료(O)"
                except:
                    continue
            return "미제출(X)"

        # 2-2. 판별 로직 적용
        df_display = df_special.copy()
        df_display['서류제출'] = df_display.apply(lambda r: check_submission(r, df_absence_reports), axis=1)
        
        # 최신순 정렬
        df_display = df_display.sort_values(by=['날짜', '번호'], ascending=[False, True])

        # 2-3. 스타일 적용 (미제출 빨간색)
        def style_rows(row):
            color = 'background-color: #FFEBEE; color: #D32F2F;' if row['서류제출'] == "미제출(X)" else ''
            return [color] * len(row)

        styled_df = df_display.style.apply(style_rows, axis=1)

        st.write("💡 학생이 앱으로 결석계를 제출하면 자동으로 '제출완료'로 바뀝니다.")
        st.dataframe(
            styled_df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "날짜": st.column_config.TextColumn("날짜", width="small"),
                "번호": st.column_config.NumberColumn("번", width="small"),
                "서류제출": st.column_config.TextColumn("📑 서류상태", width="medium"),
            }
        )
        
        # 2-4. 관리용: 데이터 삭제 버튼 (선택사항)
        with st.expander("데이터 관리 (초기화)"):
            if st.button("출결 기록 전체 삭제"):
                empty_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "비고"])
                conn.update(worksheet="출결특이사항", data=empty_df)
                st.rerun()
