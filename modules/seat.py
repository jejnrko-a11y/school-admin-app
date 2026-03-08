import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (상단 여백 제거 및 요소 간격 최적화) ---
    st.markdown("""
        <style>
        /* 웹 화면 상단 여백 제거 및 기본 선 숨기기 */
        .block-container {
            padding-top: 1rem !important;
            padding-bottom: 0rem !important;
        }
        [data-testid="stHeader"], [data-testid="stDecoration"] {
            display: none !important;
        }
        hr { display: none !important; }

        /* [제목] 최상단 배치용 스타일 */
        .main-title {
            font-size: 28px;
            font-weight: bold;
            text-align: center;
            margin-top: 0px !important;
            margin-bottom: 20px !important;
            color: #1a1a1a;
            width: 100%;
        }

        /* 좌석 그리드 */
        .seat-grid {
            display: grid; 
            grid-template-columns: repeat(5, 1fr);
            gap: 5px; 
            width: 100%; 
            margin: 0 auto !important;
        }
        .seat-container {
            background-color: #ffffff !important; 
            border: 1px solid #ccc;
            border-radius: 5px; 
            padding: 4px 2px; 
            text-align: center;
            min-height: 52px;
            display: flex; 
            align-items: center; 
            justify-content: center;
            -webkit-print-color-adjust: exact;
        }
        .seat-name { font-weight: bold; font-size: 11px; color: #333; line-height: 1.1; }
        .seat-x { color: #ff5252 !important; font-weight: bold; font-size: 14px; -webkit-print-color-adjust: exact; }

        /* 하단 요소 (교탁, 칠판) */
        .teacher-desk {
            background-color: #8d6e63 !important; 
            width: 70px; 
            height: 25px;
            margin: 10px auto 5px auto !important;
            border-radius: 3px;
            display: flex; 
            align-items: center; 
            justify-content: center;
            color: white !important; 
            font-weight: bold; 
            font-size: 11px;
            -webkit-print-color-adjust: exact;
        }
        .blackboard {
            background-color: #1e3d2f !important; 
            color: white !important; 
            border: 4px solid #5d4037;
            border-radius: 4px; 
            padding: 8px; 
            text-align: center;
            font-size: 18px; 
            font-weight: bold; 
            margin-top: 0px !important;
            -webkit-print-color-adjust: exact;
        }

        /* [인쇄 설정] */
        @media print {
            @page { size: A4 landscape; margin: 8mm; }
            
            /* 메뉴, 버튼, 설정창 등 인쇄에서 완전 제외 */
            header, footer, .stSidebar, .stButton, .stExpander, .stAlert, 
            [data-testid="stHeader"], [data-testid="stDecoration"], 
            [data-testid="stTitleBlock"], hr {
                display: none !important;
            }
            
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            .print-area { display: block !important; width: 100% !important; }

            /* 인쇄 시 제목 및 카드 크기 조정 */
            .main-title { font-size: 26px !important; margin-bottom: 15px !important; }
            .seat-container { border: 1.5px solid #000 !important; min-height: 80px !important; }
            .seat-name { font-size: 16px !important; }
            .teacher-desk { margin: 10px auto !important; height: 35px !important; font-size: 14px !important; }
            .blackboard { padding: 15px !important; font-size: 24px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 최상단 제목 표시 ---
    # st.title() 대신 HTML을 사용하여 최상단에 고정
    st.markdown('<div class="main-title">💡 컴퓨터전자 3-2반 자리배치</div>', unsafe_allow_html=True)

    # --- 3. 데이터 로드 ---
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

    # --- 4. 교사용 관리 도구 (웹 전용) ---
    if user['name'] == "교사":
        with st.expander("⚙️ 조건 설정"):
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
            cond_front = st.multiselect("📏 앞자리 (1열)", all_students)
            cond_back = st.multiselect("📺 뒷자리 (4열)", all_students)
            cond_win = st.multiselect("🪟 창가 (1분단)", all_students)
            cond_hall = st.multiselect("🚪 복도 (5분단)", all_students)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎲 자리 셔플", use_container_width=True):
                success = False
                with st.spinner("계산 중..."):
                    for _ in range(20000):
                        shuff = all_students.copy()
                        random.shuffle(shuff)
                        grid = [["" for _ in range(5)] for _ in range(4)]
                        s_map = {}
                        s_idx = 0
                        for r in range(4):
                            for c in range(5):
                                if (r, c) in fixed_x_coords: grid[r][c] = "X"
                                elif s_idx < len(shuff):
                                    name = shuff[s_idx]; grid[r][c] = name
                                    s_map[name] = (r, c); s_idx += 1
                        valid = True
                        for p in fb_pairs:
                            p1, p2 = s_map[p[0]], s_map[p[1]]
                            if not (p1[1] == p2[1] and abs(p1[0]-p2[0]) == 1): valid = False; break
                        if valid:
                            for p in ss_pairs:
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
                            conn.update(worksheet="자리배치", data=pd.DataFrame(grid))
                            success = True; break
                if success: st.rerun()
                else: st.error("조건에 맞는 배치를 찾지 못했습니다.")

        with c2:
            if st.button("🔢 번호순", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(5)] for _ in range(4)]
                for rx, cx in fixed_x_coords: new_grid[rx][cx] = "X"
                s_idx = 0
                for c in range(4, -1, -1):
                    for r in range(3, -1, -1):
                        if new_grid[r][c] == "X": continue
                        if s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]; s_idx += 1
                conn.update(worksheet="자리배치", data=pd.DataFrame(new_grid))
                st.rerun()

        with c3:
            if st.button("🖨️ 인쇄", use_container_width=True):
                components.html("<script>window.parent.print();</script>", height=0)

    # --- 5. 시각적 출력 영역 ---
    # 이 영역은 인쇄 시 제목과 함께 출력됩니다.
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    
    # [좌석 그리드]
    grid_html = '<div class="seat-grid">'
    for r in range(4):
        for c in range(5):
            try: val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except: val = ""
            if val == "X": grid_html += '<div class="seat-container" style="background-color:#f0f0f0;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None": grid_html += f'<div class="seat-container"><div class="seat-name">{val}</div></div>'
            else: grid_html += '<div class="seat-container" style="border:1px dashed #ccc;"></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # [교탁 및 칠판]
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) 

    # 안내 문구 (웹 전용)
    st.info("💡 화면 아래쪽이 교실 앞(칠판)입니다.")
