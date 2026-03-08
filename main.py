import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance, seat
from utils import get_kst, load_class_info, load_student_list
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_page_config(page_title="행정 자동화 시스템", layout="centered")

ADMIN_PASSWORD = st.secrets.get("auth", {}).get("admin_password", "0000") 
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")
    st.stop()

# 동적 학급 정보 로드
FIXED_INFO = load_class_info(conn)

# ==========================================
# 2. 로그인 페이지 (모든 사용자 포함 로드)
# ==========================================
def login_page():
    st.title(f"🏫 {FIXED_INFO['dept']} 학생 인증")
    
    # 로그인 시에는 교사를 포함해야 하므로 exclude_admins=False
    df_all_users = load_student_list(conn, exclude_admins=False)
    
    if df_all_users.empty:
        st.error("⚠️ 학생 명부를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")
        return

    student_options =[]
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
            name_only = selected_user.split("(")[0]
            user_data = df_all_users[df_all_users['이름'] == name_only].iloc[0]
            db_pw_raw = str(user_data['비밀번호']).strip().split('.')[0]
            db_pw = db_pw_raw.zfill(4) if (db_pw_raw.isdigit() and len(db_pw_raw) < 4) else db_pw_raw
            
            if str(pw_input).strip() == db_pw:
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.session_state.page = "홈"
                st.success(f"🔓 {name_only}님 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 3. 메인 로직 및 내비게이션
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if 'page' not in st.session_state:
    st.session_state.page = "홈"

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    menu_list =["홈", "결석계 작성", "시간표", "자리배치", "비밀번호 변경"]
    if user['name'] in ["교사", "관리자"]:
        menu_list +=["교사용 출석체크", "교사용 결석계 확인"]

    try:
        current_idx = menu_list.index(st.session_state.page)
    except ValueError:
        current_idx = 0
        st.session_state.page = "홈"

    # 사이드바 
    st.sidebar.title(f"👤 {user['name']}님")
    if user['name'] not in ["교사", "관리자", "테스트계정"]:
        st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
    
    selected_menu = st.sidebar.radio("메뉴", menu_list, index=current_idx)
    
    if selected_menu != st.session_state.page:
        st.session_state.page = selected_menu
        st.rerun()
    
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    if st.session_state.page != "홈":
        if st.button("🔙 홈으로 돌아가기", use_container_width=True):
            st.session_state.page = "홈"
            st.rerun()
        st.divider()

    # 페이지별 라우팅
    if st.session_state.page == "홈":
        st.title(f"👋 {user['name']}님!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%H:%M')}")
        
        st.markdown("### 🚀 바로가기")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝\n\n결석계 작성", use_container_width=True):
                st.session_state.page = "결석계 작성"
                st.rerun()
            if st.button("🪑\n\n자리배치", use_container_width=True):
                st.session_state.page = "자리배치"
                st.rerun()
        with col2:
            if st.button("📅\n\n시간표", use_container_width=True):
                st.session_state.page = "시간표"
                st.rerun()
            if st.button("🔐\n\n비밀번호 변경", use_container_width=True):
                st.session_state.page = "비밀번호 변경"
                st.rerun()
        
        if user['name'] in ["교사", "관리자"]:
            st.markdown("---")
            st.markdown("### 👨‍🏫 교사용 행정")
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("🚩\n\n출석체크", use_container_width=True):
                    st.session_state.page = "교사용 출석체크"
                    st.rerun()
            with tc2:
                if st.button("📁\n\n결석계 확인", use_container_width=True):
                    st.session_state.page = "교사용 결석계 확인"
                    st.rerun()

    elif st.session_state.page == "교사용 출석체크":
        attendance.show_page(conn)
    elif st.session_state.page == "교사용 결석계 확인":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
    elif st.session_state.page == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)
    elif st.session_state.page == "시간표":
        timetable.show_page(conn)
    elif st.session_state.page == "비밀번호 변경":
        settings.show_page(conn, user)
    elif st.session_state.page == "자리배치":
        seat.show_page(conn, user)
