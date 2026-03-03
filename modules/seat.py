import streamlit as st
import pandas as pd
import random

def show_page(conn, user):
    st.title("🪑 교실 자리배치")

    # --- 1. CSS 스타일 정의 ---
    st.markdown("""
        <style>
        .blackboard {
            background-color: #1e3d2f; color: white; border: 8px solid #5d4037;
            border-radius: 5px; padding: 20px; text-align: center;
            font-size: 24px; font-weight: bold; margin-bottom: 10px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.3);
        }
        .teacher-desk {
            background-color: #8d6e63; width: 120px; height: 50px;
            margin: 0 auto 30px auto; border-radius: 5px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-size: 14px;
        }
        .seat-card {
            background-color: #ffffff; border: 2px solid #e0e0e0;
            border-radius: 10px; padding: 15px 5px; text-align: center;
            margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            min-height: 80px; display: flex; align-items: center; justify-content: center;
        }
        .seat-name { font-weight: bold; font-size: 16px; color: #333; }
        .seat-x { color: #ff5252; font-weight: bold; font-size: 20px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 데이터 로드 ---
    try:
        # 자리배치 데이터 (머릿글 포함)
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        
        # 학생명부 데이터 (이름(번호번) 형식 리스트 생성)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        
        # "강건영(1번)" 형식의 리스트 생성
        student_formatted = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # --- 3. 교사 전용 관리 기능 ---
    if user['name'] == "교사":
        c1, c2 = st.columns(2)
        
        # 고정된 X 자리 좌표 (0-indexed: 4행 5열 기준 마지막 열의 아래쪽 두 칸)
        # 이미지 기준: E4(row 2, col 4), E5(row 3, col 4)
        fixed_x_coords = [(2, 4), (3, 4)]

        with c1:
            if st.button("🎲 랜덤 자리 바꾸기", use_container_width=True):
                shuffled = student_formatted.copy()
                random.shuffle(shuffled)
                
                new_data = []
                s_idx = 0
                for r in range(4):
                    row_content = []
                    for c in range(5):
                        if (r, c) in fixed_x_coords:
                            row_content.append("X")
                        else:
                            if s_idx < len(shuffled):
                                row_content.append(shuffled[s_idx])
                                s_idx += 1
                            else:
                                row_content.append("")
                    new_data.append(row_content)
                
                # 시트 업데이트 (머릿글 유지)
                new_df = pd.DataFrame(new_data, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
                st.rerun()

        with c2:
            if st.button("🔢 번호순 초기화", use_container_width=True):
                ordered = student_formatted.copy()
                new_data = []
                s_idx = 0
                for r in range(4):
                    row_content = []
                    for c in range(5):
                        if (r, c) in fixed_x_coords:
                            row_content.append("X")
                        else:
                            if s_idx < len(ordered):
                                row_content.append(ordered[s_idx])
                                s_idx += 1
                            else:
                                row_content.append("")
                    new_data.append(row_content)
                
                new_df = pd.DataFrame(new_data, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
                st.rerun()
        st.divider()

    # --- 4. 시각적 배치 출력 ---
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)

    # 4행 5열 그리드 출력
    for r in range(4):
        cols = st.columns(5)
        for c in range(5):
            # df_seat는 머릿글이 있으므로 iloc으로 데이터 접근
            val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            
            with cols[c]:
                if val == "X":
                    st.markdown('<div class="seat-card" style="background-color:#f0f0f0;"><div class="seat-x">X</div></div>', unsafe_allow_html=True)
                elif val.strip() and val != "None":
                    st.markdown(f'<div class="seat-card"><div class="seat-name">{val}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="seat-card" style="border:1px dashed #ccc;"></div>', unsafe_allow_html=True)

    st.info("💡 오른쪽 아래 'X' 표시는 비어있는 고정석입니다.")
