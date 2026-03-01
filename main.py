import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# 1. 페이지 설정
st.set_page_config(page_title="학교 행정 시스템", page_icon="🏫", layout="centered")

# 2. 구글 시트 연결 (Secrets 설정을 사용함)
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("구글 시트 연결 설정(Secrets)에 오류가 있습니다. 설정을 확인해 주세요.")

# 3. 디자인 (CSS)
st.markdown("""
    <style>
    h1, h2, h3 { color: #1E3A8A; }
    div.stButton > button { width: 100%; height: 60px; font-size: 18px !important; border-radius: 12px; font-weight: bold; }
    .stForm { background-color: #ffffff; padding: 20px; border-radius: 15px; border: 1px solid #e0e0e0; }
    </style>
    """, unsafe_allow_html=True)

# 메뉴 상태 관리
if 'menu' not in st.session_state:
    st.session_state.menu = "메인 화면"

# --- 메인 화면 ---
if st.session_state.menu == "메인 화면":
    st.title("🏫 학교 행정 자동화 시스템")
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
    
    st.info("💡 팁: 핸드폰에서 메뉴가 안 보이면 왼쪽 상단의 '>' 버튼을 누르거나 위 버튼을 이용하세요.")

# --- 결석계 제출 화면 ---
elif st.session_state.menu == "결석계 제출":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()
        
    st.title("📝 결석계 제출")
    st.write("모든 항목을 정확히 입력한 후 제출해 주세요.")

    # 폼 시작
    with st.form("absence_form", clear_on_submit=True):
        st.subheader("1. 학생 기본 정보")
        name = st.text_input("학생 이름", placeholder="이름을 입력하세요")
        
        c1, c2, c3 = st.columns(3)
        grade = c1.selectbox("학년", [1, 2, 3])
        cls = c2.number_input("반", 1, 15, 1)
        num = c3.number_input("번호", 1, 40, 1)
        
        st.markdown("---")
        st.subheader("2. 결석 내용")
        
        # 결석 기간
        absence_date = st.date_input("결석 날짜 (또는 기간 시작일)")
        
        # 사유 선택
        reason = st.selectbox("사유 구분", ["질병", "경조사", "현장체험학습", "기타"])
        detail = st.text_area("상세 사유", placeholder="구체적인 사유를 입력하세요 (예: 독감으로 인한 병가, 외할머니 팔순 등)")
        
        submitted = st.form_submit_button("제출하기 (구글 시트로 전송)")
        
        if submitted:
            if name and detail:
                try:
                    # 데이터 읽기
                    existing_data = conn.read(ttl=0)
                    
                    # 새 행 추가
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name,
                        "학년": grade,
                        "반": cls,
                        "번호": num,
                        "사유": reason,
                        "상세내용": detail
                    }])
                    
                    # 합치기 및 업데이트
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    
                    st.success(f"✅ {name} 학생의 결석계가 성공적으로 구글 시트에 기록되었습니다!")
                    st.balloons()
                except Exception as e:
                    st.error(f"⚠️ 저장 오류: {e}")
            else:
                st.error("⚠️ 이름과 상세 사유를 반드시 입력해 주세요.")

# --- 조퇴증/외출증 (2단계 예정) ---
elif st.session_state.menu == "조퇴증/외출증 발급":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()
    st.title("🏃 조퇴증/외출증 발급")
    st.warning("이 기능은 현재 개발 중입니다.")
