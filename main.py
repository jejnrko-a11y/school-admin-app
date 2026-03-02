import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin
from utils import get_kst

# --- 설정 및 경로 ---
FIXED_INFO = {"dept": "컴퓨터전자과", "grade": 3, "cls": 2}
STUDENT_LIST = [
    {"name": "가나다", "num": 1}, {"name": "마바사", "num": 2}, {"name": "홍길동", "num": 3},
]
STUDENT_OPTIONS = [f"{s['name']}({s['num']}번)" for s in STUDENT_LIST]
ADMIN_PASSWORD = "1234"
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# --- 연결 ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

# --- 내비게이션 ---
st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("이동", ["메인 화면", "결석계 작성", "시간표 확인", "자리배치", "교사용 관리"])

if 'submitted' not in st.session_state: st.session_state.submitted = False

if menu == "메인 화면":
    st.session_state.submitted = False
    st.title("🏫 경기기계공고 행정 시스템")
    st.write(f"현재 시간(KST): {get_kst().strftime('%m-%d %H:%M')}")
    st.info("원하시는 메뉴를 선택하세요.")

elif menu == "결석계 작성":
    absence.show_page(conn, STUDENT_OPTIONS, FIXED_INFO, PATHS)

elif menu == "교사용 관리":
    teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)

elif menu == "시간표 확인":
    st.title("📅 시간표 확인")
    st.write("준비 중인 기능입니다.")

elif menu == "자리배치":
    st.title("🪑 자리배치")
    st.write("준비 중인 기능입니다.")
