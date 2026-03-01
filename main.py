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
# 1. 초기 설정
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

# [교사용 비밀번호 설정] - 원하시는 번호로 바꾸세요
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

# 사진을 글자로 변환 (압축 포함)
def encode_image_compressed(uploaded_file):
    if uploaded_file is not None:
        try:
            img = Image.open(uploaded_file)
            if img.mode != 'RGB': img = img.convert('RGB')
            img.thumbnail((400, 400)) # 크기 축소
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=50)
            return base64.b64encode(buffer.getvalue()).decode()
        except: return "압축실패"
    return ""

# [추가] 글자를 다시 사진으로 복구하는 함수
def decode_image(base64_string):
    try:
        img_data = base64.b64decode(base64_string)
        return Image.open(io.BytesIO(img_data))
    except:
        return None

# ==========================================
# 2. PDF 생성 클래스 (생략 - 기존과 동일)
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)
    def generate_report(self, data, g_sig, s_sig):
        self.add_page()
        if os.path.exists(bg_image_path): self.image(bg_image_path, x=0, y=0, w=210, h=297)
        self.set_text_color(0, 0, 0)
        self.set_font('Nanum', '', 13)
        self.text(98, 55, FIXED_DEPT); self.text(140, 55, str(FIXED_GRADE))
        self.text(161, 55, str(FIXED_CLASS)); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        self.set_font('Nanum', '', 12); self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        if g_sig: self.image(g_sig, x=174, y=112, w=18)
        if s_sig: self.image(s_sig, x=174, y=122, w=18)
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        return bytes(self.output())

# ==========================================
# 3. 앱 UI
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"

st.sidebar.title("🏫 메뉴")
menu_choice = st.sidebar.radio("이동하기", ["메인 화면", "결석계 작성", "교사용 관리"])

if menu_choice == "메인 화면":
    st.title("🏫 경기기계공고 행정 시스템")
    st.write("왼쪽 메뉴에서 원하는 기능을 선택하세요.")
    col1, col2 = st.columns(2)
    if col1.button("📝 결석계 작성"):
        st.session_state.menu = "결석계"
        st.rerun()

elif menu_choice == "결석계 작성":
    st.title("📝 결석신고서 작성")
    # (기존 결석계 작성 코드 부분)
    d1, d2 = st.columns(2)
    start_date = d1.date_input("시작일"); end_date = d2.date_input("종료일")
    calc_days = len(pd.bdate_range(start_date, end_date)) if start_date <= end_date else 0
    st.info(f"평일 결석 일수: **{calc_days}일**")

    with st.form("absence_form"):
        sel_student = st.selectbox("이름 선택", STUDENT_OPTIONS)
        reason_detail = st.text_area("상세내용")
        proof_file = st.file_uploader("증빙서류 사진", type=['jpg', 'jpeg', 'png'])
        g_name = st.text_input("보호자 성함")
        c1, c2 = st.columns(2)
        with c1: g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with c2: s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")
        
        if st.form_submit_button("✅ 제출 및 저장"):
            img_text = encode_image_compressed(proof_file)
            report_data = {"num": int(sel_student.split("(")[1].replace("번)", "")), "name": sel_student.split("(")[0],
                           "s_m": start_date.month, "s_d": start_date.day, "e_m": end_date.month, "e_d": end_date.day,
                           "days": calc_days, "g_name": g_name}
            
            # PDF 생성 로직
            pdf_gen = SchoolPDF()
            # 서명 처리 함수 생략(기존과 동일)
            def ps(cv):
                img = Image.fromarray(cv.image_data.astype('uint8'), 'RGBA')
                b = io.BytesIO(); img.save(b, format="PNG"); return b
            st.session_state.pdf_data = pdf_gen.generate_report(report_data, ps(g_canvas), ps(s_canvas))
            
            # 시트 저장
            try:
                existing = conn.read(ttl=0)
                new_row = pd.DataFrame([{"제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                                         "이름": report_data["name"], "번호": report_data["num"],
                                         "보호자": g_name, "결석기간": f"{start_date}~{end_date}",
                                         "상세사유": reason_detail, "증빙서류데이터": img_text}])
                conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                st.success("제출 완료!")
            except: st.error("시트 저장 실패")

    if st.session_state.pdf_data:
        st.download_button("📄 PDF 다운로드", data=st.session_state.pdf_data, file_name=f"결석계.pdf", mime="application/pdf")

# ==========================================
# 4. [신규] 교사용 관리 페이지
# ==========================================
elif menu_choice == "교사용 관리":
    st.title("👨‍🏫 교사용 관리 페이지")
    pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if pw == ADMIN_PASSWORD:
        st.success("인증되었습니다.")
        try:
            # 시트 데이터 불러오기
            data = conn.read(ttl=0)
            if not data.empty:
                st.subheader("📋 최근 제출 현황")
                # 리스트 형태로 보여주기
                for i, row in data.iterrows():
                    with st.expander(f"{row['제출일시']} - {row['이름']}({row['번호']}번) 학생"):
                        st.write(f"**보호자:** {row['보호자']}")
                        st.write(f"**결석기간:** {row['결석기간']}")
                        st.write(f"**상세사유:** {row['상세사유']}")
                        
                        # [핵심] 사진 복구 출력
                        if row['증빙서류데이터']:
                            st.write("**첨부된 증빙서류:**")
                            decoded_img = decode_image(row['증빙서류데이터'])
                            if decoded_img:
                                st.image(decoded_img, caption=f"{row['이름']} 학생 증빙서류", width=400)
                            else:
                                st.warning("사진을 불러올 수 없습니다.")
                        else:
                            st.info("첨부된 서류가 없습니다.")
            else:
                st.info("제출된 데이터가 없습니다.")
        except:
            st.error("데이터를 가져오는 데 실패했습니다.")
    elif pw != "":
        st.error("비밀번호가 틀렸습니다.")
