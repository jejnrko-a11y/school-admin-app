import streamlit as st
import pandas as pd
import random

def show_page(conn, user):
    st.title("🪑 지능형 조건부 자리배치")

    # --- 1. CSS 스타일 ---
    st.markdown("""
        <style>
        .blackboard {
            background-color: #1e3d2f; color: white; border: 8px solid #5d4037;
            border-radius: 5px; padding: 20px; text-align: center;
            font-size: 24px; font-weight: bold; margin-bottom: 10px;
        }
        .teacher-desk {
            background-color: #8d6e63; width: 120px; height: 50px;
            margin: 0 auto 30px auto; border-radius: 5px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-size: 14px;
        }
        .seat-card {
            background-color: #ffffff; border: 2px solid #e0e0e0;
            border-radius: 10px; padding: 12px 5px; text-align: center;
            margin-bottom: 15px; box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            min-height: 85px; display: flex; align-items: center; justify-content: center;
        }
        .seat-name { font-weight: bold; font-size: 15px; color: #333; line-height: 1.2; }
        .seat-x { color: #ff5252; font-weight: bold; font-size: 20px; }
        .cond-label { font-size: 13px; font-weight: bold; color: #1E3A8A; margin-top: 5px; }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 데이터 로드 ---
    try:
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        all_students = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    fixed_x_coords = [(2, 4), (3, 4)] # E4, E5 고정석

    # --- 3. 교사 전용 조건 설정 폼 ---
    fb_pairs = [] # 앞뒤 짝궁 리스트
    ss_pairs = [] # 양옆 짝궁 리스트
    cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [], []
    
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정 (셔플 시 적용)"):
            st.info("💡 각 짝궁은 2명씩 선택해 주세요. (최대 3커플씩 가능)")
            
            # 앞뒤 짝궁 (세로 인접)
            st.markdown('<p class="cond-label">↕️ 앞뒤 짝궁 지정 (세로로 인접)</p>', unsafe_allow_html=True)
            cols_fb = st.columns(3)
            for i in range(3):
                p = cols_fb[i].multiselect(f"앞뒤 커플 {i+1}", all_students, max_selections=2, key=f"fb_{i}")
                if len(p) == 2: fb_pairs.append(p)

            # 양옆 짝궁 (가로 인접)
            st.markdown('<p class="cond-label">↔️ 양옆 짝궁 지정 (가로로 인접)</p>', unsafe_allow_html=True)
            cols_ss = st.columns(3)
            for i in range(3):
                p = cols_ss[i].multiselect(f"양옆 커플 {i+1}", all_students, max_selections=2, key=f"ss_{i}")
                if len(p) == 2: ss_pairs.append(p)

            st.markdown('<p class="cond-label">🚫 기타 배치 조건</p>', unsafe_allow_html=True)
            cond_sep = st.multiselect("💢 분리 지정 (절대 인접 불가)", all_students)
            cond_front = st.multiselect("📏 앞자리 지정 (1열)", all_students)
            cond_back = st.multiselect("📺 뒷자리 지정 (4열)", all_students)
            cond_win = st.multiselect("🪟 창가 지정 (1분단)", all_students)
            cond_hall = st.multiselect("🚪 복도 지정 (5분단)", all_students)

        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
                success = False
                max_attempts = 20000 
                
                with st.spinner("복합 조건을 만족하는 최적의 배치를 계산 중입니다..."):
                    for attempt in range(max_attempts):
                        shuffled = all_students.copy()
                        random.shuffle(shuffled)
                        
                        temp_grid = [["" for _ in range(5)] for _ in range(4)]
                        s_map = {}
                        s_idx = 0
                        for r in range(4):
                            for c in range(5):
                                if (r, c) in fixed_x_coords:
                                    temp_grid[r][c] = "X"
                                elif s_idx < len(shuffled):
                                    name = shuffled[s_idx]
                                    temp_grid[r][c] = name
                                    s_map[name] = (r, c)
                                    s_idx += 1
                        
                        valid = True
                        
                        # 검증 1: 앞뒤 짝궁 (같은 열, 행 차이 1)
                        for p in fb_pairs:
                            pos1, pos2 = s_map[p[0]], s_map[p[1]]
                            if not (pos1[1] == pos2[1] and abs(pos1[0] - pos2[0]) == 1):
                                valid = False; break
                        
                        # 검증 2: 양옆 짝궁 (같은 행, 열 차이 1)
                        if valid:
                            for p in ss_pairs:
                                pos1, pos2 = s_map[p[0]], s_map[p[1]]
                                if not (pos1[0] == pos2[0] and abs(pos1[1] - pos2[1]) == 1):
                                    valid = False; break

                        # 검증 3: 분리 (상하좌우 인접 불가)
                        if valid and cond_sep and len(cond_sep) > 1:
                            for i in range(len(cond_sep)):
                                for j in range(i + 1, len(cond_sep)):
                                    p1, p2 = s_map[cond_sep[i]], s_map[cond_sep[j]]
                                    if abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) == 1:
                                        valid = False; break
                                if not valid: break

                        # 나머지 조건 검증
                        if valid and cond_front and any(s_map[n][0] != 0 for n in cond_front): valid = False
                        if valid and cond_back and any(s_map[n][0] != 3 for n in cond_back): valid = False
                        if valid and cond_win and any(s_map[n][1] != 0 for n in cond_win): valid = False
                        if valid and cond_hall and any(s_map[n][1] != 4 for n in cond_hall): valid = False
                        
                        if valid:
                            new_df = pd.DataFrame(temp_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                            conn.update(worksheet="자리배치", data=new_df)
                            success = True; break
                
                if success:
                    st.toast("✅ 모든 커플 및 배치 조건을 만족합니다!")
                    st.rerun()
                else:
                    st.error("❌ 조건이 너무 복잡하여 배치를 찾지 못했습니다. 커플 수를 줄이거나 조건을 완화해 주세요.")

        with c2:
            if st.button("🔢 번호순(1분단부터)", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(5)] for _ in range(4)]
                s_idx = 0
                for c in range(5):
                    for r in range(4):
                        if (r, c) in fixed_x_coords: new_grid[r][c] = "X"
                        elif s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]
                            s_idx += 1
                new_df = pd.DataFrame(new_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
                st.rerun()

    # --- 4. 시각적 출력 ---
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)

    for r in range(4):
        cols = st.columns(5)
        for c in range(5):
            val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            with cols[c]:
                if val == "X":
                    st.markdown('<div class="seat-card" style="background-color:#f0f0f0;"><div class="seat-x">X</div></div>', unsafe_allow_html=True)
                elif val.strip() and val != "None":
                    st.markdown(f'<div class="seat-card"><div class="seat-name">{val}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="seat-card" style="border:1px dashed #ccc;"></div>', unsafe_allow_html=True)
