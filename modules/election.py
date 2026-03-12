import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from utils import get_kst, load_student_list

@st.cache_data(ttl=5)
def get_data(_conn):
    try:
        # 데이터가 없을 경우를 대비해 기본 구조 설정
        state = _conn.read(worksheet="선거상태", ttl=0)
        if state.empty or '상태' not in state.columns:
            state = pd.DataFrame([{'상태': '진행전', '종료시간': '2026-03-12 23:30:00'}])
            
        candidates = _conn.read(worksheet="후보자명단", ttl=0)
        votes = _conn.read(worksheet="투표기록", ttl=0)
        
        return {"state": state, "candidates": candidates, "votes": votes}
    except Exception as e:
        return {
            "state": pd.DataFrame([{'상태': '진행전', '종료시간': '2026-03-12 23:30:00'}]),
            "candidates": pd.DataFrame(columns=['기호', '이름', '득표수']),
            "votes": pd.DataFrame(columns=['학번', '이름', '투표완료여부'])
        }

def show_page(conn, user):
    st.title("🗳️ 실시간 반장선거")
    
    # 1. 데이터 로드
    data = get_data(conn)
    df_state, df_candidates, df_votes = data['state'], data['candidates'], data['votes']
    status = df_state.at[0, '상태']
    
    # --- 교사 관리 영역 ---
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 교사 관리 도구")
        
        # [변경] 학생명부를 불러와서 이름 선택으로 변경
        student_list = load_student_list(conn, exclude_admins=True)
        
        with st.expander("➕ 후보자 등록"):
            with st.form("add_cand"):
                selected_name = st.selectbox("후보자 선택", student_list['이름'].tolist())
                if st.form_submit_button("등록"):
                    new_cand = pd.DataFrame([{'기호': len(df_candidates)+1, '이름': selected_name, '득표수': 0}])
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

        # [실시간 업데이트] 현재 후보자 현황
        st.subheader("📋 실시간 후보 현황")
        st.table(df_candidates[['기호', '이름', '득표수']])

        if status == "종료" and st.button("📊 결과 발표"):
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
    if status == "진행중":
        end_time = datetime.strptime(str(df_state.at[0, '종료시간']), "%Y-%m-%d %H:%M:%S")
        remaining = end_time - get_kst()
        
        if remaining.total_seconds() > 0:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.metric("⏳ 남은 시간", f"{mins:02d}:{secs:02d}")
            
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
    else:
        st.warning(f"현재 선거 상태: {status}")
    
    time.sleep(5)
    st.rerun()
