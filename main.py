import streamlit as st
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="학교 행정 시스템", page_icon="🏫", layout="centered")

# 2. 디자인 (CSS) - 오류 수정 완료
st.markdown("""
    <style>
    h1, h2, h3 { color: #1E3A8A; }
    div.stButton > button:first-child {
        background-color: #2563EB; color: white; border-radius: 5px;
        width: 100%;
        height: 3em;
        font-weight: bold;
    }
    .main {
        background-color: #F8FAFC;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 사이드바 메뉴 ---
with st.sidebar:
    st.title("🏫 행정 메뉴")
    menu = st.radio(
        "기능을 선택하세요",
        ("메인 화면", "결석계 제출", "조퇴증/외출증 발급")
    )
    st.markdown("---")
    st.caption("v1.0.0 | 학교 행정 자동화")

# --- 각 메뉴별 화면 구현 ---
if menu == "메인 화면":
    st.title("🏫 학교 행정 자동화 시스템")
    st.subheader("환영합니다!")
    st.write("학생들의 행정 처리를 빠르고 정확하게 도와주는 앱입니다.")

    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="오늘의 결석계 접수", value="0건")
    with col2:
        st.metric(label="현재 외출/조퇴 승인", value="0건")

elif menu == "결석계 제출":
    st.title("📝 결석계 제출")
    st.info("결석 후 3일 이내에 증빙 서류와 함께 제출해 주세요.")

    with st.form("absence_form", clear_on_submit=True):
        st.subheader("학생 정보")
        name = st.text_input("이름")
        c1, c2, c3 = st.columns(3)
        grade = c1.selectbox("학년", [1, 2, 3])
        cls = c2.number_input("반", 1, 15, 1)
        num = c3.number_input("번호", 1, 40, 1)

        st.subheader("결석 정보")
        d_col1, d_col2 = st.columns(2)
        start_date = d_col1.date_input("결석 시작일")
        end_date = d_col2.date_input("결석 종료일")

        reason_type = st.selectbox("사유 구분", ["질병", "경조사", "현장체험학습", "기타"])
        detail_reason = st.text_area("상세 사유", placeholder="구체적인 사유를 입력하세요.")

        uploaded_file = st.file_uploader("증빙 서류 첨부", type=['jpg', 'jpeg', 'png', 'pdf'])

        submitted = st.form_submit_button("결석계 제출")

        if submitted:
            if name and detail_reason:
                st.success(f"✅ {name} 학생의 결석계가 성공적으로 접수되었습니다.")
                st.balloons()
            else:
                st.error("⚠️ 이름과 상세 사유를 반드시 입력해 주세요.")

elif menu == "조퇴증/외출증 발급":
    st.title("🏃 조퇴증/외출증 발급")
    st.warning("이 기능은 현재 준비 중입니다. 담임 선생님께 문의하세요.")
