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

# 파일 경로 설정
font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"
bg_image_path = "background.png" # 학교 양식 이미지 파일

# 2. PDF 생성 클래스 (배경 이미지 위에 글자 얹기)
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        
        # [핵심] 배경 이미지 깔기 (A4 크기에 맞춤)
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)
        else:
            st.error("배경 이미지(background.png)를 찾을 수 없습니다.")

        self.set_font('Nanum', '', 12)

        # --- 좌표에 맞춰 데이터 입력 (아래 좌표값은 이미지에 맞춰 미세조정 필요) ---
        
        # 학과, 학년, 반, 번호
        self.text(55, 62, data['dept'])   # 학과
        self.text(92, 62, str(data['grade'])) # 학년
        self.text(113, 62, str(data['cls']))  # 반
        self.text(133, 62, str(data['num']))  # 번호
        
        # 성명
        self.set_font('Nanum', '', 14)
        self.text(105, 76, data['name'])
        
        # 사유 구분 (인정, 질병, 기타 중 선택된 것에 표시 또는 동그라미)
        self.set_font('NanumB', '', 12)
        if data['reason_cat'] == "인정": self.text(48, 93, "O")
        elif data['reason_cat'] == "질병": self.text(61, 93, "O")
        elif data['reason_cat'] == "기타": self.text(74, 93, "O")

        # 기간 (시작일 ~ 종료일)
        self.set_font('Nanum', '', 11)
        self.text(115, 93, str(data['s_m'])) # 시작 월
        self.text(130, 93, str(data['s_d'])) # 시작 일
        self.text(23, 107, str(data['e_m'])) # 종료 월
        self.text(38, 107, str(data['e_d'])) # 종료 일
        self.text(58, 107, str(data['days'])) # 일수

        # 결석 종류 (결석, 지각, 조퇴 중 선택)
        if data['abs_type'] == "결석": self.text(78, 107, "V")
        elif data['abs_type'] == "지각": self.text(91, 107, "V")
        elif data['abs_type'] == "조퇴": self.text(105, 107, "V")

        # 제출 일자 (중간 부분)
        today = datetime.now()
        self.text(75, 137, str(today.year))
        self.text(100, 137, str(today.month))
        self.text(118, 137, str(today.day))

        # 보호자 성함 및 서명
        self.text(115, 154, data['g_name'])
        if g_sig:
            self.image(g_sig, x=165, y=145, w=20) # 보호자 (인) 자리

        # 학생 성함 및 서명
        self.text(115, 172, data['name'])
        if s_sig:
            self.image(s_sig, x=165, y=163, w=20) # 학생 (인) 자리

        return bytes(self.output())

# --- Streamlit UI 부분은 이전과 동일하게 유지 ---
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

st.title("🏫 경기기계공고 결석신고서")
st.write("양식에 맞춰 자동으로 PDF를 생성합니다.")

with st.form("absent_form"):
    st.subheader("1. 인적사항")
    dept = st.text_input("학과", value="컴퓨터전자과")
    c1, c2, c3 = st.columns(3)
    grade = c1.selectbox("학년", [1, 2, 3], index=2)
    cls = c2.number_input("반", 1, 15, 2)
    num = c3.number_input("번호", 1, 40, 1)
    name = st.text_input("학생 성명", value="김말숙")

    st.subheader("2. 결석 내용")
    d1, d2 = st.columns(2)
    start_date = d1.date_input("시작일")
    end_date = d2.date_input("종료일")
    days = st.number_input("일수", 1, 30, 1)
    reason_cat = st.radio("사유 구분", ["인정", "질병", "기타"], horizontal=True)
    abs_type = st.radio("종류", ["결석", "지각", "조퇴"], horizontal=True)

    st.subheader("3. 보호자 서명")
    g_name = st.text_input("보호자 성함")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write("보호자 서명")
        g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig")
    with col2:
        st.write("학생 서명")
        s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig")

    submit = st.form_submit_button("✅ 신고서 PDF 생성")

    if submit:
        def process_sig(canvas):
            img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return buf

        report_data = {
            "dept": dept, "grade": grade, "cls": cls, "num": num, "name": name,
            "s_m": start_date.month, "s_d": start_date.day,
            "e_m": end_date.month, "e_d": end_date.day,
            "days": days, "reason_cat": reason_cat, "abs_type": abs_type,
            "g_name": g_name
        }

        pdf_gen = SchoolPDF()
        generated_pdf = pdf_gen.generate_report(report_data, process_sig(g_canvas), process_sig(s_canvas))
        
        if generated_pdf:
            st.session_state.pdf_data = generated_pdf
            st.success("양식 파일 생성이 완료되었습니다!")

if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
