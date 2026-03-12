import streamlit as st
import pandas as pd
import time
from datetime import datetime
from utils import get_kst

# [핵심 수정] _conn 처럼 언더바(_)를 붙여서 캐싱 대상에서 제외함
@st.cache_data(ttl=5)
def get_data(_conn):
    return {
        "state": _conn.read(worksheet="선거상태", ttl=0),
        "candidates": _conn.read(worksheet="후보자명단", ttl=0),
        "votes": _conn.read(worksheet="투표기록", ttl=0)
    }

def show_page(conn, user):
    st.title("🗳️ 실시간 반장선거")
    
    # 데이터 로드
    data = get_data(conn)
    df_state, df_candidates, df_votes = data['state'], data['candidates'], data['votes']
    
    # 상태값 추출 (데이터가 비어있지 않은지 확인)
    if df_state.empty:
        st.error("선거상태 시트 데이터를 불러올 수 없습니다.")
        return
        
    status = df_state.at[0, '상태']
    end_time_str = df_state.at[0, '종료시간']
    
    # --- 교사(관리자) UI ---
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 교사 관리 도구")
        
        with st.expander("➕ 후보자 등록"):
            with st.form("add_cand"):
                name = st.text_input("이름")
                promise = st.text_input("공약")
                if st.form_submit_button("등록"):
                    new_cand = pd.DataFrame([{'기호': len(df_candidates)+1, '이름': name, '공약': promise, '득표수': 0}])
                    conn.update(worksheet="후보자명단", data=pd.concat([df_candidates, new_cand]))
                    st.cache_data.clear()
                    st.rerun()

        if status != "진행중" and st.button("🚀 선거 시작 (2분)"):
            end_time = get_kst() + timedelta(minutes=2)
            df_state.at[0, '상태'] = "진행중"
            df_state.at[0, '종료시간'] = end_time.strftime("%Y-%m-%d %H:%M:%S")
            conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear()
            st.rerun()

        if status == "종료" and st.button("📊 결과 발표"):
            # ... (결과 발표 로직 동일) ...
            pass
        return

    # --- 학생 UI (실시간 타이머 적용) ---
    if status == "진행중":
        # 1초마다 자동 새로고침 대신, 5초마다 새로고침 유도
        time.sleep(5) 
        
        end_time = datetime.strptime(str(end_time_str), "%Y-%m-%d %H:%M:%S")
        remaining = end_time - get_kst()
        
        if remaining.total_seconds() > 0:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.metric("남은 시간", f"{mins:02d}:{secs:02d}")
            # ... (투표 로직 동일) ...
            if st.button("투표 제출"):
                # ...
                st.cache_data.clear()
                st.rerun()
        else:
            df_state.at[0, '상태'] = "종료"
            conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear()
            st.rerun()
    
    # 갱신을 위해 마지막에 rerun
    st.rerun()
