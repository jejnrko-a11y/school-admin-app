import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from utils import get_kst

# API 호출을 최소화하기 위한 캐싱 함수
@st.cache_data(ttl=5)
def get_data(_conn):
    try:
        # 데이터가 없을 경우를 대비해 기본 데이터프레임 구조 생성
        state = _conn.read(worksheet="선거상태", ttl=0)
        if state.empty or '상태' not in state.columns:
            state = pd.DataFrame([{'상태': '진행전', '종료시간': '2026-03-12 23:30:00'}])
            
        candidates = _conn.read(worksheet="후보자명단", ttl=0)
        votes = _conn.read(worksheet="투표기록", ttl=0)
        
        return {"state": state, "candidates": candidates, "votes": votes}
    except Exception as e:
        return {
            "state": pd.DataFrame([{'상태': '진행전', '종료시간': '2026-03-12 23:30:00'}]),
            "candidates": pd.DataFrame(columns=['기호', '이름', '공약', '득표수']),
            "votes": pd.DataFrame(columns=['학번', '이름', '투표완료여부'])
        }

def show_page(conn, user):
    st.title("🗳️ 실시간 반장선거")
    
    # 1. 데이터 로드
    data = get_data(conn)
    df_state, df_candidates, df_votes = data['state'], data['candidates'], data['votes']
    
    status = df_state.at[0, '상태']
    end_time_str = df_state.at[0, '종료시간']
    
    # --- 교사 관리 영역 ---
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 교사 관리 도구")
        
        with st.expander("➕ 후보자 등록"):
            with st.form("add_cand"):
                name = st.text_input("이름")
                promise = st.text_input("공약")
                if st.form_submit_button("등록"):
                    new_cand = pd.DataFrame([{'기호': len(df_candidates)+1, '이름': name, '공약': promise, '득표수': 0}])
                    conn.update(worksheet="후보자명단", data=pd.concat([df_candidates, new_cand], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()

        if status != "진행중" and st.button("🚀 선거 시작 (2분)"):
            end_time = get_kst() + timedelta(minutes=2)
            df_state.at[0, '상태'] = "진행중"
            df_state.at[0, '종료시간'] = end_time.strftime("%Y-%m-%d %H:%M:%S")
            conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear()
            st.rerun()

        if status == "종료" and st.button("📊 결과 발표 (박진감 모드)"):
            st.write("### 🥁 선거 결과 발표 중...")
            bar_container = st.empty()
            sorted_df = df_candidates.sort_values('득표수', ascending=True)
            for i in range(1, len(sorted_df) + 1):
                time.sleep(1.0)
                bar_container.bar_chart(sorted_df.tail(i).set_index('이름')['득표수'])
            st.balloons()
            st.rerun()
        return

    # --- 학생 투표 영역 ---
    if status == "진행전":
        st.info("현재 진행 중인 선거가 없습니다.")
    
    elif status == "진행중":
        end_time = datetime.strptime(str(end_time_str), "%Y-%m-%d %H:%M:%S")
        remaining = end_time - get_kst()
        
        if remaining.total_seconds() > 0:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.metric("남은 시간", f"{mins:02d}:{secs:02d}")
            
            # 투표 여부 확인
            if not df_votes.empty and not df_votes[(df_votes['학번'] == user['num']) & (df_votes['투표완료여부'] == "O")].empty:
                st.success("✅ 이미 투표를 완료하셨습니다.")
            else:
                choice = st.radio("후보 선택", df_candidates['이름'])
                if st.button("투표 제출"):
                    df_candidates.loc[df_candidates['이름'] == choice, '득표수'] += 1
                    conn.update(worksheet="후보자명단", data=df_candidates)
                    
                    new_vote = pd.DataFrame([{'학번': user['num'], '이름': user['name'], '투표완료여부': 'O'}])
                    conn.update(worksheet="투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.cache_data.clear()
                    st.rerun()
        else:
            df_state.at[0, '상태'] = "종료"
            conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear()
            st.rerun()
            
    else: # 종료
        st.warning("선거가 종료되었습니다.")
        
    # 5초마다 새로고침 유도
    time.sleep(5)
    st.rerun()
