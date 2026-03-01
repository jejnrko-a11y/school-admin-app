import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os

# 1. 페이지 설정
st.set_page_config(page_title="경기기계공고 결석신고서", layout="centered")

# 파일 경로 (GitHub 업로드 확인 필수)
font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"
bg_image_path = "background.png"

# 2. PDF 생성 클래스 (정밀 좌표 보정판)
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        
        # 배경 이미지 깔기 (A4 크기 210x297mm)
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)

        self.set_font('Nanum', '', 13) # 글자 크기 13

        # --- [정밀 보정된 좌표값] ---
        
        # 1. 학과, 학년, 반, 번호 (상단 가로줄)
        self.text(68, 48, data['dept'])      # 학과 (과 앞쪽)
        self.text(125, 48, str(data['grade'])) # 학년
        self.text(147, 48, str(data['cls']))   # 반
        self.text(169, 48, str(data['num']))   # 번호
        
        # 2. 성명 (성명: 옆자리)
        self.text(138, 59, data['name'])
        
        # 3. 결석 날짜 및 기간 (중간 본문)
        # 시작 날짜
        self.text(148, 77, str(data['s_m'])) # 월
        self.text(168, 77, str(data['s_d'])) # 일
        # 종료 날짜 및 일수
        self.text(32, 88, str(data['e_m']))  # 월
        self.text(53, 88, str(data['e_d']))  # 일
        self.text(77, 88, str(data['days'])) # 일간
        
        # 4. 중간 제출 날짜 (2026년 __월 __일)
        today = datetime.now()
        self.text(82, 120, str(today.year))
        self.text(108, 120, str(today.month))
        self.text(126, 120, str(today.day))

        # 5. 보호자 명 및 서명
        self.text(118, 138, data['g_name']) # 보호자 성함
        if g_sig:
            self.image(g_sig, x=168, y=129, w=22) # (인) 위치
            
        # 6. 학생 명 및 서명
        self.text(138, 153, data['name'])   # 학생 성함
        if s_sig:
            self.image(s_sig, x=168, y=144, w=22) # (인) 위치

        # 7. 맨 아래 날짜 (위 신고 내용이 사실임을 확인함 하단)
        # 보통 담임 선생님 확인용 날짜 칸
        self.text(100, 246, str(today.year))
        self.text(128, 246, str(today.month))
        self.text(145, 246, str(today.day))

        return bytes(self.output())

# --- Streamlit UI ---
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

st.title("🏫 경기기계공고 결석신고서 생성")

with st.form("absent_form"):
    st.subheader("📍 1. 인적사항")
    dept = st.text_input("학과", value="컴퓨터전자과")
    c1, c2, c3 = st.columns(3)
    grade = c1.selectbox("학년", [1, 2, 3], index=2)
    cls = c2.number_input("반", 1, 15, 2)
    num = c3.number_input("번호", 1, 40, 1)
    name = st.text_input("학생 성명")

    st.subheader("📅 2. 결석 날짜")
    d1, d2 = st.columns(2)
    start_date = d1.date_input("결석 시작일")
    end_date = d2.date_input("결석 종료일")
    days = st.number_input("총 결석 일수", 1, 30, 1)

    st.subheader("✍️ 3. 보호자 및 학생 서명")
    g_name = st.text_input("보호자 성함")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("보호자 서명")
        g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig", background_color="#f0f0f0")
    with col2:
        st.write("학생 서명")
        s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig", background_color="#f0f0f0")

    submit = st.form_submit_button("✅ 결석신고서 PDF 생성")

    if submit:
        if not name or not g_name:
            st.error("이름과 보호자 성함을 입력해 주세요.")
        else:
            def process_sig(canvas):
                img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf

            report_data = {
                "dept": dept, "grade": grade, "cls": cls, "num": num, "name": name,
                "s_m": start_date.month, "s_d": start_date.day,
                "e_m": end_date.month, "e_d": end_date.day,
                "days": days, "g_name": g_name
            }

            pdf_gen = SchoolPDF()
            generated_pdf = pdf_gen.generate_report(report_data, process_sig(g_canvas), process_sig(s_canvas))
            
            if generated_pdf:
                st.session_state.pdf_data = generated_pdf
                st.success("신고서 PDF가 준비되었습니다!")

# 폼 외부 다운로드 버튼
if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
