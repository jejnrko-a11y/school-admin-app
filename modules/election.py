import streamlit as st
import pandas as pd
import time
from utils import load_student_list

# 칠판 스타일 CSS
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
        margin: 20px 0;
    }
    .chalk-text { font-size: 1.5rem; margin: 10px 0; }
</style>
"""

def show_page(conn, user):
    st.markdown(BOARD_STYLE, unsafe_allow_html=True)
    st.title("🎉 [🎉 이벤트] 반장선거")

    # 1. 데이터 로드 및 병합 (학생 명부와 DB 동기화)
    try:
        df_state = conn.read(worksheet="선거상태", ttl=0)
        df_db = conn.read(worksheet="선거데이터", ttl=0)
        all_students = load_student_list(conn, exclude_admins=True)
        
        # 선거데이터가 비어있을 경우 대비 (기존 데이터 없으면 명부 기반 초기화)
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

    # 2. 교사 제어 패널
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

    # 3. 칠판 UI
    st.markdown("<div class='chalkboard'>", unsafe_allow_html=True)
    
    candidates = df_data[df_data['역할'] == '후보']

    if status == "대기":
        st.header("⏳ 투표 대기 중")
        for name in candidates['이름']: st.markdown(f"<p class='chalk-text'>✍️ 후보자: {name}</p>", unsafe_allow_html=True)
    
    elif status == "진행중":
        st.header("🗳️ 투표 진행 중")
        if user['name'] not in ['교사', '관리자']:
            my_row = df_data[df_data['이름'] == user['name']]
            if not my_row.empty and my_row.iloc[0]['투표완료여부'] == 'O':
                st.write("이미 투표를 마쳤습니다.")
            else:
                options = candidates['이름'].tolist() + ['기권']
                choice = st.radio("후보 선택", options)
                if st.button("투표 제출"):
                    if choice != '기권':
                        df_data.loc[df_data['이름'] == choice, '득표수'] += 1
                    df_data.loc[df_data['이름'] == user['name'], '투표완료여부'] = 'O'
                    conn.update(worksheet="선거데이터", data=df_data); st.rerun()
    
    elif status == "종료" and getattr(st.session_state, 'show_results', False):
        st.header("🏆 개표 결과")
        placeholder = st.empty()
        # 긴장감 넘치는 카운트업
        for i in range(1, int(candidates['득표수'].max() + 1) if not candidates.empty else 2):
            with placeholder.container():
                for _, row in candidates.iterrows():
                    score = min(i, int(row['득표수']))
                    st.write(f"### {row['이름']} : {score}표")
            time.sleep(0.8)
        
        # 기권 수 계산 (투표완료자 - 후보득표합)
        abstain = len(df_data[df_data['투표완료여부'] == 'O']) - candidates['득표수'].sum()
        st.markdown(f"--- <br> 기권자 수: {int(abstain)}", unsafe_allow_html=True)
        st.balloons()
        
    st.markdown("</div>", unsafe_allow_html=True)
