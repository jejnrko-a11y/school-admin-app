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

# --- [수정] 학생 명부를 캐시를 써서 안전하게 가져오는 함수 ---
@st.cache_data(ttl=600) # 10분 동안 구글 시트에 재요청하지 않음
def get_cached_student_list():
    return conn.read(worksheet="학생명부")

# --- 로그인 페이지 함수 ---
def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    try:
        # 캐시된 데이터 읽기
        df_students = get_cached_student_list()
        
        student_options = []
        for _, row in df_students.iterrows():
            if pd.isna(row['번호']):
                student_options.append(row['이름'])
            else:
                student_options.append(f"{row['이름']}({int(row['번호'])}번)")
    except Exception as e:
        # 에러가 Quota 문제일 경우 안내 메시지 출력
        if "429" in str(e):
            st.error("⚠️ 접속자가 많아 잠시 서비스가 지연되고 있습니다. 1분 후 새로고침(F5) 해주세요.")
        else:
            st.error(f"학생 명부를 불러올 수 없습니다: {e}")
        return

    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")

        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = df_students[df_students['이름'] == name_only].iloc[0]
            
            # [수정된 로직] 비밀번호 비교를 매우 정밀하게 수행
            # 1. 시트 데이터를 문자열로 변환
            db_pw = str(user_data['비밀번호']).strip()
            # 2. 혹시 소수점(0.0)이 붙었다면 제거
            if db_pw.endswith('.0'):
                db_pw = db_pw[:-2]
            # 3. 입력값도 문자열로 변환
            input_pw = str(pw_input).strip()
            
            if input_pw == db_pw:
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if pd.isna(user_data['번호']) else int(user_data['번호'])
                }
                st.success(f"🔓 {name_only}님, 인증 성공!")
                st.rerun()
            else:
                st.error(f"비밀번호가 틀렸습니다. (입력: {input_pw}, 실제: {db_pw})") # 확인을 위해 실제값 잠시 노출
                
# --- 메인 로직 시작 ---
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # 사이드바 설정
    st.sidebar.title(f"👤 {user['name']}")
    if user['name'] == "선생님":
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경", "교사용 관리"]
    else:
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
