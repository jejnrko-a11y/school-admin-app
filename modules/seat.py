import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (인쇄 품질 극대화 및 UI 정제) ---
    st.markdown("""
        <style>
        /* [공통] 기본 폰트 및 스타일 */
        @import url('https://fonts.googleapis.com/css2?family=Nanum+Gothic:wght@700&display=swap');
        
        /* [웹 화면 전용] 버튼 및 메뉴 스타일 */
        .stButton button { width: 100%; }
        
        /* [인쇄 영역 설정] 제목, 좌석표, 교탁, 칠판을 감싸는 영역 */
        .print-area {
            width: 100%;
            margin: 0 auto;
            text-align: center;
        }

        /* 제목 스타일 (선 제거 및 폰트 강조) */
        .page-title {
            font-family: 'Nanum Gothic', sans-serif;
            font-size: 32px;
            font-weight: 800;
            margin-bottom: 25px;
            padding-top: 10px;
            color: #1a1a1a;
        }

        /* 좌석 그리드 */
        .seat-grid {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 10px;
            margin-bottom: 20px;
        }
        .seat-container {
            background-color: #ffffff !important;
            border: 2px solid #333 !important;
            border-radius: 8px;
            min-height: 85px;
            display: flex;
            align-items: center;
            justify-content: center;
            -webkit-print-color-adjust: exact;
        }
        .seat-name { font-weight: bold; font-size: 16px; color: #000; }
        .seat-x { color: #ff0000 !important; font-weight: bold; font-size: 22px; -webkit-print-color-adjust: exact; }

        /* 교탁 및 칠판 */
        .teacher-desk {
            background-color: #8d6e63 !important;
            width: 120px;
            height: 40px;
            margin: 0 auto 15px auto;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white !important;
            font-weight: bold;
            font-size: 14px;
            -webkit-print-color-adjust: exact;
        }
        .blackboard {
            background-color: #1e3d2f !important;
            color: white !important;
            border: 6px solid #5d4037;
            border-radius: 4px;
            padding: 15px;
            font-size: 22px;
            font-weight: bold;
            -webkit-print-color-adjust: exact;
        }

        /* [인쇄 설정] A4 가로 꽉 차게 */
        @media print {
            @page {
                size: A4 landscape;
                margin: 10mm;
            }
            /* 스트림릿 기본 요소(사이드바, 헤더, 버튼 등) 제거 */
            header, footer, .stSidebar, .stButton, .stExpander, .stAlert, 
            [data-testid="stHeader"], [data-testid="stDecoration"] {
                display: none !important;
            }
            /* 본문 여백 제거 */
            .main .block-container {
                padding: 0 !important;
                margin: 0 !important;
            }
            /* 제목 상단 선 제거 (스트림릿 기본 제목 스타일 대응) */
            h1 { display: none !important; } 
            
            .print-area {
                transform: scale(1.05); /* 인쇄 시 약간 확대 */
                transform-origin: top center;
            }
            .seat-grid { gap: 15px !important; }
            .seat-container { border: 2.5px solid #000 !important; min-height: 110px !important; }
            .seat-name { font-size: 20px !important; }
            .blackboard { font-size: 28px !important; padding: 20px !important; }
        }
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

    fixed_x_coords = [(0, 0), (1, 0)] # 5분단(왼쪽) 뒷자리 X

    # --- 3. 교사용 관리 도구 (웹에서만 보임) ---
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정"):
            st.info("💡 오른쪽(1분단)이 창가, 왼쪽(5분단)이 복도입니다.")
            
            # 조건 설정 (생략 없이 로직 유지)
            fb_pairs, ss_pairs = [], []
            c_fb = st.columns(3)
            for i in range(3):
                p = c_fb[i].multiselect(f"앞뒤 커플 {i+1}", all_students, max_selections=2, key=f"fb_{i}")
                if len(p) == 2: fb_pairs.append(p)
            
            c_ss = st.columns(3)
            for i in range(3):
                p = c_ss[i].multiselect(f"양옆 커플 {i+1}", all_students, max_selections=2, key=f"ss_{i}")
                if len(p) == 2: ss_pairs.append(p)

            cond_sep = st.multiselect("💢 분리 지정", all_students)
            cond_front = st.multiselect("📏 앞자리 (1열)", all_students)
            cond_back = st.multiselect("📺 뒷자리 (4열)", all_students)
            cond_win = st.multiselect("🪟 창가 (1분단)", all_students)
            cond_hall = st.multiselect("🚪 복도 (5분단)", all_students)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎲 조건부 자리 바꾸기"):
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
            if st.button("🔢 번호순"):
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
            if st.button("🖨️ 자리배치 인쇄"):
                components.html("<script>window.parent.print();</script>", height=0)

    # --- 4. 시각적 출력 및 인쇄 영역 (핵심) ---
    # 전체를 print-area로 감쌈
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    
    # [수정] 제목을 HTML로 직접 작성하여 인쇄 시 선이 생기지 않게 함
    st.markdown('<div class="page-title">컴퓨터전자 3-2반 자리배치</div>', unsafe_allow_html=True)
    
    # 좌석표 그리드
    grid_html = '<div class="seat-grid">'
    # 화면 출력은 r=0(뒤)부터 r=3(앞) 순으로 출력
    for r in range(4):
        for c in range(5):
            try: val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except: val = ""
            if val == "X": 
                grid_html += '<div class="seat-container" style="background-color:#f5f5f5;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None": 
                grid_html += f'<div class="seat-container"><div class="seat-name">{val}</div></div>'
            else: 
                grid_html += '<div class="seat-container" style="border:1px dashed #ccc;"></div>'
    grid_html += '</div>'
    st.markdown(grid_html, unsafe_allow_html=True)

    # 교탁과 칠판 (학생 좌석 아래 = 교실 앞쪽)
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) # print-area 끝
