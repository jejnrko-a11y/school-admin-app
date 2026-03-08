import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance, seat
from utils import get_kst, load_class_info, load_student_list
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_config = st.set_page_config(page_title="행정 자동화 시스템", layout="centered")
ADMIN_PASSWORD = st.secrets.get("auth", {}).get("admin_password", "0000") 
PATHS = {"font": "NanumGothic-Regular.ttf", "bold_font": "NanumGothic-Bold.ttf", "bg": "background.png"}

# 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}"); st.stop()

FIXED_INFO = load_class_info(conn)
dept_str, grade_str, cls_str = str(FIXED_INFO['dept']).replace('.0', ''), str(FIXED_INFO['grade']).replace('.0', ''), str(FIXED_INFO['cls']).replace('.0', '')

# [CSS 핵심: 상단 고정 헤더]
st.markdown("""
    <style>
    .fixed-header {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        background-color: white;
        padding: 10px 20px;
        border-bottom: 1px solid #ddd;
        z-index: 99999;
    }
    /* 본문이 헤더 아래에서 시작되도록 여백 설정 */
    [data-testid="stMainBlockContainer"] {
        padding-top: 80px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 로그인 페이지 & 메인 로직
# ==========================================
if 'login_info' not in st.session_state: st.session_state.login_info = None
if 'page' not in st.session_state: st.session_state.page = "메인 홈"

if st.session_state.login_info is None:
    # 로그인 화면용 간단 헤더
    st.markdown('<div class="fixed-header">🏫 경기기계공업고 인증 시스템</div>', unsafe_allow_html=True)
    
    # ... (login_page 로직은 이전과 동일하므로 생략)
    # [로그인 후 session_state.login_info 설정하는 부분은 그대로 유지]
    # (참고: 로그인 함수 내부는 이전 코드와 동일하게 사용하세요)
    pass 
else:
    user = st.session_state.login_info
    
    # [고정 상단 헤더 렌더링]
    header = st.container()
    with header:
        st.markdown('<div class="fixed-header">', unsafe_allow_html=True)
        col_h1, col_h2 = st.columns([1, 4])
        with col_h1:
            if st.session_state.page != "메인 홈":
                if st.button("⬅️ 메인 홈"):
                    st.session_state.page = "메인 홈"; st.rerun()
        with col_h2:
            st.write(f"**{grade_str}학년 {cls_str}반 {user['name']}님**")
        st.markdown('</div>', unsafe_allow_html=True)

    # 사이드바 메뉴 (내비게이션)
    with st.sidebar:
        menu_list = ["메인 홈", "결석계 작성", "시간표", "자리배치", "비밀번호 변경"]
        if user['name'] in ["교사", "관리자"]: menu_list += ["교사용 출석체크", "교사용 결석계 확인"]
        
        selected = st.radio("메뉴", menu_list, index=menu_list.index(st.session_state.page) if st.session_state.page in menu_list else 0)
        if selected != st.session_state.page:
            st.session_state.page = selected; st.rerun()
        if st.button("로그아웃"): st.session_state.clear(); st.rerun()

    # 페이지 라우팅
    if st.session_state.page == "메인 홈":
        st.markdown(f"<h1 style='font-size: 2.0rem;'>👋 {grade_str}학년 {cls_str}반 {user['name']}님</h1>", unsafe_allow_html=True)
        now = get_kst()
        st.markdown(f"📅 {now.year}년 {now.month}월 {now.day}일<br>현재시간 : **{now.strftime('%H시 %M분')}**", unsafe_allow_html=True)
        # ... (바로가기 버튼 등 나머지 본문 내용은 동일)
