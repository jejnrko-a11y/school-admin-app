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
        grade_str, cls_str = "O", "O" # 로드 실패 시 기본값
        
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
            word-break: keep-all; /* 텍스트 중간에 줄바꿈 방지 */
        }
        .seat-name { font-weight: bold; font-size: 15px; color: #333; line-height: 1.2; }
        .seat-x { color: #ff5252; font-weight: bold; font-size: 20px; }
        .cond-label { font-size: 13px; font-weight: bold; color: #1E3A8A; margin-top: 5px; }

        /* 스마트폰 화면 크기일 때 좌석 글씨와 높이를 약간 줄여서 5칸이 다 예쁘게 들어가게 조정 */
        @media (max-width: 640px) {
            .seat-card { min-height: 60px; padding: 5px 1px; border-radius: 6px; }
            .seat-name { font-size: 11px; }
        }

        /* --- 🖨️ 인쇄 전용(Print) 디자인 --- */
        @media print {
            @page { size: A4 landscape; margin: 15mm; }
            
            /* 불필요한 UI 숨기기 */
            header, [data-testid="stSidebar"], .stButton, [data-testid="stExpander"], iframe { 
                display: none !important; 
            }
            .sticky-marker, .fixed-header-bg { display: none !important; }
            
            /* 본문 여백 제거 */
            [data-testid="stMainBlockContainer"] {
                padding: 0 !important;
                max-width: 100% !important;
            }
            
            /* ⭐ 핵심: 제목과 좌석 사이의 빈 공백만 줄이기 위해 제목(Heading)의 아래 마진을 음수로 끌어올림 */
            div[data-testid="stHeadingWithActionElements"] {
                margin-bottom: -35px !important; 
                padding-bottom: 0 !important;
            }
            
            /* 좌석 간격, 교탁, 칠판 간격은 화면에서 보는 비율 그대로 유지 (겹침 문제 해결) */
            .seat-card {
                border: 2px solid #000 !important;
                box-shadow: none !important;
                break-inside: avoid;
            }
            .blackboard { border: 4px solid #000 !important; padding: 15px !important; margin-bottom: 0 !important;}
            .teacher-desk { margin: 20px auto 15px auto !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 3. 동적 데이터 로드 및 그리드 계산 ---
    try:
        df_seat = conn.read(worksheet="자리배치", ttl=0)
        
        df_students = load_student_list(conn, exclude_admins=True)
        all_students = [f"{row['이름']}({row['번호']}번)" for _, row in df_students.iterrows()]
        
        total_students = len(all_students)
        if total_students == 0:
            st.warning("학생 데이터가 없습니다.")
            return
            
        columns_count = 5
        rows_count = math.ceil(total_students / columns_count)
        
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # --- 4. 교사 전용 조건 설정 및 버튼 ---
    fb_pairs =[] 
    ss_pairs =[] 
    cond_sep, cond_front, cond_back, cond_win, cond_hall = [], [], [], [],[]
    cond_fixed_br = "선택 안함"
    
    if user['name'] in ["교사", "관리자"]:
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

        c1, c2, c3 = st.columns([2, 2, 1.5])
        
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
                success = False
                max_attempts = 20000 
                
                with st.spinner("복합 조건을 만족하는 최적의 배치를 계산 중입니다..."):
                    for attempt in range(max_attempts):
                        shuffled = all_students.copy()
                        
                        if cond_fixed_br != "선택 안함" and cond_fixed_br in shuffled:
                            shuffled.remove(cond_fixed_br)
                        
                        random.shuffle(shuffled)
                        
                        temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                        s_map = {}
                        s_idx = 0
                        
                        for r in range(rows_count):
                            for c in range(columns_count):
                                if cond_fixed_br != "선택 안함" and r == 0 and c == columns_count - 1:
                                    temp_grid[r][c] = cond_fixed_br
                                    s_map[cond_fixed_br] = (0, c)
                                elif s_idx < len(shuffled):
                                    name = shuffled[s_idx]
                                    temp_grid[r][c] = name
                                    s_map[name] = (r, c)
                                    s_idx += 1
                                else:
                                    temp_grid[r][c] = "X"
                        
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
                            success = True; break
                
                if success:
                    st.toast("✅ 모든 커플 및 배치 조건을 만족합니다!")
                    st.rerun()
                else:
                    st.error("❌ 조건이 너무 복잡하여 배치를 찾지 못했습니다. 커플 수를 줄이거나 조건을 완화해 주세요.")

        with c2:
            if st.button("🔢 번호순 배치", use_container_width=True):
                ordered = all_students.copy()
                new_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                s_idx = 0
                
                for c in range(columns_count - 1, -1, -1):
                    for r in range(rows_count):
                        if s_idx < len(ordered):
                            new_grid[r][c] = ordered[s_idx]
                            s_idx += 1
                        else:
                            new_grid[r][c] = "X"
                            
                new_df = pd.DataFrame(new_grid, columns=["1분단", "2분단", "3분단", "4분단", "5분단"])
                conn.update(worksheet="자리배치", data=new_df)
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

    # --- 5. 시각적 출력 (순수 HTML Flexbox 렌더링 - 모바일 최적화) ---
    st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True) # 위쪽 약간의 여백

    # Streamlit 기본 Column 대신 HTML Flexbox를 써서 모바일에서도 절대 세로로 찢어지지 않게 함
    for r in range(rows_count - 1, -1, -1):
        # 한 줄(Row) 컨테이너 생성
        row_html = '<div style="display: flex; flex-wrap: nowrap; gap: 10px; margin-bottom: 12px; width: 100%;">'
        for c in range(columns_count):
            try:
                val = str(df_seat.iloc[r, c]) if not pd.isna(df_seat.iloc[r, c]) else ""
            except IndexError:
                val = ""
                
            # 개별 자리 카드 HTML 생성 (flex: 1을 주어 5칸이 정확히 동일한 너비를 가짐)
            if val == "X":
                row_html += f'<div class="seat-card" style="background-color:#f0f0f0; flex: 1;"><div class="seat-x">X</div></div>'
            elif val.strip() and val != "None":
                row_html += f'<div class="seat-card" style="flex: 1;"><div class="seat-name">{val}</div></div>'
            else:
                row_html += f'<div class="seat-card" style="border:1px dashed #ccc; flex: 1;"></div>'
        
        row_html += '</div>'
        # 만들어진 한 줄을 화면에 출력
        st.markdown(row_html, unsafe_allow_html=True)

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판 (Front)</div>', unsafe_allow_html=True)
