import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    st.title("🪑 지능형 조건부 자리배치")

    # --- 1. CSS 스타일 (인쇄 최적화 및 모바일 그리드) ---
    st.markdown("""
        <style>
        /* 기본 레이아웃 스타일 */
        .blackboard {
            background-color: #1e3d2f !important; color: white !important; border: 6px solid #5d4037;
            border-radius: 5px; padding: 15px; text-align: center;
            font-size: 20px; font-weight: bold; margin-top: 10px;
            -webkit-print-color-adjust: exact;
        }
        .teacher-desk {
            background-color: #8d6e63 !important; width: 80px; height: 35px;
            margin: 15px auto 5px auto; border-radius: 5px;
            display: flex; align-items: center; justify-content: center;
            color: white !important; font-weight: bold; font-size: 12px;
            -webkit-print-color-adjust: exact;
        }
        .seat-grid {
            display: grid; grid-template-columns: repeat(5, 1fr);
            gap: 6px; width: 100%; margin: 0 auto;
        }
        .seat-container {
            background-color: #ffffff !important; border: 1px solid #ccc;
            border-radius: 5px; padding: 8px 2px; text-align: center;
            min-height: 65px; display: flex; align-items: center; 
            justify-content: center; box-shadow: 1px 1px 2px rgba(0,0,0,0.1);
            -webkit-print-color-adjust: exact;
        }
        .seat-name { font-weight: bold; font-size: 11px; color: #333; line-height: 1.1; }
        .seat-x { color: #ff5252 !important; font-weight: bold; font-size: 16px; -webkit-print-color-adjust: exact; }
        .cond-label { font-size: 13px; font-weight: bold; color: #1E3A8A; margin-top: 5px; }

        /* 인쇄 설정 (A4 가로 모드 최적화) */
        @media print {
            @page { size: A4 landscape; margin: 0; }
            html, body { height: 100vh; margin: 0 !important; padding: 0 !important; overflow: hidden; }
            
            /* 인쇄 시 스트림릿 기본 UI 모두 숨김 */
            header, footer, .stSidebar, .stButton, .stExpander, .no-print, [data-testid="stHeader"] {
                display: none !important;
            }
            
            /* 인쇄 영역 강제 노출 및 중앙 배치 */
            .main .block-container { padding: 0 !important; max-width: 100% !important; }
            .print-area {
                display: block !important;
                position: absolute; left: 50%; top: 50%;
                transform: translate(-50%, -50%) scale(1.1);
                width: 90% !important;
            }
            .seat-grid { gap: 15px !important; }
            .seat-container { border: 2px solid #000 !important; min-height: 100px !important; }
            .seat-name { font-size: 18px !important; }
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

    # 5분단(가장 왼쪽 Col 0)의 뒷자리(Row 0, Row 1) 고정석
    fixed_x_coords = [(0, 0), (1, 0)] 

    # --- 3. 교사 전용 관리 기능 ---
    fb_pairs, ss_pairs = [], []
    cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [], []

    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정 (셔플 시 적용)"):
            st.info("💡 오른쪽(1분단)이 창가, 왼쪽(5분단)이 복도입니다.")
            
            st.markdown('<p class="cond-label">↕️ 앞뒤 짝궁 (세로)</p>', unsafe_allow_html=True)
            c_fb = st.columns(3)
            for i in range(3):
                p = c_fb[i].multiselect(f"앞뒤 커플 {i+1}", all_students, max_selections=2, key=f"fb_{i}")
                if len(p) == 2: fb_pairs.append(p)

            st.markdown('<p class="cond-label">↔️ 양옆 짝궁 (가로)</p>', unsafe_allow_html=True)
            c_ss = st.columns(3)
            for i in range(3):
                p = c_ss[i].multiselect(f"양옆 커플 {i+1}", all_students, max_selections=2, key=f"ss_{i}")
                if len(p) == 2: ss_pairs.append(p)

            st.markdown('<p class="cond-label">🚫 위치 및 기타 조건</p>', unsafe_allow_html=True)
            cond_sep = st.multiselect("💢 분리 지정 (인접 불가)", all_students)
            cond_front = st.multiselect("📏 앞자리 (1열/아래)", all_students)
            cond_back = st.multiselect("📺 뒷자리 (4열/위)", all_students)
            cond_win = st.multiselect("🪟 창가 지정 (1분단/오른쪽)", all_students)
            cond_hall = st.multiselect("🚪 복도 지정 (5분단/왼쪽)", all_students)

        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
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
                else: st.error("조건을 만족하는 배치를 찾지 못했습니다.")

        with c2:
            if st.button("🔢 번호순", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(5)] for _ in range(4)]
                for rx, cx in fixed_x_coords: new_grid[rx][cx] = "X"
                s_idx = 0
                # 이미지처럼 1분단(오른쪽 Col 4)부터 왼쪽(5분단 Col 0)으로 이동
                for c in range(4, -1, -1):
                    # 아래(앞자리 Row 3)에서 위(뒷자리 Row 0)로 올라가며 배치
                    for r in range(3, -1, -1):
                        if new_grid[r][c] == "X": continue
                        if s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]
                            s_idx += 1
                conn.update(worksheet="자리배치", data=pd.DataFrame(new_grid))
                st.rerun()

        with c3:
            if st.button("🖨️ 자리배치 인쇄", use_container_width=True):
                # 부모 창의 인쇄 기능을 실행하는 스크립트
                components.html("<script>window.parent.print();</script>", height=0)

    # --- 4. 시각적 출력 (인쇄 영역) ---
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    
    # 그리드 출력 (뒷편 시점이므로 데이터 Row 0(뒤) -> 3(앞) 순으로 출력)
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

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.info("💡 화면 아래쪽이 교실 앞(칠판)입니다. 인쇄 시 여백 없이 출력됩니다.")
