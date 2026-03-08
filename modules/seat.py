import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (시간표 모듈 스타일 적용 및 모바일 5열 유지) ---
    st.markdown("""
        <style>
        /* 웹 화면 기본 설정 및 불필요한 선 제거 */
        [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
        hr { display: none !important; }

        /* [좌석표 그리드] 모바일에서도 5열 유지 */
        .seat-grid {
            display: grid; 
            grid-template-columns: repeat(5, 1fr);
            gap: 8px !important; 
            width: 100% !important;
            margin-top: 10px !important;
        }
        .seat-container {
            background-color: #ffffff !important; 
            border: 1px solid #E0E0E0 !important; 
            border-radius: 8px !important; 
            padding: 8px 2px !important; 
            text-align: center !important;
            min-height: 60px !important;
            display: flex !important; 
            align-items: center !important; 
            justify-content: center !important;
            box-shadow: 1px 1px 3px rgba(0,0,0,0.02) !important;
            -webkit-print-color-adjust: exact;
        }
        .seat-name { 
            font-weight: 700 !important; 
            font-size: 11px !important; 
            color: #000000 !important; 
            line-height: 1.1 !important; 
        }
        .seat-x { 
            color: #E74C3C !important; 
            font-weight: bold !important; 
            font-size: 16px !important; 
            -webkit-print-color-adjust: exact; 
        }

        /* [교탁 및 칠판 간격 조정] */
        .teacher-desk {
            background-color: #8d6e63 !important; 
            width: 90px !important; 
            height: 35px !important;
            margin: 40px auto 40px auto !important; 
            border-radius: 4px !important;
            display: flex !important; 
            align-items: center !important; 
            justify-content: center !important;
            color: white !important; 
            font-weight: bold !important; 
            font-size: 13px !important;
            -webkit-print-color-adjust: exact;
        }
        .blackboard {
            background-color: #1e3d2f !important; 
            color: white !important; 
            border: 5px solid #5d4037 !important;
            border-radius: 5px !important; 
            padding: 12px !important; 
            text-align: center !important; 
            font-size: 20px !important; 
            font-weight: bold !important;
            margin-top: 0px !important;
            -webkit-print-color-adjust: exact;
        }

        /* 인쇄 시 레이아웃 */
        @media print {
            @page { size: A4 landscape; margin: 10mm; }
            header, footer, .stSidebar, .stButton, .stExpander, .stAlert, [data-testid="stHeader"] { display: none !important; }
            .print-area { display: block !important; width: 100% !important; }
            .seat-container { border: 2px solid #333 !important; min-height: 100px !important; }
            .seat-name { font-size: 18px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. [제목 및 부제목] 시간표 디자인과 동일하게 적용 ---
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    st.title("🪑 학급 자리배치")
    st.markdown("### 3학년 2반 (컴퓨터전자과)")

    # 데이터 로드
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

    fixed_x_coords = [(0, 0), (1, 0)] # 5분단 뒷자리 X

    # --- 4. 교사용 관리 도구 (인쇄 시 자동 숨김) ---
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 조건 설정 및 도구"):
            st.info("💡 오른쪽(1분단)이 창가, 왼쪽(5분단)이 복도입니다.")
            
            fb_pairs, ss_pairs = [], []
            col_fb = st.columns(3)
            for i in range(3):
                p = col_fb[i].multiselect(f"앞뒤 커플 {i+1}", all_students, max_selections=2, key=f"fb_{i}")
                if len(p) == 2: fb_pairs.append(p)
            
            col_ss = st.columns(3)
            for i in range(3):
                p = col_ss[i].multiselect(f"양옆 커플 {i+1}", all_students, max_selections=2, key=f"ss_{i}")
                if len(p) == 2: ss_pairs.append(p)

            cond_sep = st.multiselect("💢 분리 지정", all_students)
            cond_front = st.multiselect("📏 앞자리 (1열/아래)", all_students)
            cond_back = st.multiselect("📺 뒷자리 (4열/위)", all_students)
            cond_win = st.multiselect("🪟 창가 (1분단/오른쪽)", all_students)
            cond_hall = st.multiselect("🚪 복도 (5분단/왼쪽)", all_students)

            c1, c2, c3 = st.columns(3)
            with c1:
                if st.button("🎲 조건부 셔플", use_container_width=True):
                    success = False
                    with st.spinner("최적의 배치를 계산 중..."):
                        for _ in range(20000):
                            shuff = all_students.copy(); random.shuffle(shuff)
                            grid = [["" for _ in range(5)] for _ in range(4)]
                            s_map, s_idx = {}, 0
                            for r in range(4):
                                for c in range(5):
                                    if (r, c) in fixed_x_coords: grid[r][c] = "X"
                                    elif s_idx < len(shuff):
                                        name = shuff[s_idx]; grid[r][c] = name; s_map[name] = (r, c); s_idx += 1
                            
                            valid = True
                            for p in fb_pairs:
                                if p[0] not in s_map or p[1] not in s_map:
                                    valid = False; break
                                p1, p2 = s_map[p[0]], s_map[p[1]]
                                if not (p1[1] == p2[1] and abs(p1[0]-p2[0]) == 1): valid = False; break
                            if valid:
                                for p in ss_pairs:
                                    if p[0] not in s_map or p[1] not in s_map:
                                        valid = False; break
                                    p1, p2 = s_map[p[0]], s_map[p[1]]
                                    if not (p1[0] == p2[0] and abs(p1[1]-p2[1]) == 1): valid = False; break
                            if valid and cond_sep:
                                for i in range(len(cond_sep)):
                                    for j in range(i+1, len(cond_sep)):
                                        p1, p2 = s_map[cond_sep[i]], s_map[cond_sep[j]]
                                        if abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) == 1: valid = False; break
                            if valid and cond_front and any(s_map[n][0] != 3 for n in cond_front): valid = False
                            if valid and cond_back and any(s_map[n][0] != 0 for n in cond_back): valid = False
                            if valid and cond_win and any(s_map[n][1] != 4 for n in cond_win): valid = False
                            if valid and cond_hall and any(s_map[n][1] != 0 for n in cond_hall): valid = False
                            if valid:
                                conn.update(worksheet="자리배치", data=pd.DataFrame(grid)); success = True; break
                    if success: st.rerun()
                    else: st.error("조건에 맞는 배치를 찾지 못했습니다.")
            with c2:
                if st.button("🔢 번호순 정렬", use_container_width=True):
                    ordered = all_students.copy()
                    new_grid = [["" for _ in range(5)] for _ in range(4)]
                    for rx, cx in fixed_x_coords: new_grid[rx][cx] = "X"
                    s_idx = 0
                    for c in range(4, -1, -1):
                        for r in range(3, -1, -1):
                            if new_grid[r][c] == "X": continue
                            if s_idx < len(ordered):
                                new_grid[r][c] = ordered[s_idx]; s_idx += 1
                    conn.update(worksheet="자리배치", data=pd.DataFrame(new_grid)); st.rerun()
            with c3:
                if st.button("🖨️ 자리배치 인쇄", use_container_width=True):
                    components.html("<script>window.parent.print();</script>", height=0)

    # --- 5. 학생 자리 그리드 ---
    grid_html = '<div class="seat-grid">'
    for r in range(4):
        for c in range(5):
            try: val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except: val = ""
            if val == "X": grid_html += '<div class="seat-container" style="background-color:#F5F5F5;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None": grid_html += f'<div class="seat-container"><div class="seat-name">{val}</div></div>'
            else: grid_html += '<div class="seat-container" style="border:1px dashed #DDD !important;"></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # --- 6. 교탁 및 칠판 (간격 확보) ---
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) # print-area 끝
