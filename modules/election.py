import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from streamlit_autorefresh import st_autorefresh
from utils import get_kst

def show_page(conn, user):
    # 1초마다 자동 새로고침 (실시간 타이머/상태 반영용)
    st_autorefresh(interval=1000, key="elec_refresh")
    
    st.title("🗳️ 실시간 반장선거")
    
    # 데이터 로드
    df_state = conn.read(worksheet="선거상태", ttl=0)
    df_candidates = conn.read(worksheet="후보자명단", ttl=0)
    df_votes = conn.read(worksheet="투표기록", ttl=0)
    
    status = df_state.at[0, '상태']
    end_time_str = df_state.at[0, '종료시간']
    
    # --- 교사(관리자) 관리 영역 ---
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 선거 관리 도구")
        
        with st.expander("후보자 등록"):
            with st.form("add_cand"):
                name = st.text_input("이름")
                promise = st.text_input("공약")
                if st.form_submit_button("등록"):
                    new_cand = pd.DataFrame([{'기호': len(df_candidates)+1, '이름': name, '공약': promise, '득표수': 0}])
                    conn.update(worksheet="후보자명단", data=pd.concat([df_candidates, new_cand]))
                    st.rerun()

        if status != "진행중" and st.button("🚀 선거 시작 (2분)"):
            end_time = get_kst() + timedelta(minutes=2)
            df_state.at[0, '상태'] = "진행중"
            df_state.at[0, '종료시간'] = end_time.strftime("%Y-%m-%d %H:%M:%S")
            conn.update(worksheet="선거상태", data=df_state)
            st.rerun()

        if status == "종료" and st.button("📊 결과 발표 (긴장감 모드)"):
            st.write("### 🥁 선거 결과 발표 중...")
            bar_container = st.empty()
            # 1위부터 순차적 공개 연출
            sorted_df = df_candidates.sort_values('득표수', ascending=True)
            for i in range(1, len(sorted_df) + 1):
                time.sleep(1.5)
                bar_container.bar_chart(sorted_df.tail(i).set_index('이름')['득표수'])
            st.balloons()
        return

    # --- 학생 UI 영역 ---
    if status == "진행전":
        st.info("현재 진행 중인 선거가 없습니다.")
    elif status == "진행중":
        # 타이머 로직
        end_time = datetime.strptime(end_time_str, "%Y-%m-%d %H:%M:%S")
        remaining = end_time - get_kst()
        
        if remaining.total_seconds() > 0:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.metric("남은 시간", f"{mins:02d}:{secs:02d}")
            
            # 투표 확인
            if not df_votes[(df_votes['학번'] == user['num']) & (df_votes['투표완료여부'] == "O")].empty:
                st.success("✅ 투표를 완료하셨습니다.")
            else:
                choice = st.radio("후보 선택", df_candidates['이름'])
                if st.button("투표 제출"):
                    df_candidates.loc[df_candidates['이름'] == choice, '득표수'] += 1
                    conn.update(worksheet="후보자명단", data=df_candidates)
                    new_vote = pd.DataFrame([{'학번': user['num'], '이름': user['name'], '투표완료여부': 'O'}])
                    conn.update(worksheet="투표기록", data=pd.concat([df_votes, new_vote]))
                    st.rerun()
        else:
            # 시간 종료 시 자동 상태 변경
            df_state.at[0, '상태'] = "종료"
            conn.update(worksheet="선거상태", data=df_state)
            st.rerun()
    else:
        st.warning("선거가 종료되었습니다.")
