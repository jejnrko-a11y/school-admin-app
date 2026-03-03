import streamlit as st
import pandas as pd

def show_page(conn):
    st.title("🪑 우리 반 자리배치표")
    st.markdown("### 3학년 2반 교실")

    try:
        # 1. 자리배치 데이터 읽기
        df = conn.read(worksheet="자리배치", ttl=60)
        df = df.fillna('') # 빈자리는 공백 처리

        # 2. 교실 디자인 스타일 적용
        st.markdown("""
            <style>
            .teacher-desk {
                background-color: #4B5563;
                color: white;
                text-align: center;
                padding: 15px;
                border-radius: 10px;
                margin: 20px auto;
                width: 50%;
                font-weight: bold;
                border: 2px solid #1F2937;
            }
            .seat-box {
                background-color: #ffffff;
                border: 2px solid #D1D5DB;
                border-radius: 8px;
                padding: 15px 5px;
                text-align: center;
                margin-bottom: 10px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
                height: 80px;
                display: flex;
                flex-direction: column;
                justify-content: center;
            }
            .seat-name {
                font-weight: bold;
                color: #1E3A8A;
                font-size: 16px;
            }
            .seat-empty {
                color: #D1D5DB;
                font-style: italic;
            }
            </style>
        """, unsafe_allow_html=True)

        # 3. 맨 위에 교탁 배치
        st.markdown('<div class="teacher-desk">🖥️ 교 탁 (칠판 쪽)</div>', unsafe_allow_html=True)
        st.write("")

        # 4. 4x5 자리 배치 (엑셀 행/열 기준)
        # 엑셀의 열을 컬럼으로 사용하여 배치
        for row_idx, row in df.iterrows():
            cols = st.columns(5) # 5열 배치
            for col_idx in range(5):
                # 엑셀의 A, B, C, D, E 열 순서대로
                student_name = row.iloc[col_idx] if col_idx < len(row) else ""
                
                with cols[col_idx]:
                    if student_name.strip():
                        st.markdown(f"""
                            <div class="seat-box">
                                <div class="seat-name">{student_name}</div>
                            </div>
                        """, unsafe_allow_html=True)
                    else:
                        st.markdown("""
                            <div class="seat-box">
                                <div class="seat-empty">빈자리</div>
                            </div>
                        """, unsafe_allow_html=True)

        st.caption("※ 자리배치는 담임 선생님의 계획에 따라 변경될 수 있습니다.")

    except Exception as e:
        st.error(f"자리배치표를 불러올 수 없습니다: {e}")
