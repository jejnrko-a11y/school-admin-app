import streamlit as st
import pandas as pd
import random
import streamlit.components.v1 as components

def show_page(conn, user):
    # --- 1. CSS 스타일 (상단 여백 제거 및 요소 간격 최소화) ---
    st.markdown("""
        <style>
        /* [전체] 기본 여백 및 스트림릿 요소 제거 */
        .block-container {
            padding-top: 1rem !important; /* 웹 화면용 최소 여백 */
            padding-bottom: 0rem !important;
        }
        
        /* [제목] 커스텀 스타일 (st.title 대체용) */
        .main-title {
            font-size: 24px;
            font-weight: bold;
            text-align: center;
            margin-top: 0px !important;
            margin-bottom: 5px !important; /* 좌석표와의 간격 최소화 */
            color: #1a1a1a;
        }

        /* [좌석표] 그리드 설정 */
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
            min-height: 50px; /* 더 촘촘하게 높이 축소 */
            display: flex; 
            align-items: center; 
            justify-content: center;
            -webkit-print-color-adjust: exact;
        }
        .seat-name { font-weight: bold; font-size: 11px; color: #333; line-height: 1.1; }
        .seat-x { color: #ff5252 !important; font-weight: bold; font-size: 14px; -webkit-print-color-adjust: exact; }

        /* [교탁/칠판] 하단 요소 간격 압축 */
        .teacher-desk {
            background-color: #8d6e63 !important; 
            width: 70px; 
            height: 25px;
            margin: 5px auto 3px auto !important; /* 상하 마진 압축 */
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

        /* [인쇄 전용] 최적화 설정 */
        @media print {
            @page { size: A4 landscape; margin: 5mm; }
            
            /* Streamlit 기본 UI 및 불필요한 선 완전 제거 */
            header, footer, .stSidebar, .stButton, .stExpander, .stAlert, 
            [data-testid="stHeader"], [data-testid="stDecoration"], 
            [data-testid="stTitleBlock"], hr {
                display: none !important;
            }
            
            /* 인쇄 시 최상단 여백 0 */
            .main .block-container { 
                padding: 0 !important; 
                margin: 0 !important; 
            }

            .print-area {
                display: block !important;
                width: 100% !important;
            }

            /* 좌석 카드 인쇄 시 시인성 확보 및 압축 */
            .seat-container { 
                border: 1.5px solid #000 !important; 
                min-height: 70px !important; 
            }
            .seat-name { font-size: 15px !important; }
            
            /* 제목 크기 조정 */
            .main-title { font-size: 22px !important; margin-bottom: 5px !important; }
            
            /* 하단 요소 간격 극단적 압축 */
            .teacher-desk { margin: 3px auto !important; height: 35px !important; font-size: 14px !important; }
            .blackboard { padding: 10px !important; font-size: 20px !important; }
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

    # --- 3. 교사 관리 도구 (웹 전용) ---
    if user['name'] == "교사":
        with st.expander("⚙️ 특별 자리배치 조건 설정"):
            st.info("💡 오른쪽(1분단)이 창가, 왼쪽(5분단)이 복도입니다.")
            # (기존 조건 설정 로직 생략...)
            
        c1, c2, c3 = st.columns(3)
        with c1:
            if st.button("🎲 조건부 자리 바꾸기", use_container_width=True):
                # (기존 셔플 로직...)
                pass 
        with c2:
            if st.button("🔢 번호순", use_container_width=True):
                # (기존 정렬 로직...)
                pass
        with c3:
            if st.button("🖨️ 자리배치 인쇄", use_container_width=True):
                components.html("<script>window.parent.print();</script>", height=0)

    # --- 4. 시각적 출력 및 인쇄 영역 (조밀하게 배치) ---
    st.markdown('<div class="print-area">', unsafe_allow_html=True)
    
    # [1. 제목] st.title 대신 커스텀 div 사용 (여백 및 선 제거)
    st.markdown('<div class="main-title">컴퓨터전자 3-2반 자리배치</div>', unsafe_allow_html=True)
    
    # [2. 좌석표 그리드]
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

    # [3. 교탁]
    st.markdown('<div class="teacher-desk">교 탁</div>', unsafe_allow_html=True)
    
    # [4. 칠판]
    st.markdown('<div class="blackboard">칠 판 (앞)</div>', unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True) 

    # 안내 문구 (웹 전용)
    st.info("💡 인쇄 시 제목, 자리배치표, 교탁, 칠판만 한 장에 조밀하게 출력됩니다.")
