import streamlit as st
from streamlit_gsheets import GSheetsConnection
from modules import absence, teacher_admin, settings, timetable, attendance, seat
from utils import get_kst
import pandas as pd

# ==========================================
# 1. 초기 설정 및 보안 로드
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

ADMIN_PASSWORD = st.secrets["auth"]["admin_password"] 
FIXED_INFO = st.secrets["school_info"]
PATHS = {
    "font": "NanumGothic-Regular.ttf",
    "bold_font": "NanumGothic-Bold.ttf",
    "bg": "background.png"
}

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error(f"데이터베이스 연결 실패: {e}")

@st.cache_data(ttl=60)
def get_cached_student_list():
    try:
        return conn.read(worksheet="학생명부")
    except:
        return pd.DataFrame()

# ==========================================
# 2. 로그인 페이지
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
            db_pw_raw = str(user_data['비밀번호']).strip().split('.')[0]
            db_pw = db_pw_raw.zfill(4) if (db_pw_raw.isdigit() and len(db_pw_raw) < 4) else db_pw_raw
            
            if str(pw_input).strip() == db_pw:
                st.session_state.login_info = {
                    "name": name_only, 
                    "num": 0 if str(user_data['번호']) == 'nan' else int(float(str(user_data['번호'])))
                }
                st.session_state.page = "메인 홈"
                st.rerun()
            else:
                st.error("비밀번호가 틀렸습니다.")

# ==========================================
# 3. 메인 로직 및 내비게이션 (CSS 최적화 포함)
# ==========================================
if 'login_info' not in st.session_state:
    st.session_state.login_info = None

if 'page' not in st.session_state:
    st.session_state.page = "메인 홈"

if st.session_state.login_info is None:
    login_page()
else:
    user = st.session_state.login_info
    
    # [강력한 CSS 적용] 여백 제거, 상단 고정 버튼, 선 제거
    st.markdown("""
        <style>
        /* [1] 페이지 상단 여백 및 헤더 선 완전 제거 */
        [data-testid="stHeader"] { display: none !important; }
        .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 100% !important; }
        hr { display: none !important; } /* st.divider 등 모든 가로선 제거 */

        /* [2] 뒤로가기 버튼 상단 고정 (Sticky) */
        [data-testid="stVerticalBlock"] > div:has(div.sticky-nav) {
            position: sticky;
            top: 0;
            z-index: 1001;
            background-color: white;
            padding-top: 10px;
            padding-bottom: 10px;
        }

        /* [3] 뒤로가기 버튼 디자인 (#1E3A8A) */
        div.stButton > button:has(div[p='🔙 메인 홈으로 돌아가기']), 
        div.stButton > button:contains('🔙') {
            background-color: #1E3A8A !important;
            color: white !important;
            font-weight: bold !important;
            border-radius: 12px !important;
            border: 2px solid #002D62 !important;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3) !important;
            height: 3.2rem !important;
            width: 100% !important;
            font-size: 1.1rem !important;
        }

        /* [4] 간격 최적화 (제목과 컨텐츠 사이 공백 최소화) */
        .stHeadingContainer { margin-bottom: -15px !important; }
        div[data-testid="stVerticalBlock"] { gap: 0.5rem !important; }
        </style>
    """, unsafe_allow_html=True)

    # 메뉴 구성
    menu_list = ["메인 홈", "결석계 작성", "시간표", "자리배치", "비밀번호 변경"]
    if user['name'] == "교사":
        menu_list += ["교사용 출석체크", "교사용 결석계 확인"]

    try:
        current_idx = menu_list.index(st.session_state.page)
    except ValueError:
        current_idx = 0

    st.sidebar.title(f"👤 {user['name']}님")
    selected_menu = st.sidebar.radio("메뉴", menu_list, index=current_idx)
    
    if selected_menu != st.session_state.page:
        st.session_state.page = selected_menu
        st.rerun()
    
    if st.sidebar.button("로그아웃"):
        st.session_state.clear()
        st.rerun()

    # [내비게이션 출력 순서 확정]
    # 1. 홈 버튼 (상단 고정 영역)
    if st.session_state.page != "메인 홈":
        st.markdown('<div class="sticky-nav"></div>', unsafe_allow_html=True)
        if st.button("🔙 메인 홈으로 돌아가기"):
            st.session_state.page = "메인 홈"
            st.rerun()
        # st.divider()는 요구사항에 따라 삭제함

    # 2. 페이지별 로직 실행
    if st.session_state.page == "메인 홈":
        st.title(f"👋 {user['name']}님!")
        st.write(f"현재 시간(KST): {get_kst().strftime('%H:%M')}")
        st.markdown("### 🚀 바로가기")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("📝\n\n결석계 작성", use_container_width=True):
                st.session_state.page = "결석계 작성"; st.rerun()
            if st.button("🪑\n\n자리배치", use_container_width=True):
                st.session_state.page = "자리배치"; st.rerun()
        with col2:
            if st.button("📅\n\n시간표", use_container_width=True):
                st.session_state.page = "시간표"; st.rerun()
            if st.button("🔐\n\n비밀번호 변경", use_container_width=True):
                st.session_state.page = "비밀번호 변경"; st.rerun()
        if user['name'] == "교사":
            st.markdown("---")
            st.markdown("### 👨‍🏫 교사용 행정")
            tc1, tc2 = st.columns(2)
            with tc1:
                if st.button("🚩\n\n출석체크", use_container_width=True):
                    st.session_state.page = "교사용 출석체크"; st.rerun()
            with tc2:
                if st.button("📁\n\n결석계 확인", use_container_width=True):
                    st.session_state.page = "교사용 결석계 확인"; st.rerun()

    elif st.session_state.page == "교사용 출석체크":
        attendance.show_page(conn)
    elif st.session_state.page == "교사용 결석계 확인":
        teacher_admin.show_page(conn, ADMIN_PASSWORD, FIXED_INFO, PATHS)
    elif st.session_state.page == "결석계 작성":
        absence.show_page(conn, user, FIXED_INFO, PATHS)
    elif st.session_state.page == "시간표":
        timetable.show_page(conn)
    elif st.session_state.page == "비밀번호 변경":
        settings.show_page(conn, user)
    elif st.session_state.page == "자리배치":
        seat.show_page(conn, user)
