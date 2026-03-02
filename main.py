import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin
from utils import get_kst

# ==========================================
# 1. 공통 설정 및 데이터
# ==========================================
FIXED_INFO = {"dept": "컴퓨터전자과", "grade": 3, "cls": 2}

STUDENT_LIST = [
    {"name": "가나다", "num": 1},
    {"name": "마바사", "num": 2},
    {"name": "홍길동", "num": 3},
]
STUDENT_OPTIONS = [f"{s['name']}({s['num']}번)" for s in STUDENT_LIST]

ADMIN_PASSWORD = "1234" # 교사용 관리 비밀번호

PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# ==========================================
# 2. 서비스 연결
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

# ==========================================
# 3. 사이드바 내비게이션
# ==========================================
st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("이동", ["메인 화면", "결석계 작성", "시간표 확인", "자리배치", "교사용 관리"])

if 'submitted' not in st.session_state: 
    st.session_state.submitted = False

# ==========================================
# 4. 메뉴별 화면 전환
# ==========================================
if menu == "메인 화면":
    st.session_state.submitted = False
    st.title("🏫 경기기계공고 행정 시스템")
    st.write(f"현재 시간(KST): {get_kst().strftime('%m-%d %H:%M')}")
    st.info("원하시는 메뉴를 선택하여 업무를 시작하세요.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.help("결석계는 사진을 여러 장 첨부할 수 있습니다.")
    with col2:
        st.help("교사용 관리 페이지에서 서류를 통합 출력하세요.")

elif menu == "결석계 작성":
    absence.show_page(conn, STUDENT_OPTIONS, FIXED_INFO, PATHS)

elif menu == "교사용 관리":
    teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)

elif menu == "시간표 확인":
    st.title("📅 시간표 확인")
    st.warning("준비 중인 기능입니다.")

elif menu == "자리배치":
    st.title("🪑 자리배치")
    st.warning("준비 중인 기능입니다.")
