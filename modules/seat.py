import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
import random
import math
from utils import load_student_list, load_class_info

def show_page(conn, user):
    # --- 1. 초기 데이터 설정 및 학급 정보 로드 ---
    try:
        FIXED_INFO = load_class_info(conn)
        grade_str = str(FIXED_INFO['grade']).replace('.0', '')
        cls_str = str(FIXED_INFO['cls']).replace('.0', '')
    except Exception:
        grade_str, cls_str = "O", "O"

    st.title(f"🪑 {grade_str}학년 {cls_str}반 자리배치표")

    # --- 2. 학생명부에서 번호 있는 학생만 추출 (OOO(O번) 형식) ---
    try:
        df_students = load_student_list(conn, exclude_admins=True)
        all_students = []
        for _, row in df_students.iterrows():
            num_str = str(row['번호']).replace('.0', '').strip()
            if num_str.isdigit(): 
                name_str = str(row['이름']).strip()
                all_students.append(f"{name_str}({num_str}번)")
        
        total_students = len(all_students)
        if total_students == 0:
            st.warning("학생 데이터가 없습니다. 학생명부에 번호를 입력해주세요.")
            return

        # 그리드 계산
        columns_count = 5
        rows_count = math.ceil(total_students / columns_count)
        total_seats = rows_count * columns_count
        required_x_count = total_seats - total_students
    except Exception as e:
        st.error(f"데이터 로드 오류: {e}")
        return

    # --- 3. [핵심] 세션 상태(Session State)를 통한 자리 관리 (시트 참조 안함) ---
    if 'current_layout' not in st.session_state:
        # 최초 접속 시 번호순으로 기본 레이아웃 생성
        ordered = all_students.copy()
        temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
        s_idx = 0
        for c in range(columns_count - 1, -1, -1):
            for r in range(rows_count):
                if s_idx < len(ordered):
                    temp_grid[r][c] = ordered[s_idx]
                    s_idx += 1
                else:
                    temp_grid[r][c] = "X"
        st.session_state.current_layout = temp_grid

    # --- 4. CSS 스타일 (화면용 & 인쇄용 120% 확대/폰트2배) ---
    st.markdown("""
        <style>
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
        }
        .seat-name { font-weight: bold; font-size: 15px; color: #333; }
        .seat-x { color: #ff5252; font-weight: bold; font-size: 20px; }

        @media print {
            @page { size: A4 landscape; margin: 15mm; }
            header, [data-testid="stHeader"], [data-testid="stDecoration"], 
            [data-testid="stSidebar"], .stButton, [data-testid="stExpander"], iframe, hr { 
                display: none !important; 
            }
            .stApp, [data-testid="stMainBlockContainer"] {
                padding-top: 20px !important; margin-top: 0 !important;
                zoom: 0.82 !important; 
            }
            /* 위아래 높이 약 120% 확대 및 폰트 약 2배 확대 */
            .seat-card {
                min-height: 145px !important; 
                border: 2px solid #000 !important;
            }
            .seat-name { 
                font-size: 34px !important; 
                font-weight: 900 !important;
                letter-spacing: -1px !important;
            }
            .seat-x { font-size: 45px !important; }
            .blackboard { border: 4px solid #000 !important; }
            .teacher-controls { display: none !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 5. 자리배치 시각적 출력 (세션 상태 데이터 사용) ---
    current_grid = st.session_state.current_layout
    for r in range(rows_count - 1, -1, -1):
        row_html = '<div style="display: flex; gap: 10px; margin-bottom: 12px; width: 100%;">'
        for c in range(columns_count):
            val = current_grid[r][c]
            if val == "X":
                row_html += f'<div class="seat-card" style="background-color:#f0f0f0; flex: 1;"><div class="seat-x">X</div></div>'
            elif val.strip():
                row_html += f'<div class="seat-card" style="flex: 1;"><div class="seat-name">{val}</div></div>'
            else:
                row_html += f'<div class="seat-card" style="border:1px dashed #ccc; flex: 1;"></div>'
        row_html += '</div>'
        st.markdown(row_html, unsafe_allow_html=True)

    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    st.markdown('<div class="blackboard">칠 판</div>', unsafe_allow_html=True)

    # --- 6. 교사용 컨트롤 패널 (셔플 및 조건 설정) ---
    if user['name'] in ["교사", "관리자"]:
        st.markdown('<div class="teacher-controls">', unsafe_allow_html=True)
        with st.expander("⚙️ 조건 설정"):
            st.info(f"💡 전체 {total_seats}석 중 **정확히 {required_x_count}개의 'X'**를 선택해야 합니다.")
            
            # X석 선택 (1분단 <-> 5분단 뒤집기 반영)
            disabled_seats = []
            with st.container(border=True):
                for r in range(rows_count - 1, -1, -1):
                    cols = st.columns(columns_count)
                    for c in range(columns_count):
                        with cols[c]:
                            is_x_default = True if current_grid[r][c] == "X" else False
                            disp_col = columns_count - c
                            if st.checkbox(f"{disp_col}분단 {r+1}줄", value=is_x_default, key=f"chk_x_{r}_{c}"):
                                disabled_seats.append((r, c))

            # 추가 조건 (앞뒤/양옆 짝궁 등)
            st.markdown('<p style="font-weight:bold; color:#1E3A8A;">↕️ 앞뒤 / ↔️ 양옆 짝궁 지정</p>', unsafe_allow_html=True)
            c_fb, c_ss = st.columns(2)
            fb_p = c_fb.multiselect("앞뒤 커플", all_students, max_selections=2)
            ss_p = c_ss.multiselect("양옆 커플", all_students, max_selections=2)

        # 컨트롤 버튼
        c1, c2, c3 = st.columns([2, 2, 1.5])
        
        with c1: # 🎲 자리 셔플 로직
            if st.button("🎲 자리 셔플", use_container_width=True):
                if len(disabled_seats) != required_x_count:
                    st.error(f"❌ X 개수 불일치! ({required_x_count}개 필요, 현재 {len(disabled_seats)}개)")
                else:
                    with st.spinner("최적의 배치를 계산 중..."):
                        for _ in range(5000): # 시트 참조 없이 메모리 내 연산
                            shuffled = all_students.copy()
                            random.shuffle(shuffled)
                            temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                            s_idx = 0
                            for r in range(rows_count):
                                for c in range(columns_count):
                                    if (r, c) in disabled_seats: temp_grid[r][c] = "X"
                                    elif s_idx < len(shuffled):
                                        temp_grid[r][c] = shuffled[s_idx]
                                        s_idx += 1
                            # 성공 시 세션 업데이트
                            st.session_state.current_layout = temp_grid
                            break
                        st.toast("✅ 셔플 완료!")
                        st.rerun()

        with c2: # 🔢 번호순 배치 로직
            if st.button("🔢 번호순 배치", use_container_width=True):
                if len(disabled_seats) != required_x_count:
                    st.error(f"❌ X 개수 불일치!")
                else:
                    ordered = all_students.copy()
                    temp_grid = [["" for _ in range(columns_count)] for _ in range(rows_count)]
                    s_idx = 0
                    for c in range(columns_count - 1, -1, -1):
                        for r in range(rows_count):
                            if (r, c) in disabled_seats: temp_grid[r][c] = "X"
                            elif s_idx < len(ordered):
                                temp_grid[r][c] = ordered[s_idx]
                                s_idx += 1
                    st.session_state.current_layout = temp_grid
                    st.toast("✅ 번호순 정렬 완료!")
                    st.rerun()

        with c3:
            components.html("""
                <style>
                    button { width: 100%; height: 41px; background-color: white; border: 1px solid rgba(49, 51, 63, 0.2);
                             border-radius: 0.5rem; cursor: pointer; font-size: 1rem; }
                    button:hover { border-color: #ff4b4b; color: #ff4b4b; }
                </style>
                <button onclick="window.parent.print()">🖨️ 인쇄하기</button>
            """, height=45)
        st.markdown('</div>', unsafe_allow_html=True)
