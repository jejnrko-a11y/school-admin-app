import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 앱 기본 설정 및 고정 데이터
# ==========================================
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

# ==========================================
# 2. 데이터 처리 함수 (캐시 적용 및 형식 보정)
# ==========================================

@st.cache_data(ttl=600) # 10분 동안 명단을 구글 시트에 재요청하지 않음 (Quota 에러 방지)
def get_cached_student_list():
    try:
        return conn.read(worksheet="학생명부")
    except Exception as e:
        st.error(f"명단을 가져오는 중 오류 발생: {e}")
        return pd.DataFrame()

# ==========================================
# 3. 로그인 페이지 함수
# ==========================================
def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    
    df_students = get_cached_student_list()
    
    if df_students.empty:
        st.warning("학생 명부 데이터가 비어있습니다. 구글 시트를 확인하세요.")
        return

    # 이름(번호번) 형식으로 옵션 생성
    student_options = []
    for _, row in df_students.iterrows():
        name = str(row['이름'])
        # 번호가 소수점(0.0)으로 표시되는 것 방지
        num_val = str(row['번호']).replace('.0', '')
        if num_val == 'nan' or name == '선생님':
            student_options.append(name)
        else:
            student_options.append(f"{name}({num_val}번)")

    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password")
        
        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = df_students[df_students['이름'] == name_only].iloc[0]
            
            # [핵심] 비밀번호 형식 불일치 해결 로직
            db_pw = str(user_data['비밀번호']).strip().replace('.0', '')
            input_pw = str(pw_input).strip()
            
            if input_pw == db_pw:
                # 로그인 정보 세션 저장
                num_raw = str(user_data['번호']).replace('.0', '')
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if num_raw == 'nan' else int(float(num_raw))
                }
                st.success(f"🔓 {name_only}님, 인증 성공!")
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 4. 메인 컨트롤 로직
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # 사이드바 설정
    st.sidebar.title(f"👤 {user['name']}")
    
    # 사용자 권한에 따른 메뉴 분기
    if user['name'] == "선생님":
        st.sidebar.info("관리자 계정으로 접속 중")
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경", "교사용 관리"]
    else:
        st.sidebar.write(f"{FIXED_INFO['grade']}-{FIXED_INFO['cls']} {user['num']}번")
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경"]

    menu = st.sidebar.radio("행정 메뉴", menu_list)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        st.session_state.login_info = None
        st.session_state.submitted = False
        st.rerun()

    # --- 페이지 연결 ---
    if menu == "메인 홈":
        st.title(f"👋 {user['name']}님, 환영합니다!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
        st.info("왼쪽 메뉴를 선택하여 행정 업무를 진행하세요.")
        
        c1, c2 = st.columns(2)
        with c1:
            st.info("📝 **결석계 작성**\n\n증빙서류 사진을 여러 장 첨부하여 제출할 수 있습니다.")
        with c2:
            st.info("⚙️ **비밀번호 변경**\n\n본인만의 비밀번호로 변경하여 보안을 강화하세요.")

    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)

    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)

    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
