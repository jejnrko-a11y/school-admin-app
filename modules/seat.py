import streamlit as st
import pandas as pd
import random
import math
from utils import load_student_list

def show_page(conn, user):
    st.title("🪑 지능형 조건부 자리배치")

    # --- 1. CSS 스타일 ---
    st.markdown("""
        <style>
        .blackboard {
            background-color: #1e3d2f; color: white; border: 8px solid #5d4037;
            border-radius: 5px; padding: 20px; text-align: center;
            font-size: 24px; font-weight: bold; margin-top: 10px; margin-bottom: 20px;
        }
        .teacher-desk {
            background-color: #8d6e63; width: 120px; height: 50px;
            margin: 30px auto 10px auto; border-radius: 5px;
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

    # --- 2. 동적 데이터 로드 및 그리드 계산 ---
    try:
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        
        # utils.py의 동적 함수 사용 (교사/테스트계정 등 자동 제외)
        df_students = load_student_list(conn, exclude_admins=True)
        all_students = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
        
        total_students = len(all_students)
        if total_students == 0:
            st.warning("학생 데이터가 없습니다.")
            return
            
        # [핵심] 학생 수에 따른 행(Row) 개수 동적 계산 (가로 5분단 고정)
        columns_count = 5
        rows_count = math.ceil(total_students / columns_count)
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # --- 3. 교사 전용 조건 설정 폼 ---
    fb_pairs =[] 
    ss_pairs =[] 
    cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [],[]
    cond_fixed_br = "선택 안함"
    
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정 (셔플 시 적용)"):
            st.info(f"💡 현재 학생 수는 총 {total_students}명이며, 자동으로 {rows_count}줄로 배치됩니다.")
            
            st.markdown('<p class="cond-label">🎯 교탁 옆 VIP석 (우측 맨 앞자리)</p>', unsafe_allow_html=True)
            cond_fixed_br = st.selectbox("해당 학생은 무조건 교탁 우측(0행 4열)에 배치됩니다.", ["선택 안함"] + all_students)

            st.markdown('<p class="cond-label">↕️ 앞뒤 짝궁 지정 (세로로 인접)</p>', unsafe_allow_html=True)
            cols_fb = st.columns(3)
            for i in range(3):
                p = cols_fb[i].multiselect(f"앞뒤 커플 {i+1}", all_students, max_selections=2, key=f"fb_{i}")
                if len(p) == 2: fb_pairs.append(p)

            st.markdown('<p class="cond-label">↔️ 양옆 짝궁 지정 (가로로 인접)</p>', unsafe_allow_html=True)
            cols_ss = st.columns(3)
            for i in range(3):
                p = cols_ss[i].multiselect(f"양옆 커플 {i+1}", all_students, max_selections=2, key=f"ss_{i}")
                if len(p) == 2: ss_pairs.append(p)

            st.markdown('<p class="cond-label">🚫 기타 배치 조건</p>', unsafe_allow_html=True)
            cond_sep = st.multiselect("💢 분리 지정 (절대 인접 불가)", all_students)
            cond_front = st.multiselect("📏 앞자리 지정 (1열)", all_students)
            cond_back = st.multiselect(f"📺 뒷자리 지정 ({rows_count}열)", all_students)
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
                        
                        # 고정석 학생 셔플에서 제외
                        if cond_fixed_br != "선택 안함" and cond_fixed_br in shuffled:
                            shuffled.remove(cond_fixed_br)
                        
                        random.shuffle(shuffled)
                        
                        # 동적 그리드 생성
                        temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                        s_map = {}
                        s_idx = 0
                        
                        for r in range(rows_count):
                            for c in range(columns_count):
                                # 우선순위 1: 고정석 (0행 4열)
                                if cond_fixed_br != "선택 안함" and r == 0 and c == columns_count - 1:
                                    temp_grid[r][c] = cond_fixed_br
                                    s_map[cond_fixed_br] = (0, c)
                                # 우선순위 2: 셔플된 학생 배치
                                elif s_idx < len(shuffled):
                                    name = shuffled[s_idx]
                                    temp_grid[r][c] = name
                                    s_map[name] = (r, c)
                                    s_idx += 1
                                # 우선순위 3: 학생 수가 그리드보다 작을 때 남는 자리는 "X"
                                else:
                                    temp_grid[r][c] = "X"
                        
                        valid = True
                        
                        # 검증 1: 앞뒤 짝궁
                        for p in fb_pairs:
                            pos1, pos2 = s_map[p[0]], s_map[p[1]]
                            if not (pos1[1] == pos2[1] and abs(pos1[0] - pos2[0]) == 1):
                                valid = False; break
                        
                        # 검증 2: 양옆 짝궁
                        if valid:
                            for p in ss_pairs:
                                pos1, pos2 = s_map[p[0]], s_map[p[1]]
                                if not (pos1[0] == pos2[0] and abs(pos1[1] - pos2[1]) == 1):
                                    valid = False; break

                        # 검증 3: 분리
                        if valid and cond_sep and len(cond_sep) > 1:
                            for i in range(len(cond_sep)):
                                for j in range(i + 1, len(cond_sep)):
                                    p1, p2 = s_map[cond_sep[i]], s_map[cond_sep[j]]
                                    if abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) == 1:
                                        valid = False; break
                                if not valid: break

                        # 검증 4: 기타 위치
                        if valid and cond_front and any(s_map[n][0] != 0 for n in cond_front): valid = False
                        if valid and cond_back and any(s_map[n][0] != rows_count - 1 for n in cond_back): valid = False
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
                new_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                s_idx = 0
                for c in range(columns_count):
                    for r in range(rows_count):
                        if s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]
                            s_idx += 1
                        else:
                            new_grid[r][c] = "X"
                            
                new_df = pd.DataFrame(new_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
                st.rerun()

    # --- 4. 시각적 출력 ---
    st.markdown("<h4 style='text-align: center; color: #555;'>뒷자리 (Back)</h4>", unsafe_allow_html=True)

    # UI 역순 렌더링: (최대 행 - 1) 부터 0행까지 거꾸로
    for r in range(rows_count - 1, -1, -1):
        cols = st.columns(columns_count)
        for c in range(columns_count):
            try:
                val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except IndexError:
                val = ""
                
            with cols[c]:
                if val == "X":
                    st.markdown('<div class="seat-card" style="background-color:#f0f0f0;"><div class="seat-x">X</div></div>', unsafe_allow_html=True)
                elif val.strip() and val != "None":
                    st.markdown(f'<div class="seat-card"><div class="seat-name">{val}</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown('<div class="seat-card" style="border:1px dashed #ccc;"></div>', unsafe_allow_html=True)

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)
