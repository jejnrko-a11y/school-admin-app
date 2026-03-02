import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 학생 명부 및 고정 정보 설정
# ==========================================
FIXED_INFO = {"dept": "컴퓨터전자과", "grade": 3, "cls": 2}

# 학생 명부 자동 생성 (테스트 + 실험1~18)
STUDENT_LIST = [{"name": "테스트", "num": 1}]
for i in range(1, 19):
    STUDENT_LIST.append({"name": f"실험{i}", "num": i + 1})

STUDENT_OPTIONS = [f"{s['name']}({s['num']}번)" for s in STUDENT_LIST]
ADMIN_PASSWORD = "1234"
USER_PASSWORD = "0000" # 학생 공통 비밀번호

PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

# ==========================================
# 2. 로그인 로직 함수
# ==========================================
def login_page():
    st.title("🏫 경기기계공고 인증 센터")
    st.subheader("학생 인증 후 서비스를 이용해 주세요.")
    
    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", STUDENT_OPTIONS)
        pw = st.text_input("비밀번호 (초기: 0000)", type="password")
        
        if st.button("로그인", use_container_width=True):
            if pw == USER_PASSWORD:
                name_only = selected_user.split("(")[0]
                num_only = int(selected_user.split("(")[1].replace("번)", ""))
                
                # 세션에 로그인 정보 저장
                st.session_state.login_info = {"name": name_only, "num": num_only}
                st.success(f"🔓 {name_only} 학생, 인증되었습니다!")
                st.rerun()
            else:
                st.error("비밀번호가 일치하지 않습니다.")

# ==========================================
# 3. 서비스 연결 및 메인 컨트롤
# ==========================================
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

# 세션 초기화
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

# 로그인 여부에 따른 화면 분기
if st.session_state.login_info is None:
    login_page()
else:
    # --- 로그인 완료 후 메인 화면 ---
    user = st.session_state.login_info
    
    st.sidebar.title(f"👤 {user['name']} 학생")
    st.sidebar.write(f"{FIXED_INFO['grade']}학년 {FIXED_INFO['cls']}반 {user['num']}번")
    
    menu = st.sidebar.radio("행정 메뉴", ["메인 홈", "결석계 작성", "시간표 확인", "자리배치", "교사용 관리"])
    
    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        st.session_state.login_info = None
        st.session_state.submitted = False
        st.rerun()

    if menu == "메인 홈":
        st.title(f"👋 반갑습니다, {user['name']} 학생!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
        
        col1, col2 = st.columns(2)
        with col1:
            st.info("📝 **결석계 작성**\n\n로그인 정보가 자동으로 입력되어 편리하게 작성할 수 있습니다.")
        with col2:
            st.info("📅 **준비 중인 기능**\n\n우리 반 시간표와 자리배치표가 곧 업데이트됩니다.")

    elif menu == "결석계 작성":
        # 로그인된 유저 정보를 absence 모듈로 넘겨줌
        absence.show_page(conn, user, FIXED_INFO, PATHS)

    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)

    elif menu == "시간표 확인":
        st.title("📅 시간표 확인")
        st.info("현재 시간표 데이터를 준비 중입니다.")

    elif menu == "자리배치":
        st.title("🪑 자리배치")
        st.info("현재 자리배치 데이터를 준비 중입니다.")
