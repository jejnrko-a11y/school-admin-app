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

# 2. 폰트 파일 존재 확인 (디버깅용)
font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"

if not os.path.exists(font_path):
    st.error(f"⚠️ 폰트 파일을 찾을 수 없습니다! GitHub에 {font_path} 파일이 있는지 확인해 주세요.")

# 3. PDF 생성 클래스
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__()
        # 폰트 추가 전 에러 방지를 위해 기본 설정
        self.set_auto_page_break(auto=True, margin=15)

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        
        # 한글 폰트 등록
        try:
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)
        except Exception as e:
            st.error(f"폰트 로드 실패: {e}")
            return None

        # --- 양식 그리기 시작 ---
        self.set_font('NanumB', '', 25)
        self.cell(0, 40, '결 석 신 고 서', ln=True, align='C')
        
        self.set_font('Nanum', '', 14)
        student_info = f"( {data['dept']} )과  ( {data['grade']} )학년  ( {data['cls']} )반  ( {data['num']} )번"
        self.cell(0, 10, student_info, ln=True, align='C')
        self.cell(0, 15, f"성명: {data['name']}", ln=True, align='C')
        self.ln(10)

        self.set_font('Nanum', '', 12)
        text1 = f"위 본인은 [{data['reason_cat']}] (으)로 인하여 2026년 ( {data['s_m']} )월 ( {data['s_d']} )일부터"
        text2 = f"( {data['e_m']} )월 ( {data['e_d']} )일까지 ( {data['days']} 일간) [{data['abs_type']}] 하였기에"
        text3 = "보호자(보증인) 연서로 신고서를 제출합니다."
        
        self.multi_cell(0, 10, text1, align='L')
        self.multi_cell(0, 10, text2, align='L')
        self.multi_cell(0, 10, text3, align='L')
        self.ln(20)

        today = datetime.now()
        self.cell(0, 10, f"{today.year} 년   {today.month} 월   {today.day} 일", ln=True, align='C')
        self.ln(15)

        # 서명 이미지 삽입 로직
        y_pos = self.get_y()
        self.cell(100, 10, f"보호자(보증인) : {data['g_name']}", align='L')
        if g_sig:
            self.image(g_sig, x=75, y=y_pos-5, w=25)
        self.cell(0, 10, " (인)", ln=True, align='L')
        
        self.ln(5)
        y_pos = self.get_y()
        self.cell(100, 10, f"학 생 : {data['name']}", align='L')
        if s_sig:
            self.image(s_sig, x=75, y=y_pos-5, w=25)
        self.cell(0, 10, " (인)", ln=True, align='L')

        self.ln(30)
        self.set_font('NanumB', '', 18)
        self.cell(0, 10, "경 기 기 계 공 업 고 등 학 교 장   귀하", ln=True, align='C')

        # bytearray를 bytes로 명시적 변환하여 반환
        return bytes(self.output())

# --- 앱 UI ---
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

st.title("🏫 경기기계공고 행정 시스템")

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

    st.subheader("3. 보호자 확인 및 서명")
    g_name = st.text_input("보호자 성함", value="뿌애앵")
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.write("보호자 서명")
        g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig")
    with col_sig2:
        st.write("학생 서명")
        s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig")

    submit = st.form_submit_button("✅ 신고서 생성")

    if submit:
        # 서명 처리 함수
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

        g_sig_buf = process_sig(g_canvas)
        s_sig_buf = process_sig(s_canvas)

        pdf_gen = SchoolPDF()
        generated_pdf = pdf_gen.generate_report(report_data, g_sig_buf, s_sig_buf)
        
        if generated_pdf:
            st.session_state.pdf_data = generated_pdf
            st.success("신고서 생성이 완료되었습니다. 아래 버튼을 눌러주세요!")
        else:
            st.error("PDF 생성에 실패했습니다. 폰트 파일을 확인해 주세요.")

# 폼 외부 다운로드 버튼
if st.session_state.pdf_data:
    st.download_button(
        label="📄 경기기계공고 결석신고서 PDF 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{datetime.now().strftime('%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
