import streamlit as st
import pandas as pd
import time
from utils import load_student_list

# CSS: 칠판 스타일
BOARD_STYLE = """
<style>
    .chalkboard {
        background-color: #2e5934;
        border: 15px solid #5d4037;
        border-radius: 20px;
        padding: 40px;
        color: white;
        font-family: 'Courier New', monospace;
        text-align: center;
        box-shadow: 10px 10px 20px rgba(0,0,0,0.5);
    }
</style>
"""

def show_page(conn, user):
    st.markdown(BOARD_STYLE, unsafe_allow_html=True)
    st.title("🎉 반장선거 이벤트")
    
    # 데이터 로드
    df_state = conn.read(worksheet="선거상태", ttl=0)
    df_data = conn.read(worksheet="선거데이터", ttl=0)
    status = df_state.at[0, '상태']

    # 교사 전용 제어 패널
    if user['name'] in ['교사', '관리자']:
        st.subheader("🛠 관리자 제어")
        c1, c2, c3 = st.columns(3)
        if c1.button("▶ 투표 시작"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '진행중'}])); st.rerun()
        if c2.button("■ 투표 종료"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '종료'}])); st.rerun()
        if c3.button("📊 결과 발표"): st.session_state.show_results = True
        
        # 후보 등록 (학생명부 활용)
        all_students = load_student_list(conn, exclude_admins=True)
        with st.form("cand_form"):
            selected = st.selectbox("후보 등록", all_students['이름'])
            if st.form_submit_button("후보 추가"):
                df_data.loc[df_data['이름'] == selected, '역할'] = '후보'
                conn.update(worksheet="선거데이터", data=df_data); st.rerun()

    # 칠판 UI
    st.markdown("<div class='chalkboard'>", unsafe_allow_html=True)
    if status == "대기":
        st.header("⏳ 투표 대기 중...")
        candidates = df_data[df_data['역할'] == '후보']
        for name in candidates['이름']: st.write(f"✍️ 후보자: {name}")
    
    elif status == "진행중":
        st.header("🗳️ 투표 진행 중")
        if user['name'] not in ['교사', '관리자']:
            # 투표 완료 체크
            my_row = df_data[df_data['이름'] == user['name']]
            if my_row.iloc[0]['투표완료여부'] == 'O':
                st.write("이미 투표하셨습니다.")
            else:
                options = df_data[df_data['역할'] == '후보']['이름'].tolist() + ['기권']
                choice = st.radio("후보를 선택하세요", options)
                if st.button("투표하기"):
                    if choice != '기권':
                        df_data.loc[df_data['이름'] == choice, '득표수'] += 1
                    df_data.loc[df_data['이름'] == user['name'], '투표완료여부'] = 'O'
                    conn.update(worksheet="선거데이터", data=df_data); st.rerun()
    
    elif status == "종료" and getattr(st.session_state, 'show_results', False):
        st.header("🏆 개표 결과")
        final_data = df_data[df_data['역할'] == '후보']
        # 카운트업 애니메이션
        placeholder = st.empty()
        for i in range(1, int(final_data['득표수'].max()) + 1):
            with placeholder.container():
                for _, row in final_data.iterrows():
                    score = min(i, int(row['득표수']))
                    st.write(f"## {row['이름']}: {score}표")
            time.sleep(0.5)
        st.write(f"--- 기권표: {len(df_data[df_data['투표완료여부']=='O']) - df_data['득표수'].sum()} ---")
    st.markdown("</div>", unsafe_allow_html=True)
