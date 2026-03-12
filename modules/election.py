import streamlit as st
import pandas as pd
from utils import get_kst, load_class_info

def show_page(conn, user):
    st.title("🗳️ 반장선거")
    
    # 데이터 로드
    df_candidates = conn.read(worksheet="반장선거_후보", ttl=0)
    df_votes = conn.read(worksheet="반장선거_투표기록", ttl=0)
    class_info = load_class_info(conn)
    
    # 투표 여부 체크
    has_voted = not df_votes[df_votes['번호'] == user['num']].empty
    
    # 관리자/교사 전용 대시보드
    if user['name'] in ["교사", "관리자"]:
        st.subheader("📊 선거 진행 상황")
        
        # 투표율 계산
        total_students = class_info['student_count']
        current_votes = len(df_votes)
        col1, col2 = st.columns(2)
        col1.metric("투표율", f"{(current_votes/total_students)*100:.1f}%", f"{current_votes}/{total_students}명")
        
        # 시각화
        chart_data = df_candidates.set_index('이름')['득표수']
        st.bar_chart(chart_data)
        
        st.divider()
        st.subheader("📋 후보 목록 (교사용)")
        st.dataframe(df_candidates)
        return

    # 학생 화면
    if has_voted:
        st.success("✅ 이미 투표를 완료하셨습니다. 결과 발표를 기다려 주세요.")
    else:
        st.info("💡 후보자의 공약을 확인하고 투표해 주세요.")
        
    for _, row in df_candidates.iterrows():
        with st.container(border=True):
            st.markdown(f"### 기호 {row['기호']}. {row['이름']}")
            st.write(f"**공약:** {row['공약']}")
            
            if st.button(f"{row['이름']}에게 투표하기", key=f"vote_{row['기호']}", disabled=has_voted):
                # 1. 득표수 업데이트
                df_candidates.loc[df_candidates['기호'] == row['기호'], '득표수'] += 1
                conn.update(worksheet="반장선거_후보", data=df_candidates)
                
                # 2. 투표 기록 추가 (비밀 투표 보장: 누구에게 투표했는지는 저장하지 않음)
                new_vote = pd.DataFrame([{
                    "번호": user['num'], "이름": user['name'], "투표일시": get_kst().strftime("%Y-%m-%d %H:%M:%S")
                }])
                conn.update(worksheet="반장선거_투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                
                st.rerun()
