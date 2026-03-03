import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

# 중요 정보를 Secrets에서 가져오기
ADMIN_PASSWORD = st.secrets["auth"]["admin_password"] 
FIXED_INFO = st.secrets["school_info"]
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# 구글 시트 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")

@st.cache_data(ttl=60)
def get_cached_student_list():
    try:
        # 구글 시트에서 실시간으로 명단을 읽어옴
        return conn.read(worksheet="학생명부")
    except:
        return pd.DataFrame()

# ==========================================
# 2. 로그인 페이지 정의
# ==========================================
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
            
            # 비밀번호 형식 보정 (0 -> 0000)
            db_pw_raw = str(user_data['비밀번호']).strip().split('.')[0]
            db_pw = db_pw_raw.zfill(4) if (db_pw_raw.isdigit() and len(db_pw_raw) < 4) else db_pw_raw
            
            if str(pw_input).strip() == db_pw:
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.success(f"🔓 {name_only}님 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 3. 메인 로직 (세션 상태에 따른 분기)
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

# 로그인 전
if st.session_state.login_info is None:
    login_page()

# 로그인 후 (에러 방지를 위해 모든 메뉴 코드를 else 안에 배치)
else:
    user = st.session_state.login_info
    st.sidebar.title(f"👤 {user['name']}님")
    
    # [권한별 메뉴 설정]
    if user['name'] == "교사":
        menu_list = ["메인 홈", "출결/서류 관리", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경", "교사용 관리"]
    else:
        st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
        menu_list = ["메인 홈", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경"]

    menu = st.sidebar.radio("행정 메뉴", menu_list)
    
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    # [메뉴별 페이지 라우팅]
    if menu == "메인 홈":
        st.title(f"👋 {user['name']}님, 환영합니다!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
        st.info("왼쪽 메뉴를 선택하여 행정 업무를 진행하세요.")
    
    elif menu == "출결/서류 관리":
        # 교사용 스마트 서류 크로스체크 모듈 호출
        attendance.show_page(conn)
        
    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)
        
    elif menu == "시간표 확인":
        timetable.show_page(conn)
        
    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)
        
    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
        
    elif menu == "자리배치":
        st.title("🪑 자리배치 확인")
        st.warning("준비 중입니다.")
