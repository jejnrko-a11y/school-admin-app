import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os

# ==========================================
# 1. 초기 설정 및 학생 명부
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 자동화", layout="centered")

FIXED_DEPT = "컴퓨터전자과"
FIXED_GRADE = 3
FIXED_CLASS = 2

STUDENT_LIST = [
    {"name": "가나다", "num": 1},
    {"name": "마바사", "num": 2},
    {"name": "홍길동", "num": 3},
]
STUDENT_OPTIONS = [f"{s['name']}({s['num']}번)" for s in STUDENT_LIST]

font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"
bg_image_path = "background.png"

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    pass

# ==========================================
# 2. PDF 생성 클래스
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)

        self.set_font('Nanum', '', 13)
        self.text(98, 55, FIXED_DEPT)      
        self.text(140, 55, str(FIXED_GRADE)) 
        self.text(161, 55, str(FIXED_CLASS))   
        self.text(177, 55, str(data['num']))   
        
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])) 
        self.text(163, 77, str(data['s_d'])) 
        self.text(28, 85, str(data['e_m']))  
        self.text(47, 85, str(data['e_d']))  
        self.text(74, 85, str(data['days'])) 
        
        today = datetime.now()
        self.text(104.5, 105, str(today.month))
        self.text(117.8, 105, str(today.day))

        if g_sig: self.image(g_sig, x=174, y=112, w=18) 
        if s_sig: self.image(s_sig, x=174, y=122, w=18)

        self.text(105.5, 248, str(today.month))
        self.text(118.5, 248, str(today.day))

        return bytes(self.output())

# ==========================================
# 3. 앱 UI
# ==========================================
st.title("🏫 경기기계공고 행정 시스템")

if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    # --- [실시간 계산을 위해 날짜 입력을 Form 밖으로 배치] ---
    st.subheader("📅 결석 날짜 설정 (주말 제외 자동 계산)")
    d1, d2 = st.columns(2)
    # 한글화를 위해 format 변경 및 브라우저가 한국어면 한글로 뜹니다.
    start_date = d1.date_input("결석 시작일", value=datetime.now())
    end_date = d2.date_input("결석 종료일", value=datetime.now())

    # [실시간 주말 제외 결석 일수 계산 로직]
    if start_date <= end_date:
        # pandas의 bdate_range를 사용하여 평일(월-금)만 계산
        business_days = pd.bdate_range(start=start_date, end=end_date)
        calc_days = len(business_days)
        st.info(f"선택하신 기간 중 **평일은 총 {calc_days}일**입니다. (주말 제외)")
    else:
        st.error("종료일이 시작일보다 빠를 수 없습니다.")
        calc_days = 0

    # --- [나머지 정보 입력을 위한 Form] ---
    with st.form("absence_form"):
        st.subheader("📍 1. 학생 정보")
        selected_student = st.selectbox("학생 이름을 선택하세요", STUDENT_OPTIONS)
        
        st.subheader("✍️ 2. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", 
                                 background_color="rgba(0,0,0,0)", update_streamlit=True)
        with col_sig2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", 
                                 background_color="rgba(0,0,0,0)", update_streamlit=True)

        submit = st.form_submit_button("✅ 결석신고서 PDF 생성")

        if submit:
            if not g_name or calc_days == 0:
                st.error("보호자 성함과 날짜를 확인해 주세요.")
            else:
                # 데이터 분리
                name_only = selected_student.split("(")[0]
                num_only = int(selected_student.split("(")[1].replace("번)", ""))
                
                def process_sig(canvas):
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        return buf
                    return None

                report_data = {
                    "num": num_only, "name": name_only,
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": calc_days, "g_name": g_name,
                    "dept": FIXED_DEPT, "grade": FIXED_GRADE, "cls": FIXED_CLASS
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(
                    report_data, process_sig(g_canvas), process_sig(s_canvas)
                )
                st.success("PDF 생성이 완료되었습니다!")

# 다운로드 버튼
if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{datetime.now().strftime('%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
