import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance, seat, issuance_user, issuance_admin
from utils import get_kst, load_class_info, load_student_list
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_page_config(page_title="학교 생활 도우미", layout="centered")

ADMIN_PASSWORD = st.secrets.get("auth", {}).get("admin_password", "0000") 
PATHS = {"font": "NanumGothic-Regular.ttf", "bold_font": "NanumGothic-Bold.ttf", "bg": "background.png"}

# 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")
    st.stop()

# 동적 학급 정보 로드
FIXED_INFO = load_class_info(conn)
dept_str = str(FIXED_INFO['dept']).replace('.0', '')
grade_str = str(FIXED_INFO['grade']).replace('.0', '')
cls_str = str(FIXED_INFO['cls']).replace('.0', '')

# [CSS: Sticky 상단 고정 방식 및 겹침 방지]
st.markdown("""
    <style>
    /* 1. 마커가 들어간 컨테이너는 화면에서 숨김 */
    div.element-container:has(.sticky-marker) {
        display: none;
    }
    
    /* 2. 마커 바로 다음 요소(버튼)를 본문 상단에 '찰싹(Sticky)' 고정 */
    div.element-container:has(.sticky-marker) + div.element-container {
        position: sticky;
        top: 60px; /* Streamlit 헤더 아래 위치 */
        z-index: 9999; /* 가장 위에 떠 있도록 설정 */
        background-color: white !important; /* 투명도 없는 완벽한 흰색 배경 */
        width: 100% !important; /* ★ 가로 전체를 덮어서 옆으로 글자가 새어나오지 않게 차단 */
        display: block !important;
        padding-top: 10px;
        padding-bottom: 10px;
        border-bottom: 2px solid #f0f2f6;
        margin-bottom: 15px; /* 고정 영역 아래에 약간의 여백 추가 */
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. 로그인 페이지
# ==========================================
def login_page():
    st.markdown(f"<h1 style='font-size: 1.8rem; margin-bottom: 18px;'>🏫 경기기계공업고 {dept_str} {grade_str}학년 {cls_str}반 인증</h1>", unsafe_allow_html=True)
    df_all_users = load_student_list(conn, exclude_admins=False)
    
    if df_all_users.empty: 
        st.error("⚠️ 학생 명부를 불러오지 못했습니다.")
        return

    student_options = []
    for _, row in df_all_users.iterrows():
        name = str(row['이름']).strip()
        num_raw = str(row['번호']).replace('.0', '')
        if num_raw == 'nan' or name in ['교사', '테스트계정', '관리자']: 
            student_options.append(name)
        else: 
            student_options.append(f"{name}({num_raw}번)")
    
    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")
        if st.button("로그인", use_container_width=True):
            user_data = df_all_users[df_all_users['이름'] == selected_user.split("(")[0]].iloc[0]
            db_pw = str(user_data['비밀번호']).strip().split('.')[0]
            if str(pw_input).strip() == db_pw:
                st.session_state.login_info = {
                    "name": selected_user.split("(")[0], 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.session_state.page = "메인 홈"
                st.rerun()
            else: 
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 3. 메인 로직 및 페이지 라우팅
# ==========================================
if 'login_info' not in st.session_state: 
    st.session_state.login_info = None
if 'page' not in st.session_state: 
    st.session_state.page = "메인 홈"

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # [상단 고정 버튼 렌더링]
    if st.session_state.page != "메인 홈":
        # 고정시킬 버튼 바로 위에 sticky 마커 삽입
        st.markdown('<div class="sticky-marker"></div>', unsafe_allow_html=True)
        if st.button("⬅️ 메인 홈 돌아가기"): 
            st.session_state.page = "메인 홈"
            st.rerun()

    # 사이드바
    with st.sidebar:
        st.title(f"👤 {user['name']}님")
        menu_list = ["메인 홈", "시간표", "자리배치", "결석신고서 작성", "조퇴/외출/교내활동증 신청", "비밀번호 변경"]
        if user['name'] in ["교사", "관리자"]: 
            menu_list += ["[교사용]출석체크", "[교사용]결석계 다운로드", "[교사용]증명서 승인"]
        
        selected = st.radio("메뉴", menu_list, index=menu_list.index(st.session_state.page) if st.session_state.page in menu_list else 0)
        if selected != st.session_state.page: 
            st.session_state.page = selected
            st.rerun()
            
        if st.button("로그아웃", use_container_width=True): 
            st.session_state.clear()
            st.rerun()

    # 페이지 라우팅
    if st.session_state.page == "메인 홈":
        st.markdown(f"<h1 style='font-size: 2.0rem;'>👋 {grade_str}학년 {cls_str}반 {user['name']}님</h1>", unsafe_allow_html=True)
        now = get_kst()
        st.markdown(f"📅 {now.year}년 {now.month}월 {now.day}일<br>현재시간 : **{now.strftime('%H시 %M분')}**", unsafe_allow_html=True)
        
        st.markdown("### 🚀 바로가기")
        c1, c2 = st.columns(2)
        if c1.button("📅 시간표", use_container_width=True): 
            st.session_state.page = "시간표"
            st.rerun()
        if c1.button("🪑 자리배치", use_container_width=True): 
            st.session_state.page = "자리배치"
            st.rerun()
        if c2.button("📝 결석신고서 작성", use_container_width=True): 
            st.session_state.page = "결석신고서 작성"
            st.rerun()
        if c2.button("🔐 비밀번호 변경", use_container_width=True): 
            st.session_state.page = "비밀번호 변경"
            st.rerun()
        
        if user['name'] in ["교사", "관리자"]:
            st.markdown("---")
            st.markdown("### 👨‍🏫 교사용 행정")
            if st.button("🚩 출석체크", use_container_width=True): 
                st.session_state.page = "[교사용]출석체크"
                st.rerun()
            if st.button("📁 결석계 다운로드", use_container_width=True): 
                st.session_state.page = "[교사용]결석계 다운로드"
                st.rerun()

    elif st.session_state.page == "[교사용]출석체크": 
        attendance.show_page(conn)
    elif st.session_state.page == "[교사용]결석계 다운로드": 
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
    elif st.session_state.page == "결석신고서 작성": 
        absence.show_page(conn, user, FIXED_INFO, PATHS)
    elif st.session_state.page == "시간표": 
        timetable.show_page(conn)
    elif st.session_state.page == "비밀번호 변경": 
        settings.show_page(conn, user)
    elif st.session_state.page == "자리배치": 
        seat.show_page(conn, user)
    elif st.session_state.page == "조퇴/외출/교내활동증 신청":
        issuance_user.show_page(conn, user, FIXED_INFO)
    elif st.session_state.page == "[교사용]증명서 승인":
        issuance_admin.show_page(conn)
