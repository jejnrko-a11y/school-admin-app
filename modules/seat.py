import streamlit as st
import pandas as pd
import random

def show_page(conn, user):
    st.title("🪑 교실 자리배치")

    # --- 1. CSS 스타일 정의 (교실 분위기) ---
    st.markdown("""
        <style>
        .blackboard {
            background-color: #1e3d2f;
            color: white;
            border: 8px solid #5d4037;
            border-radius: 5px;
            padding: 20px;
            text-align: center;
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .teacher-desk {
            background-color: #8d6e63;
            width: 120px;
            height: 50px;
            margin: 0 auto 30px auto;
            border-radius: 5px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-weight: bold;
            font-size: 14px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
        }
        .seat-card {
            background-color: #ffffff;
            border: 2px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px 5px;
            text-align: center;
            margin-bottom: 15px;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            min-height: 70px;
            display: flex;
            flex-direction: column;
            justify-content: center;
        }
        .seat-name {
            font-weight: bold;
            font-size: 18px;
            color: #333;
        }
        .seat-empty {
            color: #ccc;
            font-style: italic;
            font-size: 14px;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 데이터 로드 ---
    try:
        # 자리배치 데이터 (4행 5열)
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        
        # 학생명부 데이터 (초기화/셔플용 명단 추출)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        student_names = df_students['이름'].tolist()
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")
        return

    # --- 3. 교사 전용 버튼 영역 ---
    if user['name'] == "교사":
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🎲 랜덤 자리 바꾸기", use_container_width=True):
                # 명단 섞기
                shuffled = student_names.copy()
                random.shuffle(shuffled)
                
                # 4x5 구조로 재배치 (빈자리는 빈 문자열)
                new_seats = []
                for i in range(4):
                    row = []
                    for j in range(5):
                        idx = i * 5 + j
                        row.append(shuffled[idx] if idx < len(shuffled) else "")
                    new_seats.append(row)
                
                new_df = pd.DataFrame(new_seats)
                conn.update(worksheet="자리배치", data=new_df)
                st.toast("자리가 랜덤하게 섞였습니다!")
                st.rerun()
                
        with c2:
            if st.button("🔢 번호순(초기화)", use_container_width=True):
                # 번호순 명단 배치 (강건영부터 시작)
                ordered = student_names.copy()
                new_seats = []
                for i in range(4):
                    row = []
                    for j in range(5):
                        idx = i * 5 + j
                        row.append(ordered[idx] if idx < len(ordered) else "")
                    new_seats.append(row)
                
                new_df = pd.DataFrame(new_seats)
                conn.update(worksheet="자리배치", data=new_df)
                st.toast("번호순으로 자리가 배치되었습니다.")
                st.rerun()
        st.divider()

    # --- 4. 교실 레이아웃 렌더링 ---
    # 칠판 및 교탁
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)

    # 학생 책상 그리드 (4행 5열)
    for r in range(4):
        cols = st.columns(5)
        for c in range(5):
            name = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            
            with cols[c]:
                if name.strip() and name != "None" and name != "":
                    st.markdown(f"""
                        <div class="seat-card">
                            <div class="seat-name">{name}</div>
                        </div>
                    """, unsafe_allow_html=True)
                else:
                    st.markdown(f"""
                        <div class="seat-card" style="background-color: #f9f9f9; border: 1px dashed #ccc;">
                            <div class="seat-empty">빈자리</div>
                        </div>
                    """, unsafe_allow_html=True)

    st.info("💡 위 화면은 교실 앞쪽(칠판)에서 바라본 시점입니다.")
