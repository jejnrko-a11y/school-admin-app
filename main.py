import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd

# 모듈을 안전하게 하나씩 직접 불러옵니다.
import modules.absence as absence
import modules.teacher_admin as teacher_admin
import modules.settings as settings
import modules.timetable as timetable
import modules.attendance as attendance
import modules.seating as seating

from utils import get_kst

# --- 이하 코드(FIXED_INFO 등)는 동일 ---

# --- 앱 기본 설정 ---
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

ADMIN_PASSWORD = st.secrets["auth"]["admin_password"] 
FIXED_INFO = st.secrets["school_info"]
PATHS = {"font": "NanumGothic-Regular.ttf", "bold_font": "NanumGothic-Bold.ttf", "bg": "background.png"}

# 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

@st.cache_data(ttl=60)
def get_cached_student_list():
    try:
        return conn.read(worksheet="학생명부")
    except:
        return pd.DataFrame()

# --- [에러 해결 핵심] 시트 데이터에서 명단 리스트 생성 함수 ---
def get_current_student_list():
    df = get_cached_student_list()
    if df.empty: return []
    s_list = []
    for _, row in df.iterrows():
        name = str(row['이름'])
        if name != "교사": # 교사는 출석 체크에서 제외
            num = 0 if pd.isna(row['번호']) else int(float(str(row['번호']).replace('.0', '')))
            s_list.append({"name": name, "num": num})
    return s_list

def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    df_students = get_cached_student_list()
    if df_students.empty:
        st.error("⚠️ 학생 명부를 불러오지 못했습니다. 새로고침 해주세요.")
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
                st.success(f"🔓 {name_only}님 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    st.sidebar.title(f"👤 {user['name']}님")
    
    if user['name'] == "교사":
        menu_list = ["메인 홈", "출결 관리", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경", "교사용 관리"]
    else:
        menu_list = ["메인 홈", "결석계 작성", "시간표 확인", "자리배치", "비밀번호 변경"]

    menu = st.sidebar.radio("행정 메뉴", menu_list)
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    # --- 실시간 학생 명부 생성 ---
    current_students = get_current_student_list()

    if menu == "메인 홈":
        st.title(f"👋 {user['name']}님, 환영합니다!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
        st.info("왼쪽 메뉴를 선택하여 업무를 진행하세요.")
    elif menu == "출결 관리":
        attendance.show_page(conn, current_students)
    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)
    elif menu == "시간표 확인":
        timetable.show_page(conn)
    elif menu == "자리배치":
        seating.show_page(conn)
    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)
    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
