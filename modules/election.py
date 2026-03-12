import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from utils import get_kst, load_student_list

# 1. 데이터 로드 함수 정의 (항상 상단에 위치)
@st.cache_data(ttl=5)
def get_data(_conn):
    try:
        # 시트 데이터 읽기
        state = _conn.read(worksheet="선거상태", ttl=0)
        candidates = _conn.read(worksheet="후보자명단", ttl=0)
        votes = _conn.read(worksheet="투표기록", ttl=0)
        
        # 헤더 공백 제거 및 구조 보정
        state.columns = state.columns.str.strip()
        candidates.columns = candidates.columns.str.strip()
        votes.columns = votes.columns.str.strip()
        
        return {"state": state, "candidates": candidates, "votes": votes}
    except Exception as e:
        st.error(f"데이터 로드 에러: {e}")
        return None

# 2. 투표 처리 로직 함수
def process_vote(conn, candidate_name, user):
    data = get_data(conn)
    df_cands = data['candidates']
    df_votes = data['votes']
    
    # 득표수 업데이트
    df_cands.loc[df_cands['이름'] == candidate_name, '득표수'] += 1
    conn.update(worksheet="후보자명단", data=df_cands)
    
    # 투표 기록 추가
    new_vote = pd.DataFrame([{'학번': user['num'], '이름': user['name'], '투표완료여부': 'O'}])
    conn.update(worksheet="투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
    st.cache_data.clear()

# 3. 메인 화면 함수
def show_page(conn, user):
    st.markdown("""
        <style>
        .candidate-card { background: #ffffff; border-radius: 15px; padding: 20px; margin-bottom: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); border-left: 8px solid #3b82f6; }
        .stButton>button { width: 100%; border-radius: 50px; font-weight: bold; background-color: #3b82f6; color: white; border: none; }
        </style>
    """, unsafe_allow_html=True)

    # 데이터 호출
    data = get_data(conn)
    if not data: return
    df_elec, df_votes = data['candidates'], data['votes']
    
    st.title("🗳️ 실시간 반장선거")

    # 학생 UI
    if user['name'] not in ["교사", "관리자"]:
        st.markdown("### 🏆 후보자 목록")
        for _, row in df_elec.iterrows():
            with st.container():
                st.markdown(f"<div class='candidate-card'><h2>기호 {int(row['기호'])}번 {row['이름']}</h2></div>", unsafe_allow_html=True)
                if st.button(f"🗳️ {row['이름']} 투표하기", key=f"btn_{row['기호']}"):
                    process_vote(conn, row['이름'], user)
                    st.toast(f"✅ {row['이름']} 후보에게 투표 완료!", icon="🎉")
                    st.balloons()
                    st.rerun()

    # 교사 UI
    else:
        if st.button("📊 실시간 긴장감 개표"):
            st.subheader("🔥 개표 진행 중...")
            chart_area = st.empty()
            sorted_df = df_elec.sort_values('득표수', ascending=True)
            for i in range(1, len(sorted_df) + 1):
                time.sleep(1.0)
                st.progress(i / len(sorted_df))
                chart_area.bar_chart(sorted_df.tail(i).set_index('이름')['득표수'])
            st.balloons()
