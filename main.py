import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

ADMIN_PASSWORD = st.secrets["auth"]["admin_password"] 
FIXED_INFO = st.secrets["school_info"]
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")

@st.cache_data(ttl=60)
def get_cached_student_list():
    try:
        return conn.read(worksheet="학생명부")
    except:
        return pd.DataFrame()

def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    df_students = get_cached_student_list()
    if df_students.empty:
        st.error("⚠️ 학생 명부를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")
        return

    student_options = []
    for _, row in df_students.iterrows():
        name = str(row['이름'])
        num_raw = str(row['번호']).replace('.0', '')
        if num_raw == 'nan' or name == '교사':
            student_options.append(name)
        else:
            student_options.append(f"{name}({num_raw}번)")

    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = df_students[df_students['이름'] == name_only].iloc[0]
            db_pw_raw = str(user_data['비밀번호']).strip().split('.')[0]
            db_pw = db_pw_raw.zfill(4) if (db_pw_raw.isdigit() and len(db_pw_raw) < 4) else db_pw_raw
            
            if str(pw_input).strip() == db_pw:
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.session_state.page = "메인 홈" # 로그인 직후 페이지 초기화
                st.success(f"🔓 {name_only}님 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 3. 메인 로직 및 동적 라우팅 (에러 수정됨)
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

# 현재 페이지 상태 초기화 (핵심: 별도 변수 관리)
if 'page' not in st.session_state:
    st.session_state.page = "메인 홈"

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # [권한별 메뉴 설정]
    if user['name'] == "교사":
        menu_list = ["메인 홈", "출결/서류 관리", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경", "교사용 관리"]
    else:
        menu_list = ["메인 홈", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경"]

    # 현재 세션 상태의 페이지가 메뉴 리스트 중 몇 번째인지 확인
    try:
        current_idx = menu_list.index(st.session_state.page)
    except ValueError:
        current_idx = 0

    # 사이드바 구성
    st.sidebar.title(f"👤 {user['name']}님")
    if user['name'] != "교사":
        st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
    
    # ⭐️ 에러 수정 포인트: key를 사용하지 않고 return값과 index를 사용
    selected_menu = st.sidebar.radio(
        "행정 메뉴", 
        menu_list, 
        index=current_idx
    )
    
    # 사이드바에서 메뉴를 클릭했을 때 상태 동기화
    if selected_menu != st.session_state.page:
        st.session_state.page = selected_menu
        st.rerun()
    
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    # [페이지별 화면 출력]
    if st.session_state.page == "메인 홈":
        st.title(f"👋 {user['name']}님!")
        st.write(f"오늘도 즐거운 학교생활 되세요! (KST: {get_kst().strftime('%H:%M')})")
        
        st.markdown("### 🚀 바로가기")
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("📝\n\n결석계 작성", use_container_width=True):
                st.session_state.page = "결석계 작성" # 상태 변경
                st.rerun()
            if st.button("🪑\n\n자리배치", use_container_width=True):
                st.session_state.page = "자리배치"
                st.rerun()
        
        with col2:
            if st.button("📅\n\n시간표 확인", use_container_width=True):
                st.session_state.page = "시간표 확인"
                st.rerun()
            if st.button("🔐\n\n비번 변경", use_container_width=True):
                st.session_state.page = "비밀번호 변경"
                st.rerun()
        
        if user['name'] == "교사":
            st.markdown("---")
            st.markdown("### 👨‍🏫 교사용 행정")
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("🚩\n\n출결/서류 관리", use_container_width=True):
                    st.session_state.page = "출결/서류 관리"
                    st.rerun()
            with tc2:
                if st.button("📁\n\n교사용 관리", use_container_width=True):
                    st.session_state.page = "교사용 관리"
                    st.rerun()

    elif st.session_state.page == "출결/서류 관리":
        attendance.show_page(conn)
        
    elif st.session_state.page == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)
        
    elif st.session_state.page == "시간표 확인":
        timetable.show_page(conn)
        
    elif st.session_state.page == "비밀번호 변경":
        settings.show_page(conn, user)
        
    elif st.session_state.page == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
        
    elif st.session_state.page == "자리배치":
        st.title("🪑 자리배치 확인")
        st.warning("준비 중입니다.")
