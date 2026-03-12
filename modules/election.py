import streamlit as st
import pandas as pd
import time
from utils import load_student_list

def show_page(conn, user):
    st.title("🎉 [🎉 이벤트] 반장선거")

    # 1. 데이터 로드 및 병합 (학생 명부와 DB 동기화)
    try:
        df_state = conn.read(worksheet="선거상태", ttl=0)
        df_db = conn.read(worksheet="선거데이터", ttl=0)
        all_students = load_student_list(conn, exclude_admins=True)
        
        # 선거데이터가 비어있을 경우 명부 기반 초기화
        if df_db.empty:
            df_data = all_students[['번호', '이름']].copy()
            df_data['역할'] = '일반'
            df_data['투표완료여부'] = 'X'
            df_data['득표수'] = 0
        else:
            df_data = pd.merge(all_students[['번호', '이름']], df_db, on=['번호', '이름'], how='left')
            df_data[['역할', '투표완료여부']] = df_data[['역할', '투표완료여부']].fillna({'역할': '일반', '투표완료여부': 'X'})
            df_data['득표수'] = df_data['득표수'].fillna(0)
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return

    status = df_state.at[0, '상태']

    # 2. 교사 제어 패널 (관리자 전용)
    if user['name'] in ['교사', '관리자']:
        with st.expander("🛠 교사용 제어 패널"):
            c1, c2, c3 = st.columns(3)
            if c1.button("▶ 투표 시작"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '진행중'}])); st.rerun()
            if c2.button("■ 투표 종료"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '종료'}])); st.rerun()
            if c3.button("📊 결과 발표"): st.session_state.show_results = True
            
            selected = st.selectbox("후보 등록", df_data['이름'])
            if st.button("후보 추가"):
                df_data.loc[df_data['이름'] == selected, '역할'] = '후보'
                conn.update(worksheet="선거데이터", data=df_data); st.success("등록 완료"); st.rerun()

    # 3. 칠판 UI (후보자 실시간 노출)
    candidates = df_data[df_data['역할'] == '후보']
    
    chalk_content = ""
    if status == "대기":
        chalk_content = "<h2>⏳ 투표 대기 중</h2>"
        for i, row in candidates.iterrows():
            chalk_content += f"<p style='font-size: 1.5rem;'>✍️ 기호 {i+1}번. {row['이름']}</p>"
    elif status == "진행중":
        chalk_content = "<h2>🗳️ 투표 진행 중</h2>"
    elif status == "종료" and getattr(st.session_state, 'show_results', False):
        chalk_content = "<h2>🏆 최종 결과</h2>"
        for i, row in candidates.iterrows():
            chalk_content += f"<p style='font-size: 1.5rem;'>{row['이름']} : {int(row['득표수'])}표</p>"

    st.markdown(f"""
        <div style="background-color: #2e5934; border: 15px solid #5d4037; border-radius: 20px; 
                    padding: 40px; color: white; font-family: 'Courier New', monospace; 
                    text-align: center; box-shadow: 10px 10px 20px rgba(0,0,0,0.5);">
            {chalk_content}
        </div>
    """, unsafe_allow_html=True)

    # 4. 학생 투표 로직 (진행중일 때만 활성화)
    if status == "진행중" and user['name'] not in ['교사', '관리자']:
        my_row = df_data[df_data['이름'] == user['name']]
        if not my_row.empty and my_row.iloc[0]['투표완료여부'] == 'O':
            st.warning("이미 투표를 완료하셨습니다.")
        else:
            options = candidates['이름'].tolist() + ['기권']
            choice = st.radio("후보 선택", options)
            if st.button("투표 제출"):
                if choice != '기권':
                    df_data.loc[df_data['이름'] == choice, '득표수'] += 1
                df_data.loc[df_data['이름'] == user['name'], '투표완료여부'] = 'O'
                conn.update(worksheet="선거데이터", data=df_data); st.rerun()
