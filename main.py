import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings
from utils import get_kst
import pandas as pd

# --- 앱 기본 설정 ---
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

ADMIN_PASSWORD = "1234" 
FIXED_INFO = {"dept": "컴퓨터전자과", "grade": 3, "cls": 2}
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# 서비스 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

# --- 로그인 페이지 함수 ---
def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    try:
        # 구글 시트의 '학생명부' 탭 읽기
        df_students = conn.read(worksheet="학생명부", ttl=0)
        # 이름(번호번) 형식으로 옵션 생성 (선생님은 번호 제외)
        student_options = []
        for _, row in df_students.iterrows():
            if pd.isna(row['번호']):
                student_options.append(row['이름'])
            else:
                student_options.append(f"{row['이름']}({int(row['번호'])}번)")
    except Exception as e:
        st.error(f"학생 명부를 불러올 수 없습니다: {e}")
        return

    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = df_students[df_students['이름'] == name_only].iloc[0]
            
            # 비밀번호 비교 (문자열로 변환하여 비교)
            if str(pw_input) == str(user_data['비밀번호']):
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if pd.isna(user_data['번호']) else int(user_data['번호'])
                }
                st.success(f"🔓 {name_only}님, 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# --- 메인 로직 시작 ---
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # 사이드바 프로필 표시
    st.sidebar.title(f"👤 {user['name']}")
    if user['name'] == "선생님":
        st.sidebar.write("관리자 계정")
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경", "교사용 관리"]
    else:
        st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경"]

    menu = st.sidebar.radio("행정 메뉴", menu_list)
    
    if st.sidebar.button("로그아웃"):
        st.session_state.login_info = None
        st.session_state.submitted = False
        st.rerun()

    if menu == "메인 홈":
        st.title(f"👋 {user['name']}님, 반갑습니다!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
        st.info("왼쪽 메뉴를 선택하여 행정 업무를 시작하세요.")

    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)

    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)

    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
