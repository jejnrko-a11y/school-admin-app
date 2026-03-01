import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os
import base64  # 사진을 텍스트로 변환하기 위해 추가

# ==========================================
# 1. 초기 설정
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

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
    st.sidebar.warning("구글 시트 연결 대기 중...")

# [추가] 이미지를 텍스트로 변환하는 함수
def encode_image(uploaded_file):
    if uploaded_file is not None:
        return base64.b64encode(uploaded_file.read()).decode()
    return ""

# ==========================================
# 2. PDF 생성 클래스 (이전 좌표 유지)
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

        self.set_text_color(0, 0, 0)
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
        self.text(104.5, 105, str(data['s_m']))
        self.text(117.8, 105, str(data['s_d']))
        if g_sig: self.image(g_sig, x=174, y=112, w=18) 
        if s_sig: self.image(s_sig, x=174, y=122, w=18)
        self.text(105.5, 248, str(data['s_m']))
        self.text(118.5, 248, str(data['s_d']))
        self.text(158, 117, data['g_name']) 
        self.text(158, 126, data['name'])   
        return bytes(self.output())

# ==========================================
# 3. 앱 UI 및 로직
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"

st.title("🏫 경기기계공고 행정 시스템")

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    st.subheader("📍 1. 학생 정보")
    sel_student = st.selectbox("이름 선택", STUDENT_OPTIONS)
    name_only = sel_student.split("(")[0]
    num_only = int(sel_student.split("(")[1].replace("번)", ""))

    st.subheader("📅 2. 결석 날짜")
    d1, d2 = st.columns(2)
    s_date = d1.date_input("시작일")
    e_date = d2.date_input("종료일")

    if s_date <= e_date:
        calc_days = len(pd.bdate_range(s_date, e_date))
        st.info(f"평일 결석 일수: **{calc_days}일**")
    else:
        st.error("날짜를 확인하세요.")
        calc_days = 0

    with st.form("absence_form"):
        st.subheader("❓ 3. 사유 및 서류")
        reason_cat = st.radio("구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세내용")
        
        # [수정] 이제 드라이브가 아닌 시트 저장을 위한 파일 업로더
        proof_file = st.file_uploader("증빙서류 사진 첨부", type=['jpg', 'jpeg', 'png'])

        st.subheader("✍️ 4. 서명")
        g_name = st.text_input("보호자 성함")
        
        c1, c2 = st.columns(2)
        g_canvas = c1.st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        s_canvas = c2.st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        submit = st.form_submit_button("✅ 결석신고서 제출")

        if submit:
            if not g_name or calc_days == 0:
                st.error("정보를 모두 입력하세요.")
            else:
                # [수정] 사진을 텍스트로 변환
                img_text = encode_image(proof_file)
                
                def process_sig(canvas):
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                report_data = {
                    "num": num_only, "name": name_only,
                    "s_m": s_date.month, "s_d": s_date.day,
                    "e_m": e_date.month, "e_d": end_date.day,
                    "days": calc_days, "g_name": g_name
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(report_data, process_sig(g_canvas), process_sig(s_canvas))

                # [수정] 구글 시트에 직접 텍스트 데이터 저장
                try:
                    existing = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "번호": num_only, "보호자": g_name,
                        "결석기간": f"{s_date}~{e_date}", "일수": calc_days,
                        "증빙서류데이터": img_text  # 이 열에 사진 글자가 저장됨
                    }])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                    st.success("성공적으로 제출되었습니다!")
                except Exception as e:
                    st.error(f"저장 중 오류: {e}")

if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name_only}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
