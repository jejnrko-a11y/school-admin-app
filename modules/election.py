import streamlit as st
import pandas as pd
import time
from datetime import datetime, timedelta
from utils import get_kst, load_student_list

@st.cache_data(ttl=5)
def get_data(_conn):
    try:
        state = _conn.read(worksheet="선거상태", ttl=0)
        candidates = _conn.read(worksheet="후보자명단", ttl=0)
        votes = _conn.read(worksheet="투표기록", ttl=0)
        # 헤더 공백 제거
        state.columns = state.columns.str.strip()
        candidates.columns = candidates.columns.str.strip()
        votes.columns = votes.columns.str.strip()
        return {"state": state, "candidates": candidates, "votes": votes}
    except:
        return None

def show_page(conn, user):
    st.title("🗳️ 실시간 반장선거")
    
    data = get_data(conn)
    if not data:
        st.error("데이터 로드 실패: 시트 이름과 헤더를 확인하세요.")
        return
        
    df_state, df_candidates, df_votes = data['state'], data['candidates'], data['votes']
    status = df_state.at[0, '상태']
    
    # 1. 교사 관리 영역
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 교사 관리 도구")
        student_list = load_student_list(conn, exclude_admins=True)
        
        with st.expander("➕ 후보자 등록"):
            with st.form("add_cand"):
                # '이름' 컬럼 존재 확인
                if '이름' in student_list.columns:
                    selected_name = st.selectbox("후보자 선택", student_list['이름'].tolist())
                else:
                    selected_name = st.text_input("이름 (학생명부 '이름' 컬럼 확인 필요)")
                    
                if st.form_submit_button("등록"):
                    new_cand = pd.DataFrame([{'기호': int(len(df_candidates)+1), '이름': selected_name, '득표수': 0}])
                    conn.update(worksheet="후보자명단", data=pd.concat([df_candidates, new_cand], ignore_index=True))
                    st.cache_data.clear(); st.rerun()

        if status != "진행중" and st.button("🚀 선거 시작 (2분)"):
            end_time = get_kst() + timedelta(minutes=2)
            df_state.at[0, '상태'] = "진행중"; df_state.at[0, '종료시간'] = end_time.strftime("%Y-%m-%d %H:%M:%S")
            conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear(); st.rerun()

        if status == "종료" and st.button("📊 결과 발표 (긴장감 모드)"):
            st.write("### 🥁 당선자 발표!")
            # 득표수를 0부터 실제값까지 천천히 올림
            chart_data = {row['이름']: 0 for _, row in df_candidates.iterrows()}
            chart_placeholder = st.empty()
            
            for score in range(int(df_candidates['득표수'].max()) + 1):
                for _, row in df_candidates.iterrows():
                    if score <= int(row['득표수']):
                        chart_data[row['이름']] = score
                chart_placeholder.bar_chart(pd.Series(chart_data))
                time.sleep(0.5)
            st.balloons()
            return
        return

    # 2. 학생 투표 영역
    if status == "진행중":
        end_time = datetime.strptime(str(df_state.at[0, '종료시간']), "%Y-%m-%d %H:%M:%S")
        remaining = end_time - get_kst()
        
        if remaining.total_seconds() > 0:
            mins, secs = divmod(int(remaining.total_seconds()), 60)
            st.metric("⏳ 남은 시간", f"{mins:02d}:{secs:02d}")
            
            # 투표 완료 여부 엄격 체크 (학번 기반)
            if not df_votes.empty and str(user['num']) in df_votes['학번'].astype(str).values:
                st.success("✅ 이미 투표를 완료하셨습니다.")
            else:
                # 기호 정수화 출력
                df_candidates['기호'] = df_candidates['기호'].astype(int)
                options = {f"{int(row['기호'])}번. {row['이름']}": row['이름'] for _, row in df_candidates.iterrows()}
                choice = st.radio("후보 선택", list(options.keys()))
                
                if st.button("투표 제출"):
                    candidate_name = options[choice]
                    df_candidates.loc[df_candidates['이름'] == candidate_name, '득표수'] += 1
                    conn.update(worksheet="후보자명단", data=df_candidates)
                    
                    new_vote = pd.DataFrame([{'학번': user['num'], '이름': user['name'], '투표완료여부': 'O'}])
                    conn.update(worksheet="투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.cache_data.clear(); st.rerun()
        else:
            df_state.at[0, '상태'] = "종료"; conn.update(worksheet="선거상태", data=df_state)
            st.cache_data.clear(); st.rerun()
    else:
        st.warning(f"현재 선거 상태: {status}")
    
    time.sleep(5); st.rerun()
