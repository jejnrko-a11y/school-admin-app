import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance
import io
import os
import base64

# ==========================================
# 1. 초기 설정 및 한국 시간 설정
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

# 한국 시간(KST) 계산 함수
def get_kst():
    return datetime.now() + timedelta(hours=9)

ADMIN_PASSWORD = "1234" 

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

# 이미지 처리 함수 (가변 압축 알고리즘)
def process_image(image_data, mode="evidence"):
    if image_data is None: return ""
    try:
        if mode == "signature":
            img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
            img.thumbnail((200, 100)) 
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        else:
            img = Image.open(image_data)
            img = ImageOps.grayscale(img)
            img = ImageEnhance.Contrast(img).enhance(1.5)
            img = ImageEnhance.Sharpness(img).enhance(1.2)

            quality = 85
            max_width = 1100
            while True:
                temp_img = img.copy()
                temp_img.thumbnail((max_width, max_width))
                buf = io.BytesIO()
                temp_img.save(buf, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(buf.getvalue()).decode()
                if len(encoded) < 49000 or (quality <= 20 and max_width <= 400):
                    return encoded
                if quality > 30: quality -= 10
                else: max_width -= 150; quality = 50
    except: return ""

def decode_image(base64_string):
    if not base64_string: return None
    try:
        return io.BytesIO(base64.b64decode(base64_string))
    except: return None

# ==========================================
# 2. PDF 생성 클래스
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig, s_sig, evidence_img=None):
        self.add_page()
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)
        self.set_text_color(0, 0, 0)
        self.set_font('Nanum', '', 13)
        self.text(98, 55, FIXED_DEPT); self.text(140, 55, str(FIXED_GRADE))
        self.text(161, 55, str(FIXED_CLASS)); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        if g_sig: self.image(g_sig, x=174, y=112, w=18)
        if s_sig: self.image(s_sig, x=174, y=122, w=18)

        if evidence_img:
            self.add_page()
            self.image(evidence_img, x=10, y=10, w=190)
        return bytes(self.output())

# ==========================================
# 3. 앱 로직
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'target_student_name' not in st.session_state: st.session_state.target_student_name = "신고서"

st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("이동", ["메인 화면", "결석계 작성", "교사용 관리"])

if menu == "메인 화면":
    st.title("🏫 경기기계공고 행정 시스템")
    st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M:%S')}")
    st.info("왼쪽 메뉴를 이용하세요.")

elif menu == "결석계 작성":
    st.title("📝 결석신고서 작성")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("시작일", get_kst())
    end_d = c2.date_input("종료일", get_kst())
    calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
    st.info(f"평일 결석 일수: **{calc_days}일**")

    with st.form("absence_form"):
        sel_student = st.selectbox("학생 이름 선택", STUDENT_OPTIONS)
        reason_detail = st.text_area("상세 사유")
        proof_file = st.file_uploader("증빙서류 사진 첨부", type=['jpg', 'png', 'jpeg'])
        g_name = st.text_input("보호자 성함")
        sc1, sc2 = st.columns(2)
        with sc1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sc2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0:
                st.error("정보를 모두 입력해 주세요.")
            else:
                name_only = sel_student.split("(")[0]
                num_only = int(sel_student.split("(")[1].replace("번)", ""))
                st.session_state.target_student_name = name_only
                
                g_b64 = process_image(g_canvas.image_data, mode="signature")
                s_b64 = process_image(s_canvas.image_data, mode="signature")
                proof_b64 = process_image(proof_file, mode="evidence")

                rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                            "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                
                pdf_bytes = SchoolPDF().generate_report(rep_data, decode_image(g_b64), decode_image(s_b64), decode_image(proof_b64))
                st.session_state.pdf_data = pdf_bytes

                try:
                    existing = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": get_kst().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "번호": num_only, "보호자": g_name,
                        "결석기간": f"{start_d}~{end_d}", "일수": calc_days, "상세사유": reason_detail,
                        "증빙서류데이터": proof_b64, "보호자서명": g_b64, "학생서명": s_b64
                    }])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                    st.success("제출되었습니다!")
                except: st.error("저장 실패")

    if st.session_state.pdf_data:
        st.download_button("📄 통합 PDF 다운로드", data=st.session_state.pdf_data, 
                           file_name=f"결석계_{st.session_state.target_student_name}.pdf", mime="application/pdf")

elif menu == "교사용 관리":
    st.title("👨‍🏫 교사용 관리")
    pw = st.text_input("비밀번호", type="password")
    if pw == ADMIN_PASSWORD:
        try:
            data = conn.read(ttl=0)
            if not data.empty:
                data = data.sort_values(by='제출일시', ascending=False)
                for i, row in data.iterrows():
                    with st.expander(f"📌 {row['제출일시']} - {row['이름']} 학생"):
                        if st.button(f"📄 통합 PDF 생성", key=f"b_{i}"):
                            try:
                                dt = str(row['결석기간']).split('(')[0].strip()
                                sd = datetime.strptime(dt.split('~')[0].strip(), "%Y-%m-%d")
                                ed = datetime.strptime(dt.split('~')[1].strip(), "%Y-%m-%d")
                                r_data = {"num": int(float(row['번호'])), "name": str(row['이름']), 
                                          "s_m": sd.month, "s_d": sd.day, "e_m": ed.month, "e_d": ed.day,
                                          "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                                pdf_out = SchoolPDF().generate_report(r_data, decode_image(row.get('보호자서명')), decode_image(row.get('학생서명')), decode_image(row.get('증빙서류데이터')))
                                st.session_state[f"p_{i}"] = pdf_out
                            except: st.error("생성 실패")
                        if f"p_{i}" in st.session_state:
                            st.download_button("📥 다운로드", data=st.session_state[f"p_{i}"], file_name=f"{row['이름']}_결석계.pdf", key=f"d_{i}")
            else: st.info("데이터 없음")
        except: st.error("시트 로드 실패")
