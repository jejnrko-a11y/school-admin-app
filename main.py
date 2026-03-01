import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="학교 행정 시스템", page_icon="🏫", layout="centered")

# 2. 디자인 (CSS)
st.markdown("""
    <style>
    h1, h2, h3 { color: #1E3A8A; }
    /* 큰 버튼 스타일 */
    div.stButton > button {
        width: 100%;
        height: 100px;
        font-size: 20px !important;
        border-radius: 15px;
        margin-bottom: 10px;
    }
    </style>
    """, unsafe_allow_html=True)

# 세션 상태로 메뉴 관리 (버튼 클릭 시 메뉴 이동을 위해)
if 'menu_option' not in st.session_state:
    st.session_state.menu_option = "메인 화면"

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🏫 행정 메뉴")
    # 세션 상태와 연동된 라디오 버튼
    menu = st.radio(
        "기능을 선택하세요",
        ("메인 화면", "결석계 제출", "조퇴증/외출증 발급"),
        key="sidebar_menu"
    )
    # 사이드바에서 선택하면 세션 상태 업데이트
    st.session_state.menu_option = menu

# --- 각 메뉴별 화면 구현 ---
current_menu = st.session_state.menu_option

if current_menu == "메인 화면":
    st.title("🏫 학교 행정 시스템")
    st.subheader("필요한 기능을 선택하세요")
    
    # 모바일용 큰 버튼 배치
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📝\n결석계 제출"):
            st.session_state.menu_option = "결석계 제출"
            st.rerun()
            
    with col2:
        if st.button("🏃\n조퇴/외출증"):
            st.session_state.menu_option = "조퇴증/외출증 발급"
            st.rerun()

    st.markdown("---")
    # 현황판
    c1, c2 = st.columns(2)
    c1.metric("오늘의 결석계", "0건")
    c2.metric("현재 외출/조퇴", "0건")

elif current_menu == "결석계 제출":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu_option = "메인 화면"
        st.rerun()
        
    st.title("📝 결석계 제출")
    # ... (결석계 폼 코드는 동일하게 유지) ...
    with st.form("absence_form"):
        name = st.text_input("학생 이름")
        submitted = st.form_submit_button("제출하기")
        if submitted:
            st.success(f"{name} 학생의 결석계가 접수되었습니다.")

elif current_menu == "조퇴증/외출증 발급":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu_option = "메인 화면"
        st.rerun()
    st.title("🏃 조퇴증/외출증 발급")
    st.info("준비 중인 기능입니다.")
