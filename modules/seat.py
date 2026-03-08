import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (시간표 스타일 상속, 상단 고정 버튼, 인쇄 최적화) ---
    st.markdown("""
        <style>
        /* 웹 화면 기본 설정 */
        [data-testid="stHeader"], [data-testid="stDecoration"] { display: none !important; }
        .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; }
        hr { display: none !important; }

        /* [제목 스타일] 시간표 코드 참고: 왼쪽 정렬 및 크기 조절 */
        .title-container {
            text-align: left !important;
            margin-top: 10px;
            margin-bottom: 15px;
        }
        .main-title {
            font-size: 2.2rem; /* 시간표 st.title 크기 */
            font-weight: 700;
            color: #1a1a1a;
            margin-bottom: 0.2rem;
        }
        .sub-title {
            font-size: 1.5rem; /* 시간표 ### 크기 */
            font-weight: 600;
            color: #31333F;
        }

        /* [메인 홈 버튼] 상단 고정(Sticky) 및 디자인 강화 */
        .sticky-wrapper {
            position: sticky;
            top: 0;
            z-index: 1001;
            background-color: white;
            padding: 10px 0;
        }
        div.stButton > button:first-child {
            background-color: #1E3A8A !important;
            color: white !important;
            font-weight: bold !important;
            border: 2px solid #002D62 !important;
            border-radius: 10px !important;
            box-shadow: 0 4px 6px rgba(0,0,0,0.2) !important;
            height: 3rem !important;
        }

        /* 좌석 그리드 레이아웃 */
        .seat-grid {
            display: grid; 
            grid-template-columns: repeat(5, 1fr);
            gap: 6px; 
            width: 100%; 
            margin: 0 auto !important;
        }
        .seat-container {
            background-color: #ffffff !important; 
            border: 1px solid #ccc;
            border-radius: 5px; 
            padding: 8px 2px; 
            text-align: center;
            min-height: 55px;
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
            width: 80px; height: 30px;
            margin: 10px auto 5px auto !important;
            border-radius: 3px;
            display: flex; align-items: center; justify-content: center;
            color: white !important; font-weight: bold; font-size: 12px;
            -webkit-print-color-adjust: exact;
        }
        .blackboard {
            background-color: #1e3d2f !important; 
            color: white !important; 
            border: 4px solid #5d4037;
            border-radius: 4px; padding: 10px; 
            text-align: center; font-size: 20px; font-weight: bold;
            -webkit-print-color-adjust: exact;
        }

        /* 인쇄 설정 (A4 가로 최적화) */
        @media print {
            @page { size: A4 landscape; margin: 10mm; }
            header, footer, .stSidebar, .stButton, .stExpander, .stAlert, .sticky-wrapper, [data-testid="stHeader"] {
                display: none !important;
            }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            .print-area { display: block !important; width: 100% !important; }
            .seat-container { border: 2px solid #000 !important; min-height: 85px !important; }
            .seat-name { font-size: 17px !important; }
            .main-title { font-size: 26px !important; }
            .sub-title { font-size: 18px !important; }
            .blackboard { font-size: 26px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 2. [홈 버튼] 상단 고정 영역 ---
    st.markdown('<div class="sticky-wrapper">', unsafe_allow_html=True)
    if st.button("🔙 메인 홈으로 돌아가기", use_container_width=True):
        st.session_state.page = "메인 홈"
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    # --- 3. [제목 영역] 시간표 스타일 참고 (왼쪽 정렬) ---
    # 인쇄 영역(print-area) 안에 포함시켜 인쇄 시에도 제목이 나오게 함
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    st.markdown("""
        <div class="title-container">
            <div class="main-title">🪑 학급 자리배치</div>
            <div class="sub-title">3학년 2반 (컴퓨터전자과)</div>
        </div>
    """, unsafe_allow_html=True)

    # --- 4. 데이터 로드 ---
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

    # 5분단(가장 왼쪽 Col 0)의 뒷자리(Row 0, 1) X 고정석
    fixed_x_coords = [(0, 0), (1, 0)] 

    # --- 5. 교사용 관리 도구 ---
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
            cond_front = st.multiselect("📏 앞자리 (1열/아래)", all_students)
            cond_back = st.multiselect("📺 뒷자리 (4열/위)", all_students)
            cond_win = st.multiselect("🪟 창가 (1분단/오른쪽)", all_students)
            cond_hall = st.multiselect("🚪 복도 (5분단/왼쪽)", all_students)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎲 자리 셔플", use_container_width=True):
                success = False
                with st.spinner("계산 중..."):
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
                            if not (pos1:=s_map[p[0]]) or not (pos2:=s_map[p[1]]): valid=False; break
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
                else: st.error("조건을 만족하는 배치를 찾지 못했습니다.")

        with c2:
            if st.button("🔢 번호순", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(5)] for _ in range(4)]
                for rx, cx in fixed_x_coords: new_grid[rx][cx] = "X"
                s_idx = 0
                # [수정 로직] 오른쪽(1분단 Col 4)부터 왼쪽(5분단 Col 0)으로
                for c in range(4, -1, -1):
                    # 아래(앞자리 Row 3)에서 위(뒷자리 Row 0)로 번호순 배치
                    for r in range(3, -1, -1):
                        if new_grid[r][c] == "X": continue
                        if s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]; s_idx += 1
                conn.update(worksheet="자리배치", data=pd.DataFrame(new_grid))
                st.rerun()

        with c3:
            if st.button("🖨️ 인쇄", use_container_width=True):
                components.html("<script>window.parent.print();</script>", height=0)

    # --- 6. 시각적 출력 (인쇄 영역 내부) ---
    grid_html = '<div class="seat-grid">'
    # 데이터 row 0(뒤) ~ row 3(앞) 순서로 출력 (데이터 순서와 시각적 배치를 일치시킴)
    for r in range(4):
        for c in range(5):
            try: val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except: val = ""
            if val == "X": grid_html += '<div class="seat-container" style="background-color:#f0f0f0;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None": grid_html += f'<div class="seat-container"><div class="seat-name">{val}</div></div>'
            else: grid_html += '<div class="seat-container" style="border:1px dashed #ccc;"></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True) # print-area 끝
