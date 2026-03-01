import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io

# 1. 페이지 설정
st.set_page_config(page_title="경기기계공고 결석신고서", layout="centered")

# 2. 구글 시트 연결
conn = st.connection("gsheets", type=GSheetsConnection)

# 3. PDF 생성 클래스 정의
class PDF(FPDF):
    def header(self):
        # 폰트 설정 (GitHub에 업로드한 ttf 파일 이름과 일치해야 함)
        try:
            self.add_font('Nanum', '', 'NanumGothic.ttf')
            self.set_font('Nanum', '', 20)
        except:
            self.set_font('Arial', 'B', 20)
        
        self.cell(0, 20, '결 석 신 고 서', ln=True, align='C')
        self.ln(10)

def create_pdf(data, guardian_sig, student_sig):
    pdf = PDF()
    pdf.add_page()
    pdf.add_font('Nanum', '', 'NanumGothic.ttf')
    pdf.set_font('Nanum', '', 12)

    # 1. 학생 정보 행
    pdf.text(40, 50, f"( {data['학과']} )과  ( {data['학년']} )학년  ( {data['반']} )반  ( {data['번호']} )번")
    pdf.text(80, 60, f"성명: {data['이름']}")

    # 2. 본문 내용
    pdf.text(20, 80, f"위 본인은 [{data['사유구분']}] (으)로 인하여 2026년 ( {data['시작월']} )월 ( {data['시작일']} )일부터")
    pdf.text(20, 90, f"( {data['종료월']} )월 ( {data['종료일']} )일까지 ( {data['일수']} 일간) [{data['결석종류']}] 하였기에")
    pdf.text(20, 100, "보호자(보증인) 연서로 신고서를 제출합니다.")

    # 3. 제출 일자
    today = datetime.now()
    pdf.text(80, 120, f"{today.year} 년  {today.month} 월  {today.day} 일")

    # 4. 서명란 (이미지 삽입)
    pdf.text(100, 140, f"보호자(보증인) : {data['보호자명']}")
    if guardian_sig:
        pdf.image(guardian_sig, x=160, y=132, w=20) # 보호자 서명 위치
    
    pdf.text(125, 155, f"학생 : {data['이름']}")
    if student_sig:
        pdf.image(student_sig, x=160, y=147, w=20) # 학생 서명 위치

    pdf.set_font('Nanum', '', 15)
    pdf.text(60, 180, "경 기 기 계 공 업 고 등 학 교 장 귀하")

    return pdf.output()

# --- 앱 화면 구성 ---
st.title("🏫 결석신고서 제출 시스템")

if 'menu' not in st.session_state:
    st.session_state.menu = "메인 화면"

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성하기"):
        st.session_state.menu = "작성"
        st.rerun()

elif st.session_state.menu == "작성":
    with st.form("absent_form"):
        st.subheader("📋 학생 정보")
        dept = st.text_input("학과 (예: 컴퓨터응용기계과)")
        c1, c2, c3, c4 = st.columns(4)
        grade = c1.selectbox("학년", [1, 2, 3])
        cls = c2.number_input("반", 1, 15, 1)
        num = c3.number_input("번호", 1, 40, 1)
        name = st.text_input("학생 성명")

        st.subheader("📅 결석 정보")
        start_date = st.date_input("시작일")
        end_date = st.date_input("종료일")
        total_days = st.number_input("일수", 1, 100, 1)
        
        reason_type = st.radio("사유 구분", ["인정", "질병", "기타"], horizontal=True)
        absent_type = st.radio("종류", ["결석", "지각", "조퇴"], horizontal=True)
        detail_reason = st.text_area("상세 사유")

        st.subheader("✍️ 보호자 정보 및 서명")
        guardian_name = st.text_input("보호자 성함")
        
        # 보호자 서명 패드
        st.write("보호자 서명 (마우스/손가락)")
        g_canvas = st_canvas(height=100, width=300, stroke_width=2, key="g_sig")
        
        # 학생 서명 패드
        st.write("학생 서명")
        s_canvas = st_canvas(height=100, width=300, stroke_width=2, key="s_sig")

        submit = st.form_submit_button("제출 및 PDF 다운로드")

        if submit:
            # 데이터 준비
            data = {
                "학과": dept, "학년": grade, "반": cls, "번호": num, "이름": name,
                "시작월": start_date.month, "시작일": start_date.day,
                "종료월": end_date.month, "종료일": end_date.day,
                "일수": total_days, "사유구분": reason_type, "결석종류": absent_type,
                "보호자명": guardian_name
            }

            # 서명 이미지를 PNG로 변환
            g_img = Image.fromarray(g_canvas.image_data.astype('uint8'), 'RGBA')
            s_img = Image.fromarray(s_canvas.image_data.astype('uint8'), 'RGBA')
            
            g_buffer = io.BytesIO()
            s_buffer = io.BytesIO()
            g_img.save(g_buffer, format="PNG")
            s_img.save(s_buffer, format="PNG")

            # PDF 생성
            pdf_bytes = create_pdf(data, g_buffer, s_buffer)
            
            # 구글 시트 저장 (이전 로직 동일하게 추가 가능)
            
            st.success("신고서가 생성되었습니다! 아래 버튼을 눌러 다운로드하세요.")
            st.download_button(
                label="📄 결석신고서 PDF 다운로드",
                data=pdf_bytes,
                file_name=f"결석신고서_{name}.pdf",
                mime="application/pdf"
            )
