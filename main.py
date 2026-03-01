import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os
import base64

# ==========================================
# 1. 초기 설정 및 명부
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

ADMIN_PASSWORD = "1234" # 교사용 비밀번호

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

# 이미지 처리를 위한 함수들
def encode_image(image_or_file, quality=50):
    if image_or_file is None: return ""
    try:
        if isinstance(image_or_file, Image.Image): img = image_or_file
        else: img = Image.open(image_or_file)
        if img.mode != 'RGB': img = img.convert('RGB')
        img.thumbnail((400, 400))
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=quality)
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

def decode_image(base64_string):
    if not base64_string: return None
    try:
        return io.BytesIO(base64.b64decode(base64_string))
    except: return None

# ==========================================
# 2. PDF 생성 클래스 (좌표 유지)
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
        # 인적사항 좌표
        self.text(98, 55, FIXED_DEPT)      
        self.text(140, 55, str(FIXED_GRADE)) 
        self.text(161, 55, str(FIXED_CLASS))   
        self.text(177, 55, str(data['num']))   
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        # 날짜 좌표
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d'])) 
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days'])) 
        # 하단 날짜 (결석 시작일 기준)
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        # 이름 및 서명
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        if g_sig: self.image(g_sig, x=174, y=112, w=18)
        if s_sig: self.image(s_sig, x=174, y=122, w=18)
        return bytes(self.output())

# ==========================================
# 3. 메인 로직 및 UI
# ==========================================
st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("메뉴 선택", ["메인 화면", "결석계 작성", "교사용 관리"])

if menu == "메인 화면":
    st.title("🏫 경기기계공고 행정 시스템")
    st.write("원하시는 기능을 왼쪽 메뉴에서 선택해 주세요.")
    col1, col2 = st.columns(2)
    col1.metric("오늘의 결석", "0건")
    col2.metric("접수된 서류", "미정")

elif menu == "결석계 작성":
    st.title("📝 결석신고서 작성")
    
    st.subheader("📅 1. 결석 날짜 설정")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("시작일", datetime.now())
    end_d = c2.date_input("종료일", datetime.now())
    
    calc_days = 0
    if start_d <= end_d:
        calc_days = len(pd.bdate_range(start_d, end_d))
        st.info(f"평일 결석 일수: **{calc_days}일** (주말 제외)")
    else: st.error("날짜를 확인해 주세요.")

    with st.form("absence_form"):
        st.subheader("📍 2. 학생 정보 및 사유")
        sel_student = st.selectbox("학생 이름 선택", STUDENT_OPTIONS)
        reason_cat = st.radio("사유 구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세 사유")
        proof_file = st.file_uploader("증빙서류 사진", type=['jpg', 'jpeg', 'png'])

        st.subheader("✍️ 3. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        sig_col1, sig_col2 = st.columns(2)
        with sig_col1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sig_col2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0:
                st.error("보호자 성함과 날짜를 확인해 주세요.")
            else:
                name_only = sel_student.split("(")[0]
                num_only = int(sel_student.split("(")[1].replace("번)", ""))
                
                # 데이터 인코딩
                g_sig_img = Image.fromarray(g_canvas.image_data.astype('uint8'), 'RGBA')
                s_sig_img = Image.fromarray(s_canvas.image_data.astype('uint8'), 'RGBA')
                g_sig_b64 = encode_image(g_sig_img, quality=30)
                s_sig_b64 = encode_image(s_sig_img, quality=30)
                proof_b64 = encode_image(proof_file)

                # PDF 생성
                report_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                               "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                pdf_gen = SchoolPDF()
                pdf_out = pdf_gen.generate_report(report_data, decode_image(g_sig_b64), decode_image(s_sig_b64))
                st.session_state.temp_pdf = pdf_out

                # 시트 저장
                try:
                    existing = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "번호": num_only, "보호자": g_name,
                        "결석기간": f"{start_d}~{end_d}", "일수": calc_days, "상세사유": reason_detail,
                        "증빙서류데이터": proof_b64, "보호자서명": g_sig_b64, "학생서명": s_sig_b64
                    }])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                    st.success("제출 완료!")
                except Exception as e: st.error(f"저장 실패: {e}")

    if 'temp_pdf' in st.session_state:
        st.download_button("📄 완성된 결석계 PDF 다운로드", data=st.session_state.temp_pdf, file_name="결석신고서.pdf")

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
                        st.write(f"**결석기간:** {row['결석기간']} ({row['일수']}일간)")
                        col_v, col_p = st.columns(2)
                        with col_v:
                            if row.get('증빙서류데이터'): st.image(decode_image(row['증빙서류데이터']), width=300)
                        with col_p:
                            if st.button(f"📄 {row['이름']} PDF 생성", key=f"b_{i}"):
                                try:
                                    dt_part = str(row['결석기간']).split('(')[0].strip()
                                    sd = datetime.strptime(dt_part.split('~')[0].strip(), "%Y-%m-%d")
                                    ed = datetime.strptime(dt_part.split('~')[1].strip(), "%Y-%m-%d")
                                    r_data = {"num": int(float(row['번호'])), "name": str(row['이름']), 
                                              "s_m": sd.month, "s_d": sd.day, "e_m": ed.month, "e_d": ed.day,
                                              "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                                    pdf_bytes = SchoolPDF().generate_report(r_data, decode_image(row.get('보호자서명')), decode_image(row.get('학생서명')))
                                    st.session_state[f"p_{i}"] = pdf_bytes
                                except Exception as e: st.error(f"변환 오류: {e}")
                            if f"p_{i}" in st.session_state:
                                st.download_button("📥 PDF 다운로드", data=st.session_state[f"p_{i}"], file_name=f"{row['이름']}_결석계.pdf", key=f"d_{i}")
            else: st.info("데이터가 없습니다.")
        except: st.error("시트 로드 실패")
