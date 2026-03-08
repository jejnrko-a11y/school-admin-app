import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (디자인 개선 및 강력한 스타일 강제 적용) ---
    st.markdown("""
        <style>
        /* [공통] 웹 화면 기본 설정 및 선 제거 */
        [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0rem !important; padding-bottom: 2rem !important; max-width: 100% !important; }
        hr { display: none !important; } /* 모든 구분선 제거 */

        /* [1. 상단 고정 내비게이션 바] */
        .sticky-nav {
            position: sticky;
            top: 0;
            z-index: 1001;
            background-color: white !important;
            padding: 15px 0 !important;
            border-bottom: none !important;
        }

        /* [2. 네비게이션 버튼 - 차분한 네이비 블루 #2C3E50] */
        div.stButton > button:first-child {
            background-color: #2C3E50 !important;
            color: #FFFFFF !important;
            font-weight: 700 !important;
            border: none !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 10px rgba(0,0,0,0.15) !important;
            height: 3.2rem !important;
            transition: all 0.2s ease !important;
        }
        div.stButton > button:first-child:hover {
            background-color: #1A252F !important;
            box-shadow: 0 6px 15px rgba(0,0,0,0.2) !important;
            transform: translateY(-1px) !important;
        }

        /* [제목 영역 스타일] */
        .title-container {
            text-align: left !important;
            margin-top: 5px !important;
            margin-bottom: 10px !important; /* 좌석표와 조밀하게 유지 */
        }
        .main-title {
            font-size: 2.2rem !important;
            font-weight: 800 !important;
            color: #2C3E50 !important;
            margin-bottom: 0px !important;
        }
        .sub-title {
            font-size: 1.4rem !important;
            font-weight: 500 !important;
            color: #7F8C8D !important;
            margin-top: -5px !important;
        }

        /* [좌석표 그리드] */
        .seat-grid {
            display: grid; 
            grid-template-columns: repeat(5, 1fr);
            gap: 8px !important; 
            width: 100% !important;
        }
        .seat-container {
            background-color: #ffffff !important; 
            border: 1px solid #E0E0E0 !important; /* 연한 회색 테두리 */
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
            color: #000000 !important; /* 선명한 검은색 글자 */
            line-height: 1.1 !important; 
        }
        .seat-x { 
            color: #E74C3C !important; 
            font-weight: bold !important; 
            font-size: 16px !important; 
            -webkit-print-color-adjust: exact; 
        }

        /* [교탁 및 칠판 간격 대폭 조정] */
        .teacher-desk {
            background-color: #8d6e63 !important; 
            width: 90px !important; 
            height: 35px !important;
            margin: 40px auto 40px auto !important; /* 좌석-교탁, 교탁-칠판 간격 40px */
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
            .sticky-nav, .stButton, .stExpander, .stAlert, [data-testid="stHeader"] { display: none !important; }
            .print-area { display: block !important; width: 100% !important; }
            .seat-container { border: 2px solid #333 !important; min-height: 100px !important; }
            .seat-name { font-size: 18px !important; }
            .main-title { font-size: 26px !important; }
            .sub-title { font-size: 16px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. 상단 고정 네비게이션 버튼 (통합 및 하나로 고정) ---
    st.markdown('<div class="sticky-nav">', unsafe_allow_html=True)
    if st.button("🔙 메인 홈으로 돌아가기", key="back_to_home_seat", use_container_width=True):
        st.session_state.page = "메인 홈"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. 제목 및 부제목 (왼쪽 정렬 및 시간표 스타일 참고) ---
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    st.markdown("""
        <div class="title-container">
            <div class="main-title">🪑 학급 자리배치</div>
            <div class="sub-title">3학년 2반 (컴퓨터전자과)</div>
        </div>
    """, unsafe_allow_html=True)

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

    # --- 5. 학생 자리 그리드 (1열이 아래쪽으로 역순 출력) ---
    grid_html = '<div class="seat-grid">'
    # r=0(뒷자리) ~ r=3(앞자리) 데이터 구조에서 시각적으로 앞자리가 아래로 가게 출력
    for r in range(4):
        for c in range(5):
            try: val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except: val = ""
            if val == "X": grid_html += '<div class="seat-container" style="background-color:#F5F5F5;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None": grid_html += f'<div class="seat-container"><div class="seat-name">{val}</div></div>'
            else: grid_html += '<div class="seat-container" style="border:1px dashed #DDD !important;"></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # --- 6. 교탁 및 칠판 (간격 확보됨) ---
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) # print-area 끝
