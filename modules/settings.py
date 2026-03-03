import streamlit as st
import pandas as pd

def show_page(conn):
    st.title("🪑 우리 반 자리배치표")
    st.markdown("### 3학년 2반 교실 Layout")

    try:
        # 1. 구글 시트에서 자리배치 탭 읽기
        df = conn.read(worksheet="자리배치", ttl=60)
        df = df.fillna('') # 빈칸 처리

        # 2. 교실 디자인 스타일
        st.markdown("""
            <style>
            .teacher-desk {
                background-color: #4B5563; color: white; text-align: center;
                padding: 15px; border-radius: 10px; margin: 20px auto;
                width: 50%; font-weight: bold; border: 2px solid #1F2937;
            }
            .seat-box {
                background-color: #ffffff; border: 2px solid #D1D5DB;
                border-radius: 8px; padding: 15px 5px; text-align: center;
                margin-bottom: 10px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                height: 80px; display: flex; flex-direction: column; justify-content: center;
            }
            .seat-name { font-weight: bold; color: #1E3A8A; font-size: 16px; }
            </style>
        """, unsafe_allow_html=True)

        # 3. 교탁 배치
        st.markdown('<div class="teacher-desk">🖥️ 교 탁 (칠판 방향)</div>', unsafe_allow_html=True)

        # 4. 4행 5열 배치 (엑셀 데이터 기준)
        for _, row in df.iterrows():
            cols = st.columns(5)
            for i in range(5):
                # 엑셀 열 개수가 5개보다 적을 경우를 대비
                name = row.iloc[i] if i < len(row) else ""
                with cols[i]:
                    if str(name).strip():
                        st.markdown(f'<div class="seat-box"><div class="seat-name">{name}</div></div>', unsafe_allow_html=True)
                    else:
                        st.markdown('<div class="seat-box" style="background-color:#f9fafb; border-style:dashed;"></div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"자리배치 데이터를 불러오지 못했습니다. 시트 이름을 확인하세요: {e}")
