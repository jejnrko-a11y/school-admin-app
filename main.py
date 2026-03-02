import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings
from utils import get_kst
import pandas as pd

# 설정 데이터
ADMIN_PASSWORD = "1234"
FIXED_INFO = {"dept": "컴퓨터전자과", "grade": 3, "cls": 2}
PATHS = {"font": "NanumGothic-Regular.ttf", "bold_font": "NanumGothic-Bold.ttf", "bg": "background.png"}

# 서비스 연결
conn = st.connection("gsheets", type=GSheetsConnection)

def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    try:
        # 학생명부 탭에서 정보 읽기
        student_df = conn.read(worksheet="학생명부", ttl=0)
        student_options = [f"{row['이름']}({int(row['번호'])}번)" for _, row in student_df.iterrows()]
    except:
        st.error("구글 시트에서 '학생명부' 탭을 찾을 수 없습니다. 시트 이름을 확인해 주세요.")
        return

    with st.container(border=True):
        selected_user = st.selectbox("이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = student_df[student_df['이름'] == name_only].iloc[0]
            
            if str(pw_input) == str(user_data['비밀번호']):
                st.session_state.login_info = {"name": name_only, "num": int(user_data['번호'])}
                st.success(f"{name_only} 학생 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    st.sidebar.title(f"👤 {user['name']} 학생")
    st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
    
    menu = st.sidebar.radio("행정 메뉴", ["메인 홈", "결석계 작성", "비밀번호 변경", "교사용 관리"])
    
    if st.sidebar.button("로그아웃"):
        st.session_state.login_info = None
        st.rerun()

    if menu == "메인 홈":
        st.title(f"👋 {user['name']} 학생, 환영합니다!")
        st.write(f"현재 시간: {get_kst().strftime('%m-%d %H:%M')}")
        st.info("왼쪽 메뉴에서 업무를 선택하세요.")

    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)

    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)

    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
