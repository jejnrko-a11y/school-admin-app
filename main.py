import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="학교 행정 시스템", page_icon="🏫", layout="centered")

# 2. 구글 시트 연결 (Secrets에 설정한 gsheets 사용)
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. 디자인 (CSS)
st.markdown("""
    <style>
    h1, h2, h3 { color: #1E3A8A; }
    div.stButton > button { width: 100%; height: 80px; font-size: 18px !important; border-radius: 12px; }
    </style>
    """, unsafe_allow_html=True)

# 메뉴 상태 관리
if 'menu' not in st.session_state:
    st.session_state.menu = "메인 화면"

# --- 메인 화면 ---
if st.session_state.menu == "메인 화면":
    st.title("🏫 학교 행정 시스템")
    st.subheader("원하시는 업무를 선택하세요")
    
    col1, col2 = st.columns(2)
    with col1:
        if st.button("📝\n결석계 제출"):
            st.session_state.menu = "결석계 제출"
            st.rerun()
    with col2:
        if st.button("🏃\n조퇴/외출증"):
            st.session_state.menu = "조퇴증/외출증 발급"
            st.rerun()

# --- 결석계 제출 화면 ---
elif st.session_state.menu == "결석계 제출":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()
        
    st.title("📝 결석계 제출")
    st.info("내용을 입력하면 담임 선생님의 구글 시트로 자동 저장됩니다.")

    with st.form("absence_form", clear_on_submit=True):
        name = st.text_input("학생 이름")
        c1, c2, c3 = st.columns(3)
        grade = c1.selectbox("학년", [1, 2, 3])
        cls = c2.number_input("반", 1, 15, 1)
        num = c3.number_input("번호", 1, 40, 1)
        
        reason = st.selectbox("사유", ["질병", "경조사", "체험학습", "기타"])
        detail = st.text_area("상세 사유 (병원명, 질병명 등)")
        
        submitted = st.form_submit_button("제출하기")
        
        if submitted:
            if name and detail:
                try:
                    # 1. 기존 데이터 읽어오기
                    existing_data = conn.read(ttl=0)
                    
                    # 2. 새 데이터 만들기
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name,
                        "학년": grade,
                        "반": cls,
                        "번호": num,
                        "사유": reason,
                        "상세내용": detail
                    }])
                    
                    # 3. 데이터 합치기
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    
                    # 4. 구글 시트 업데이트
                    conn.update(data=updated_df)
                    
                    st.success(f"✅ {name} 학생의 결석계가 성공적으로 저장되었습니다!")
                    st.balloons()
                except Exception as e:
                    st.error(f"저장 중 오류가 발생했습니다: {e}")
            else:
                st.error("모든 항목을 입력해 주세요.")

# --- 조퇴증/외출증 (준비 중) ---
elif st.session_state.menu == "조퇴증/외출증 발급":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()
    st.title("🏃 조퇴증/외출증 발급")
    st.warning("이 기능은 2단계에서 구현될 예정입니다.")
