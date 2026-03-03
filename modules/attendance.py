import streamlit as st
import pandas as pd
from utils import get_kst
from datetime import datetime

def show_page(conn, student_list):
    st.title("📋 스마트 출석 관리")
    
    tab1, tab2 = st.tabs(["오늘의 출결 체크", "월별 현황 보기"])

    # --- 탭 1: 실시간 체크 ---
    with tab1:
        today_str = get_kst().strftime("%m-%d")
        st.subheader(f"📅 {today_str} 출결 체크")
        
        # 1. 이미 체크된 명단 가져오기
        try:
            log_df = conn.read(worksheet="출결기록", ttl=0)
            today_logs = log_df[log_df['날짜'] == today_str]
        except:
            today_logs = pd.DataFrame()

        st.write("학생을 클릭하여 결석/지각 정보를 입력하세요.")
        
        # 2. 학생 명단을 3열로 배치하여 버튼 생성
        cols = st.columns(3)
        for idx, student in enumerate(student_list):
            with cols[idx % 3]:
                # 이미 체크된 학생인지 확인
                is_checked = student['name'] in today_logs['이름'].values
                btn_label = f"✅ {student['name']}" if is_checked else f"⚪ {student['name']}"
                
                if st.button(btn_label, key=f"att_{student['name']}"):
                    st.session_state.target_student = student
                    st.session_state.show_dialog = True

        # 3. 입력 다이얼로그 (팝업 대신 하단 입력창)
        if st.session_state.get('show_dialog'):
            with st.expander(f"📌 {st.session_state.target_student['name']} 학생 상태 입력", expanded=True):
                status = st.radio("상태 선택", ["결석", "지각", "조퇴", "정상(취소)"], horizontal=True)
                note = st.text_input("비고(사유)", placeholder="예: 늦잠, 병원 등")
                
                if st.button("기록 저장"):
                    # 데이터 저장 로직
                    new_log = pd.DataFrame([{
                        "날짜": today_str,
                        "이름": st.session_state.target_student['name'],
                        "번호": st.session_state.target_student['num'],
                        "상태": status,
                        "교사비고": note
                    }])
                    
                    # 기존 데이터에서 해당 날짜/학생 삭제 후 추가 (중복 방지)
                    if not log_df.empty:
                        log_df = log_df[~((log_df['날짜'] == today_str) & (log_df['이름'] == st.session_state.target_student['name']))]
                    
                    if status != "정상(취소)":
                        updated_df = pd.concat([log_df, new_log], ignore_index=True)
                    else:
                        updated_df = log_df
                        
                    conn.update(worksheet="출결기록", data=updated_df)
                    st.success("반영되었습니다.")
                    st.session_state.show_dialog = False
                    st.rerun()

    # --- 탭 2: 월별 현황판 (출석부 형식) ---
    with tab2:
        st.subheader("📊 월별 출석부 현황")
        try:
            all_logs = conn.read(worksheet="출결기록", ttl=0)
            if all_logs.empty:
                st.info("기록된 출결 데이터가 없습니다.")
            else:
                # 데이터 피벗 (행: 이름, 열: 날짜)
                pivot_df = all_logs.pivot(index='이름', columns='날짜', values='상태').fillna('')
                
                # 가독성을 위한 스타일링
                def color_status(val):
                    if val == '결석': return 'background-color: #FEE2E2; color: #991B1B;' # 빨강
                    if val == '지각': return 'background-color: #FEF3C7; color: #92400E;' # 노랑
                    if val == '조퇴': return 'background-color: #DBEAFE; color: #1E40AF;' # 파랑
                    return ''

                st.dataframe(pivot_df.style.applymap(color_status), use_container_width=True)
                
                # 통계 요약
                st.divider()
                summary = all_logs['상태'].value_counts()
                st.write("📈 **이번 달 누적 통계**")
                c1, c2, c3 = st.columns(3)
                c1.metric("총 결석", f"{summary.get('결석', 0)}건")
                c2.metric("총 지각", f"{summary.get('지각', 0)}건")
                c3.metric("총 조퇴", f"{summary.get('조퇴', 0)}건")

        except Exception as e:
            st.error(f"데이터를 불러올 수 없습니다: {e}")
