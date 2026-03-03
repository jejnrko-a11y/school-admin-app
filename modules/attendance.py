import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("🚩 출결 특이사항 & 서류 관리")
    st.info("나이스(NEIS) 입력 전 특이사항을 기록하고, 결석계 제출 여부를 체크하는 페이지입니다.")

    # 1. 학생 명부 로드 (입력용)
    try:
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = df_students['번호'].apply(lambda x: int(float(x)))
        df_students = df_students.sort_values(by='번호')
        
        # 선택박스용 리스트 생성 (예: "1번 김철수")
        student_list = [f"{int(row['번호'])}번 {row['이름']}" for _, row in df_students.iterrows()]
    except Exception as e:
        st.error(f"명부를 불러올 수 없습니다: {e}")
        return

    # ---------------------------------------------------------
    # PART 1: 특이사항 학생 추가 (입력부)
    # ---------------------------------------------------------
    st.subheader("➕ 특이사항 기록 추가")
    with st.form("attendance_add_form", clear_on_submit=True):
        c1, c2, c3 = st.columns([1.5, 2, 1.5])
        with c1:
            target_date = st.date_input("날짜", value=get_kst().date())
        with c2:
            selected_student = st.selectbox("학생 선택", student_list)
        with c3:
            category = st.selectbox("종류", ["결석", "지각", "조퇴", "결과"])

        c4, c5, c6 = st.columns([2, 1, 2])
        with c4:
            reason_type = st.selectbox("사유 구분", ["질병", "미인정", "기타(체험/경조사 등)"])
        with c5:
            is_submitted = st.selectbox("서류 제출", ["X", "O"])
        with c6:
            remark = st.text_input("비고 (상세 사유 등)")

        submit_btn = st.form_submit_button("기록 추가하기", use_container_width=True)

        if submit_btn:
            try:
                # 데이터 파싱
                s_num = int(selected_student.split('번')[0])
                s_name = selected_student.split(' ')[1]
                
                new_data = pd.DataFrame([{
                    "날짜": target_date.strftime("%Y-%m-%d"),
                    "번호": s_num,
                    "이름": s_name,
                    "종류": category,
                    "사유": reason_type,
                    "서류제출": is_submitted,
                    "비고": remark
                }])

                # 기존 데이터 읽기 및 병합
                try:
                    existing_df = conn.read(worksheet="출결특이사항", ttl=0)
                except:
                    existing_df = pd.DataFrame(columns=["날짜", "번호", "이름", "종류", "사유", "서류제출", "비고"])
                
                updated_df = pd.concat([existing_df, new_data], ignore_index=True)
                conn.update(worksheet="출결특이사항", data=updated_df)
                
                st.success(f"✅ {s_name} 학생의 특이사항이 기록되었습니다.")
                st.rerun()
            except Exception as e:
                st.error(f"저장 중 오류 발생: {e}")

    st.divider()

    # ---------------------------------------------------------
    # PART 2: 서류 제출 크로스체크 (확인 및 수정부)
    # ---------------------------------------------------------
    st.subheader("🔍 서류 제출 현황 및 관리")
    
    try:
        # 데이터 로드
        display_df = conn.read(worksheet="출결특이사항", ttl=0)
        
        if display_df.empty:
            st.warning("기록된 특이사항이 없습니다.")
        else:
            # 최신 날짜순 정렬
            display_df = display_df.sort_values(by=['날짜', '번호'], ascending=[False, True])
            
            st.write("💡 아래 표에서 '서류제출'이나 '비고'를 직접 수정하고 하단의 저장 버튼을 누르세요.")
            
            # 데이터 에디터 활용 (핵심 기능)
            edited_df = st.data_editor(
                display_df,
                column_config={
                    "서류제출": st.column_config.SelectboxColumn(
                        "서류제출",
                        help="제출 완료 시 O로 변경",
                        options=["O", "X"],
                        required=True,
                    ),
                    "날짜": st.column_config.TextColumn(disabled=True),
                    "번호": st.column_config.NumberColumn(disabled=True),
                    "이름": st.column_config.TextColumn(disabled=True),
                    "종류": st.column_config.TextColumn(disabled=True),
                    "사유": st.column_config.TextColumn(disabled=True),
                },
                hide_index=True,
                use_container_width=True,
                key="attendance_editor"
            )

            # 변경 사항이 있을 때만 저장 버튼 활성화
            if not display_df.equals(edited_df):
                if st.button("💾 변경된 내용 시트에 반영하기", type="primary", use_container_width=True):
                    try:
                        # 원본 시트는 정렬되지 않은 상태로 업데이트해도 무방하므로 바로 업데이트
                        conn.update(worksheet="출결특이사항", data=edited_df)
                        st.success("변경 사항이 저장되었습니다!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"수정 실패: {e}")

    except Exception as e:
        st.info("아직 '출결특이사항' 시트가 생성되지 않았거나 비어있습니다.")
