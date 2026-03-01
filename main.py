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
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("구글 시트 연결 설정이 필요합니다.")

# 3. PDF 생성 클래스
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__()
        try:
            self.add_font('Nanum', '', 'NanumGothic-Regular.ttf')
            self.add_font('NanumB', '', 'NanumGothic-Bold.ttf')
        except:
            pass # 폰트가 없을 경우 기본 폰트 사용

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        self.set_font('NanumB', '', 25)
        self.cell(0, 40, '결 석 신 고 서', ln=True, align='C')
        self.ln(5)
        self.set_font('Nanum', '', 14)
        student_info = f"( {data['dept']} )과  ( {data['grade']} )학년  ( {data['cls']} )반  ( {data['num']} )번"
        self.cell(0, 10, student_info, ln=True, align='C')
        self.cell(0, 15, f"성명: {data['name']}", ln=True, align='C')
        self.ln(10)
        self.set_font('Nanum', '', 12)
        text1 = f"위 본인은 [{data['reason_cat']}] (으)로 인하여 2026년 ( {data['s_m']} )월 ( {data['s_d']} )일부터"
        text2 = f"( {data['e_m']} )월 ( {data['e_d']} )일까지 ( {data['days']} 일간) [{data['abs_type']}] 하였기에"
        text3 = "보호자(보증인) 연서로 신고서를 제출합니다."
        self.cell(0, 10, text1, ln=True, align='L')
        self.cell(0, 10, text2, ln=True, align='L')
        self.cell(0, 10, text3, ln=True, align='L')
        self.ln(20)
        today = datetime.now()
        self.set_font('Nanum', '', 14)
        self.cell(0, 10, f"{today.year} 년   {today.month} 월   {today.day} 일", ln=True, align='C')
        self.ln(15)
        y_pos = self.get_y()
        self.cell(100, 10, f"보호자(보증인) : {data['g_name']}", align='L')
        if g_sig:
            try: self.image(g_sig, x=75, y=y_pos-5, w=25)
            except: pass
        self.cell(0, 10, "(인)", ln=True, align='L')
        self.ln(5)
        y_pos = self.get_y()
        self.cell(100, 10, f"학 생 : {data['name']}", align='L')
        if s_sig:
            try: self.image(s_sig, x=75, y=y_pos-5, w=25)
            except: pass
        self.cell(0, 10, "(인)", ln=True, align='L')
        self.ln(30)
        self.set_font('NanumB', '', 18)
        self.cell(0, 10, "경 기 기 계 공 업 고 등 학 교 장   귀하", ln=True, align='C')
        return self.output()

# --- 앱 UI 및 세션 상태 ---
if 'page' not in st.session_state: st.session_state.page = "home"
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'file_name' not in st.session_state: st.session_state.file_name = ""

st.title("🏫 경기기계공고 행정 시스템")

if st.session_state.page == "home":
    col1, col2 = st.columns(2)
    if col1.button("📝 결석신고서 작성", use_container_width=True):
        st.session_state.page = "form"
        st.session_state.pdf_data = None # 초기화
        st.rerun()
    if col2.button("🏃 조퇴/외출증", use_container_width=True):
        st.info("준비 중입니다.")

elif st.session_state.page == "form":
    if st.button("⬅️ 메인으로"):
        st.session_state.page = "home"
        st.rerun()

    # 양식 부분
    with st.form("absent_form"):
        st.subheader("1. 인적사항")
        dept = st.text_input("학과")
        c1, c2, c3 = st.columns(3)
        grade = c1.selectbox("학년", [1, 2, 3])
        cls = c2.number_input("반", 1, 15, 1)
        num = c3.number_input("번호", 1, 40, 1)
        name = st.text_input("학생 성명")

        st.subheader("2. 결석 내용")
        d1, d2 = st.columns(2)
        start_date = d1.date_input("시작일")
        end_date = d2.date_input("종료일")
        days = st.number_input("일수", 1, 30, 1)
        reason_cat = st.radio("사유 구분", ["인정", "질병", "기타"], horizontal=True)
        abs_type = st.radio("종류", ["결석", "지각", "조퇴"], horizontal=True)

        st.subheader("3. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig")
        with col_sig2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig")

        submit = st.form_submit_button("✅ 신고서 생성")

        if submit:
            if not name or not g_name:
                st.error("이름과 보호자 성함을 입력해 주세요.")
            else:
                # PDF 생성 로직
                report_data = {
                    "dept": dept, "grade": grade, "cls": cls, "num": num, "name": name,
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": days, "reason_cat": reason_cat, "abs_type": abs_type,
                    "g_name": g_name
                }
                
                def get_sig_image(canvas):
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                g_sig_buf = get_sig_image(g_canvas)
                s_sig_buf = get_sig_image(s_canvas)

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(report_data, g_sig_buf, s_sig_buf)
                st.session_state.file_name = f"결석신고서_{name}.pdf"
                st.success("신고서 생성이 완료되었습니다. 아래 다운로드 버튼을 눌러주세요!")

    # [핵심] 폼(Form) 밖에서 다운로드 버튼 배치
    if st.session_state.pdf_data:
        st.markdown("---")
        st.download_button(
            label="📄 경기기계공고 결석신고서 PDF 다운로드",
            data=st.session_state.pdf_data,
            file_name=st.session_state.file_name,
            mime="application/pdf",
            use_container_width=True
        )
        st.balloons()
