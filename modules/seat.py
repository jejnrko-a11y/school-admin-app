import streamlit as st
import pandas as pd
import random

def show_page(conn, user):
    st.title("🪑 지능형 조건부 자리배치")

    # --- 1. CSS 스타일 (교실 테마) ---
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
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 데이터 로드 및 전처리 ---
    try:
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        df_students = conn.read(worksheet="학생명부", ttl=0)
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = pd.to_numeric(df_students['번호'], errors='coerce').fillna(0).astype(int)
        df_students = df_students.sort_values(by='번호')
        
        # 전체 학생 리스트 (이름(번호번) 형식)
        all_students = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # 고정석 X 좌표 (E4, E5 -> 5분단 아래쪽 두 칸)
    fixed_x_coords = [(2, 4), (3, 4)]

    # --- 3. 교사 전용 조건 설정 폼 ---
    cond_adj, cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [], [], []
    
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정 (셔플 시 적용)"):
            st.info("💡 왼쪽(1분단)이 창가, 오른쪽(5분단)이 복도입니다.")
            cond_adj = st.multiselect("🤝 옆자리 지정 (서로 인접해야 함)", all_students)
            cond_sep = st.multiselect("💢 분리 지정 (서로 인접 불가)", all_students)
            cond_front = st.multiselect("📏 앞자리 지정 (1열 배치)", all_students)
            cond_back = st.multiselect("📺 뒷자리 지정 (4열 배치)", all_students)
            cond_win = st.multiselect("🪟 창가 지정 (왼쪽 1분단 배치)", all_students)
            cond_hall = st.multiselect("🚪 복도 지정 (오른쪽 5분단 배치)", all_students)

        c1, c2 = st.columns(2)
        
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
                success = False
                max_attempts = 15000 # 조건이 늘어났으므로 시도 횟수 상향
                
                with st.spinner("최적의 배치를 계산 중입니다..."):
                    for attempt in range(max_attempts):
                        # 1. 셔플
                        shuffled = all_students.copy()
                        random.shuffle(shuffled)
                        
                        # 2. 가상 그리드 배치 (X자리 고려)
                        temp_grid = [["" for _ in range(5)] for _ in range(4)]
                        s_map = {} # 이름: (r, c) 매핑 저장
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
                        
                        # 3. 조건 검증 로직
                        valid = True
                        
                        # 검증 함수: 인접 여부 (상하좌우)
                        def is_neighbor(p1, p2):
                            return abs(p1[0] - p2[0]) + abs(p1[1] - p2[1]) == 1

                        # 조건 1: 옆자리 (선택된 이들이 서로 인접)
                        if cond_adj and len(cond_adj) > 1:
                            for name in cond_adj:
                                if not any(is_neighbor(s_map[name], s_map[other]) for other in cond_adj if name != other):
                                    valid = False; break
                        
                        # 조건 2: 분리 (선택된 이들끼리 누구도 인접 불가)
                        if valid and cond_sep and len(cond_sep) > 1:
                            for i in range(len(cond_sep)):
                                for j in range(i + 1, len(cond_sep)):
                                    if is_neighbor(s_map[cond_sep[i]], s_map[cond_sep[j]]):
                                        valid = False; break
                                if not valid: break

                        # 조건 3: 앞자리 (Row 0)
                        if valid and cond_front:
                            if any(s_map[name][0] != 0 for name in cond_front):
                                valid = False
                        
                        # 조건 4: 뒷자리 (Row 3)
                        if valid and cond_back:
                            if any(s_map[name][0] != 3 for name in cond_back):
                                valid = False
                        
                        # 조건 5: 창가 지정 (Col 0 - 1분단)
                        if valid and cond_win:
                            if any(s_map[name][1] != 0 for name in cond_win):
                                valid = False
                        
                        # 조건 6: 복도 지정 (Col 4 - 5분단)
                        if valid and cond_hall:
                            # 5분단 아래쪽 X자리는 배정되지 않으므로 자동 필터링됨
                            if any(s_map[name][1] != 4 for name in cond_hall):
                                valid = False
                        
                        if valid:
                            # 모든 조건 만족 시 시트 업데이트
                            new_df = pd.DataFrame(temp_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                            conn.update(worksheet="자리배치", data=new_df)
                            success = True
                            break
                
                if success:
                    st.toast("✅ 조건을 모두 만족하는 배치를 찾았습니다!")
                    st.rerun()
                else:
                    st.error("❌ 조건이 너무 까다로워 배치를 찾지 못했습니다. 조건을 조금만 완화해 주세요.")

        with c2:
            if st.button("🔢 번호순(1분단부터)", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(5)] for _ in range(4)]
                s_idx = 0
                for c in range(5):
                    for r in range(4):
                        if (r, c) in fixed_x_coords:
                            new_grid[r][c] = "X"
                        elif s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]
                            s_idx += 1
                
                new_df = pd.DataFrame(new_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
                st.rerun()
        st.divider()

    # --- 4. 시각적 배치 출력 (창가/복도 정보 표시) ---
    col_info1, col_info2, col_info3 = st.columns([1, 3, 1])
    col_info1.markdown("<div style='text-align:center; color:#666;'>🪟 창가</div>", unsafe_allow_html=True)
    col_info3.markdown("<div style='text-align:center; color:#666;'>🚪 복도</div>", unsafe_allow_html=True)

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

    st.info("💡 1분단(왼쪽)이 창가석, 5분단(오른쪽)이 복도석입니다.")
