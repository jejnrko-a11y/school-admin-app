import streamlit as st
import pandas as pd
from utils import get_kst
from datetime import datetime

def show_page(conn, student_list):
    st.title("📋 스마트 출석 관리")
    
    if not student_list:
        st.warning("학생 명부를 불러올 수 없습니다. 구글 시트의 '학생명부' 탭을 확인하세요.")
        return

    tab1, tab2 = st.tabs(["오늘의 출결 체크", "월별 현황 보기"])

    # --- 탭 1: 실시간 체크 ---
    with tab1:
        today_str = get_kst().strftime("%m-%d")
        st.subheader(f"📅 {today_str} 출결 체크")
        
        try:
            log_df = conn.read(worksheet="출결기록", ttl=0)
            log_df = log_df.fillna('')
        except:
            log_df = pd.DataFrame(columns=["날짜", "이름", "번호", "상태", "교사비고"])

        st.write("학생 버튼을 클릭하여 상태를 입력하세요.")
        
        # 학생 명단을 3열로 배치
        cols = st.columns(3)
        for idx, student in enumerate(student_list):
            with cols[idx % 3]:
                # 오늘 이미 체크된 기록이 있는지 확인
                today_logs = log_df[log_df['날짜'] == today_str]
                is_checked = student['name'] in today_logs['이름'].values
                
                btn_label = f"✅ {student['name']}" if is_checked else f"⚪ {student['name']}"
                if st.button(btn_label, key=f"att_btn_{student['name']}"):
                    st.session_state.target_student = student
                    st.session_state.show_att_dialog = True

        # 입력창 (버튼 클릭 시 나타남)
        if st.session_state.get('show_att_dialog'):
            st.divider()
            with st.expander(f"📌 {st.session_state.target_student['name']} 학생 상태 설정", expanded=True):
                target = st.session_state.target_student
                status = st.radio("상태", ["결석", "지각", "조퇴", "정상(취소)"], horizontal=True)
                note = st.text_input("비고(사유)")
                
                if st.button("기록 저장"):
                    # 기존 기록 삭제 후 새 기록 추가 (중복 방지)
                    new_log_df = log_df[~((log_df['날짜'] == today_str) & (log_df['이름'] == target['name']))]
                    
                    if status != "정상(취소)":
                        new_row = pd.DataFrame([{
                            "날짜": today_str, "이름": target['name'], "번호": target['num'],
                            "상태": status, "교사비고": note
                        }])
                        new_log_df = pd.concat([new_log_df, new_row], ignore_index=True)
                    
                    conn.update(worksheet="출결기록", data=new_log_df)
                    st.success(f"{target['name']} 학생 {status} 처리 완료!")
                    st.session_state.show_att_dialog = False
                    st.rerun()

    # --- 탭 2: 월별 현황판 ---
    with tab2:
        st.subheader("📊 출석부 현황")
        try:
            all_logs = conn.read(worksheet="출결기록", ttl=0)
            if all_logs.empty:
                st.info("기록된 출결 데이터가 없습니다.")
            else:
                pivot_df = all_logs.pivot(index='이름', columns='날짜', values='상태').fillna('')
                st.dataframe(pivot_df, use_container_width=True)
        except:
            st.info("데이터를 구성하는 중입니다.")
