import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import math
from utils import load_student_list, load_class_info

def show_page(conn, user):
    # --- 1. 동적 학급 정보 로드 및 제목 설정 ---
    try:
        FIXED_INFO = load_class_info(conn)
        grade_str = str(FIXED_INFO['grade']).replace('.0', '')
        cls_str = str(FIXED_INFO['cls']).replace('.0', '')
    except Exception:
        grade_str, cls_str = "O", "O"
        
    st.title(f"🪑 {grade_str}학년 {cls_str}반 자리배치표")

    # --- 2. CSS 스타일 (화면용 & 인쇄용) ---
    st.markdown("""
        <style>
        /* --- 화면 및 모바일 전용 디자인 --- */
        .blackboard {
            background-color: #1e3d2f; color: white; border: 8px solid #5d4037;
            border-radius: 5px; padding: 20px; text-align: center;
            font-size: 24px; font-weight: bold; margin-top: 20px; margin-bottom: 20px;
        }
        .teacher-desk {
            background-color: #8d6e63; width: 120px; height: 50px;
            margin: 30px auto 20px auto; border-radius: 5px;
            display: flex; align-items: center; justify-content: center;
            color: white; font-weight: bold; font-size: 14px;
        }
        .seat-card {
            background-color: #ffffff; border: 2px solid #e0e0e0;
            border-radius: 10px; padding: 10px 2px; text-align: center;
            box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            min-height: 85px; display: flex; align-items: center; justify-content: center;
            word-break: keep-all;
        }
        .seat-name { font-weight: bold; font-size: 15px; color: #333; line-height: 1.2; }
        .seat-x { color: #ff5252; font-weight: bold; font-size: 20px; }
        .cond-label { font-size: 14px; font-weight: bold; color: #1E3A8A; margin-top: 15px; margin-bottom: 5px;}

        @media (max-width: 640px) {
            .seat-card { min-height: 60px; padding: 5px 1px; border-radius: 6px; }
            .seat-name { font-size: 11px; }
        }

        /* --- 🖨️ 인쇄 전용(Print) 디자인 --- */
        @media print {
            @page { size: A4 landscape; margin: 15mm; }
            
            /* 불필요한 UI 및 모든 종류의 구분선 완벽 제거 */
            header, [data-testid="stHeader"], [data-testid="stDecoration"], 
            [data-testid="stSidebar"], .stButton, [data-testid="stExpander"], iframe, hr { 
                display: none !important; 
            }
            .sticky-marker, .fixed-header-bg { display: none !important; }
            
            /* 회색 실선(테두리/그림자)이 생길 수 있는 모든 컨테이너 속성 강제 초기화 */
            .stApp, [data-testid="stAppViewContainer"], [data-testid="stMainBlockContainer"] {
                border: none !important;
                outline: none !important;
                box-shadow: none !important;
                background-color: transparent !important;
                padding-top: 0 !important;
                margin-top: 0 !important;
                max-width: 100% !important;
            }
            
            div[data-testid="stHeadingWithActionElements"] {
                margin-top: 0 !important;
                padding-top: 0 !important;
                margin-bottom: -35px !important; 
                padding-bottom: 0 !important;
                border: none !important;
            }
            
            .seat-card {
                border: 2px solid #000 !important;
                box-shadow: none !important;
                break-inside: avoid;
            }
            .blackboard { border: 4px solid #000 !important; padding: 15px !important; margin-bottom: 0 !important;}
            .teacher-desk { margin: 20px auto 15px auto !important; }
            
            .teacher-controls { display: none !important; } 
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. 동적 데이터 로드 및 그리드 계산 ---
    try:
        # 💡 [핵심수정] 429 에러 방지: ttl=0(매번 로드) 대신 ttl="10m"(10분 캐시) 사용
        df_seat = conn.read(worksheet="자리배치", ttl="10m")
        df_students = load_student_list(conn, exclude_admins=True)
        all_students = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
        
        total_students = len(all_students)
        if total_students == 0:
            st.warning("학생 데이터가 없습니다.")
            return
            
        columns_count = 5
        rows_count = math.ceil(total_students / columns_count)
        total_seats = rows_count * columns_count
        required_x_count = total_seats - total_students
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # --- 4. 시각적 출력 (순수 HTML Flexbox 렌더링 - 칠판이 위로 옴) ---
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) 

    for r in range(rows_count - 1, -1, -1):
        row_html = '<div style="display: flex; flex-wrap: nowrap; gap: 10px; margin-bottom: 12px; width: 100%;">'
        for c in range(columns_count):
            try:
                val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except IndexError:
                val = ""
                
            if val == "X":
                row_html += f'<div class="seat-card" style="background-color:#f0f0f0; flex: 1;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None":
                row_html += f'<div class="seat-card" style="flex: 1;"><div class="seat-name">{val}</div></div>'
            else:
                row_html += f'<div class="seat-card" style="border:1px dashed #ccc; flex: 1;"></div>'
        
        row_html += '</div>'
        st.markdown(row_html, unsafe_allow_html=True)

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)

    # --- 5. 교사 전용 조건 설정 및 버튼 (칠판 아래로 이동) ---
    st.markdown('<div class="teacher-controls"></div>', unsafe_allow_html=True)
    
    fb_pairs = [] 
    ss_pairs = [] 
    cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [], []
    disabled_seats = [] 
    
    if user['name'] in ["교사", "관리자"]:
        st.markdown("<br>", unsafe_allow_html=True)
        with st.expander("⚙️ 특별 자리배치 조건 설정 (셔플 시 적용)"):
            st.info(f"💡 전체 {total_seats}석 중 학생 수({total_students}명)를 제외한 **정확히 {required_x_count}개의 자리**를 'X'로 체크해야 합니다.")
            
            st.markdown('<p class="cond-label">🚫 사용하지 않을 빈 좌석(X) 선택</p>', unsafe_allow_html=True)
            
            with st.container(border=True):
                for r in range(rows_count - 1, -1, -1):
                    cols = st.columns(columns_count)
                    for c in range(columns_count):
                        with cols[c]:
                            is_x_default = False
                            try:
                                if str(df_seat.iloc[r, c]) == "X": is_x_default = True
                            except: pass
                            
                            if st.checkbox(f"{c+1}분단 {r+1}줄", value=is_x_default, key=f"chk_x_{r}_{c}"):
                                disabled_seats.append((r, c))

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

        # 하단 컨트롤 버튼 영역
        c1, c2, c3 = st.columns([2, 2, 1.5])
        
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
                if len(disabled_seats) != required_x_count:
                    st.error(f"❌ 빈 좌석(X) 개수가 맞지 않습니다! (필요한 X 개수: **{required_x_count}개**, 현재 선택됨: **{len(disabled_seats)}개**)")
                else:
                    success = False
                    max_attempts = 20000 
                    
                    with st.spinner("복합 조건을 만족하는 최적의 배치를 계산 중입니다..."):
                        for attempt in range(max_attempts):
                            shuffled = all_students.copy()
                            random.shuffle(shuffled)
                            
                            temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                            s_map = {}
                            s_idx = 0
                            
                            for r in range(rows_count):
                                for c in range(columns_count):
                                    if (r, c) in disabled_seats:
                                        temp_grid[r][c] = "X"
                                    elif s_idx < len(shuffled):
                                        name = shuffled[s_idx]
                                        temp_grid[r][c] = name
                                        s_map[name] = (r, c)
                                        s_idx += 1
                            
                            valid = True
                            
                            for p in fb_pairs:
                                pos1, pos2 = s_map[p[0]], s_map[p[1]]
                                if not (pos1[1] == pos2[1] and abs(pos1[0] - pos2[0]) == 1):
                                    valid = False; break
                            
                            if valid:
                                for p in ss_pairs:
                                    pos1, pos2 = s_map[p[0]], s_map[p[1]]
                                    if not (pos1[0] == pos2[0] and abs(pos1[1] - pos2[1]) == 1):
                                        valid = False; break

                            if valid and cond_sep and len(cond_sep) > 1:
                                for i in range(len(cond_sep)):
                                    for j in range(i + 1, len(cond_sep)):
                                        p1, p2 = s_map[cond_sep[i]], s_map[cond_sep[j]]
                                        if abs(p1[0]-p2[0]) + abs(p1[1]-p2[1]) == 1:
                                            valid = False; break
                                    if not valid: break

                            if valid and cond_front and any(s_map[n][0] != 0 for n in cond_front): valid = False
                            if valid and cond_back and any(s_map[n][0] != rows_count - 1 for n in cond_back): valid = False
                            if valid and cond_win and any(s_map[n][1] != 0 for n in cond_win): valid = False
                            if valid and cond_hall and any(s_map[n][1] != 4 for n in cond_hall): valid = False
                            
                            if valid:
                                new_df = pd.DataFrame(temp_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                                conn.update(worksheet="자리배치", data=new_df)
                                st.cache_data.clear() # 💡 [핵심수정] 업데이트 성공 시에만 캐시를 초기화하여 다음 로드 때 갱신되게 함
                                success = True; break
                    
                    if success:
                        st.toast("✅ 모든 커플 및 배치 조건을 만족합니다!")
                        st.rerun()
                    else:
                        st.error("❌ 조건이 너무 복잡하여 배치를 찾지 못했습니다. 조건을 완화해 주세요.")

        with c2:
            if st.button("🔢 번호순 배치", use_container_width=True):
                if len(disabled_seats) != required_x_count:
                    st.error(f"❌ 빈 좌석(X) 개수가 맞지 않습니다! (필요한 X 개수: **{required_x_count}개**, 현재 선택됨: **{len(disabled_seats)}개**)")
                else:
                    ordered = all_students.copy()
                    new_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                    s_idx = 0
                    
                    for c in range(columns_count - 1, -1, -1):
                        for r in range(rows_count):
                            if (r, c) in disabled_seats:
                                new_grid[r][c] = "X"
                            elif s_idx < len(ordered):
                                new_grid[r][c] = ordered[s_idx]
                                s_idx += 1
                                
                    new_df = pd.DataFrame(new_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                    conn.update(worksheet="자리배치", data=new_df)
                    st.cache_data.clear() # 💡 [핵심수정] 업데이트 성공 시에만 캐시를 초기화
                    st.rerun()
                
        with c3:
            components.html("""
                <style>
                    body { margin: 0; padding: 0; display: flex; align-items: flex-start; }
                    button {
                        width: 100%; height: 41px; margin-top: 1px;
                        background-color: white; border: 1px solid rgba(49, 51, 63, 0.2);
                        border-radius: 0.5rem; font-family: "Source Sans Pro", sans-serif;
                        font-size: 1rem; font-weight: 400; color: #31333F;
                        cursor: pointer; transition: border-color 0.2s, color 0.2s;
                        display: flex; align-items: center; justify-content: center;
                    }
                    button:hover { border-color: #ff4b4b; color: #ff4b4b; }
                </style>
                <button onclick="window.parent.print()">🖨️ 인쇄하기</button>
            """, height=45)
