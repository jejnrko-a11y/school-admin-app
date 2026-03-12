import streamlit as st
import pandas as pd
import time
from utils import get_kst

def show_page(conn, user):
    # CSS: 카드 및 버튼 스타일 강화
    st.markdown("""
        <style>
        .candidate-card {
            background: #ffffff;
            border-radius: 15px;
            padding: 20px;
            margin-bottom: 15px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            border-left: 8px solid #3b82f6;
        }
        .stButton>button {
            width: 100%;
            border-radius: 50px;
            font-weight: bold;
            background-color: #3b82f6;
            color: white;
            border: none;
        }
        </style>
    """, unsafe_allow_html=True)

    # 데이터 로드 (생략된 캐싱 함수 사용 가정)
    data = get_data(conn)
    df_elec, df_votes = data['candidates'], data['votes']
    
    st.title("🗳️ 실시간 반장선거")

    # --- 학생 UI: 세련된 카드 레이아웃 ---
    if user['name'] not in ["교사", "관리자"]:
        st.markdown("### 🏆 후보자 목록")
        for _, row in df_elec.iterrows():
            with st.container():
                st.markdown(f"""
                <div class='candidate-card'>
                    <h2 style='margin:0;'>기호 {int(row['기호'])}번 {row['이름']}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                if st.button(f"🗳️ {row['이름']}에게 투표하기", key=f"btn_{row['기호']}"):
                    # 투표 로직 (기존 함수 활용)
                    process_vote(conn, row['이름'], user)
                    st.toast(f"✅ {row['이름']} 후보에게 소중한 한 표를 행사했습니다!", icon="🎉")
                    st.balloons()
                    st.rerun()

    # --- 교사 UI: 박진감 넘치는 순위 시각화 ---
    else:
        if st.button("📊 실시간 긴장감 넘치는 개표"):
            st.subheader("🔥 개표 진행 중...")
            chart_area = st.empty()
            
            # 1위부터 꼴찌까지 서서히 공개되는 로직
            sorted_df = df_elec.sort_values('득표수', ascending=True)
            for i in range(1, len(sorted_df) + 1):
                time.sleep(1.2)
                # progress bar 연출
                progress = i / len(sorted_df)
                st.progress(progress)
                chart_area.bar_chart(sorted_df.tail(i).set_index('이름')['득표수'])
            
            st.success("🎉 당선자가 확정되었습니다!")
            st.balloons()
