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

# 폰트 파일 경로 설정
font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"

# 2. PDF 생성 클래스 (에러 방지용 최적화)
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.set_margins(20, 20, 20) # 좌, 상, 우 여백 20mm 설정
        self.set_auto_page_break(auto=True, margin=15)
        
        # 폰트 등록
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)
        else:
            st.error("폰트 파일을 찾을 수 없습니다. GitHub 업로드 상태를 확인하세요.")

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        
        # 제목
        self.set_font('NanumB', '', 25)
        self.ln(10)
        self.cell(0, 20, '결 석 신 고 서', ln=True, align='C')
        self.ln(10)

        # 학생 정보 (학과, 학년, 반, 번호)
        self.set_font('Nanum', '', 14)
        info_text = f"( {data['dept']} )과 ( {data['grade']} )학년 ( {data['cls']} )반 ( {data['num']} )번"
        self.cell(0, 10, info_text, ln=True, align='C')
        self.cell(0, 10, f"성명: {data['name']}", ln=True, align='C')
        self.ln(15)

        # 본문 내용 (multi_cell 대신 안전한 cell 사용)
        self.set_font('Nanum', '', 12)
        text1 = f"위 본인은 [{data['reason_cat']}] (으)로 인하여 2026년 ( {data['s_m']} )월 ( {data['s_d']} )일부터"
        text2 = f"( {data['e_m']} )월 ( {data['e_d']} )일까지 ( {data['days']} 일간) [{data['abs_type']}] 하였기에"
        text3 = "보호자(보증인) 연서로 신고서를 제출합니다."
        
        self.cell(0, 10, text1, ln=True, align='L')
        self.cell(0, 10, text2, ln=True, align='L')
        self.cell(0, 10, text3, ln=True, align='L')
        self.ln(25)

        # 제출 일자
        today = datetime.now()
        self.set_font('Nanum', '', 14)
        self.cell(0, 10, f"{today.year} 년   {today.month} 월   {today.day} 일", ln=True, align='C')
        self.ln(20)

        # 서명란
        self.set_font('Nanum', '', 12)
        
        # 보호자 서명행
        current_y = self.get_y()
        self.cell(100, 10, f"보호자(보증인) : {data['g_name']}", border=0)
        if g_sig:
            self.image(g_sig, x=95, y=current_y-5, w=25) # 서명 이미지 위치
        self.set_x(130) # (인) 위치로 이동
        self.cell(0, 10, "(인)", ln=True)
        
        self.ln(5)
        
        # 학생 서명행
        current_y = self.get_y()
        self.cell(100, 10, f"학 생 : {data['name']}", border=0)
        if s_sig:
            self.image(s_sig, x=95, y=current_y-5, w=25)
        self.set_x(130)
        self.cell(0, 10, "(인)", ln=True)

        # 하단 학교명
        self.set_y(240) # 하단 근처로 이동
        self.set_font('NanumB', '', 18)
        self.cell(0, 10, "경 기 기 계 공 업 고 등 학 교 장   귀하", ln=True, align='C')

        return bytes(self.output())

# --- Streamlit 앱 인터페이스 ---
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

st.title("🏫 경기기계공고 결석신고서")

with st.form("absent_form", clear_on_submit=False):
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

    st.subheader("3. 보호자 확인 및 서명")
    g_name = st.text_input("보호자 성함", value="보호자성함")
    
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("보호자 서명")
        g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig", background_color="#eee")
    with col_sig2:
        st.write("학생 서명")
        s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig", background_color="#eee")

    submit = st.form_submit_button("✅ 신고서 PDF 생성")

    if submit:
        def process_sig(canvas):
            if canvas.image_data is not None:
                img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                return buf
            return None

        report_data = {
            "dept": dept, "grade": grade, "cls": cls, "num": num, "name": name,
            "s_m": start_date.month, "s_d": start_date.day,
            "e_m": end_date.month, "e_d": end_date.day,
            "days": days, "reason_cat": reason_cat, "abs_type": abs_type,
            "g_name": g_name
        }

        g_sig_buf = process_sig(g_canvas)
        s_sig_buf = process_sig(s_canvas)

        pdf_gen = SchoolPDF()
        generated_pdf = pdf_gen.generate_report(report_data, g_sig_buf, s_sig_buf)
        
        if generated_pdf:
            st.session_state.pdf_data = generated_pdf
            st.success("신고서 생성이 완료되었습니다! 아래 버튼을 눌러 다운로드하세요.")

# 폼 외부에서 다운로드
if st.session_state.pdf_data:
    st.download_button(
        label="📄 결석신고서 PDF 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.balloons()
