import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 앱 기본 설정
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
# 2. 데이터 처리 함수 (캐시 적용)
# ==========================================
@st.cache_data(ttl=60) # 테스트 중에는 반영 속도를 위해 1분(60초)으로 줄였습니다.
def get_cached_student_list():
    try:
        return conn.read(worksheet="학생명부")
    except Exception as e:
        return pd.DataFrame()

# ==========================================
# 3. 로그인 페이지 함수
# ==========================================
def login_page():
    st.title("🏫 경기기계공고 학생 인증")
    
    df_students = get_cached_student_list()
    
    if df_students.empty:
        st.error("⚠️ 학생 명부를 불러오지 못했습니다. 잠시 후 새로고침 해주세요.")
        return

    # 이름(번호번) 형식으로 옵션 생성
    student_options = []
    for _, row in df_students.iterrows():
        name = str(row['이름'])
        num_raw = str(row['번호']).replace('.0', '')
        if num_raw == 'nan' or name == '선생님':
            student_options.append(name)
        else:
            student_options.append(f"{name}({num_raw}번)")

    with st.container(border=True):
        selected_user = st.selectbox("본인의 이름을 선택하세요", student_options)
        pw_input = st.text_input("비밀번호", type="password", placeholder="초기 비밀번호 0000")
        
        if st.button("로그인", use_container_width=True):
            name_only = selected_user.split("(")[0]
            user_data = df_students[df_students['이름'] == name_only].iloc[0]
            
            # --- [핵심] 비밀번호 비교 로직 보강 ---
            # 1. 시트에서 가져온 값 문자열로 변환 및 소수점 제거
            db_pw_raw = str(user_data['비밀번호']).strip().split('.')[0] 
            
            # 2. 숫자만 있는 경우 4자리로 맞추기 (예: "0" -> "0000", "123" -> "0123")
            if db_pw_raw.isdigit() and len(db_pw_raw) < 4:
                db_pw = db_pw_raw.zfill(4)
            else:
                db_pw = db_pw_raw
            
            input_pw = str(pw_input).strip()
            
            if input_pw == db_pw:
                # 로그인 정보 세션 저장
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.success(f"🔓 {name_only}님, 인증 성공!")
                st.rerun()
            else:
                st.error(f"비밀번호가 틀렸습니다.")
                # st.write(f"디버그: 입력한값[{input_pw}] / 시트값[{db_pw}]") # 로그인 안될 때만 주석 해제해서 확인

# ==========================================
# 4. 메인 로직
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    st.sidebar.title(f"👤 {user['name']}님")
    
    if user['name'] == "선생님":
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경", "교사용 관리"]
    else:
        st.sidebar.write(f"{FIXED_INFO['grade']}학년 {FIXED_INFO['cls']}반 {user['num']}번")
        menu_list = ["메인 홈", "결석계 작성", "비밀번호 변경"]

    menu = st.sidebar.radio("행정 메뉴", menu_list)
    
    st.sidebar.markdown("---")
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    if menu == "메인 홈":
        st.title(f"👋 {user['name']}님, 환영합니다!")
        st.write(f"현재 KST: {get_kst().strftime('%m-%d %H:%M')}")
        st.info("왼쪽 메뉴에서 업무를 선택하세요.")

    elif menu == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)

    elif menu == "비밀번호 변경":
        settings.show_page(conn, user)

    elif menu == "교사용 관리":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
        
    elif menu == "시간표 확인":
        from modules import timetable
        timetable.show_page(conn)        
