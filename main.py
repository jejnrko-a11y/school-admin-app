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

# 이미지/서명을 텍스트로 변환 및 압축
def encode_image_to_base64(image_or_file, quality=50, size=(400, 400)):
    if image_or_file is None: return ""
    try:
        if isinstance(image_or_file, Image.Image):
            img = image_or_file
        else:
            img = Image.open(image_or_file)
        
        if img.mode != 'RGB': img = img.convert('RGB')
        img.thumbnail(size)
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=quality)
        return base64.b64encode(buffer.getvalue()).decode()
    except: return ""

# 텍스트를 다시 이미지(BytesIO)로 복구
def decode_base64_to_bytes(base64_string):
    if not base64_string: return None
    try:
        return io.BytesIO(base64.b64decode(base64_string))
    except: return None

# ==========================================
# 2. PDF 생성 클래스 (경기기계공고 전용)
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_bytes, s_sig_bytes):
        self.add_page()
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)

        self.set_text_color(0, 0, 0)
        self.set_font('Nanum', '', 13)
        # 인적사항 (좌표 유지)
        self.text(98, 55, FIXED_DEPT)      
        self.text(140, 55, str(FIXED_GRADE)) 
        self.text(161, 55, str(FIXED_CLASS))   
        self.text(177, 55, str(data['num']))   
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        
        # 날짜 및 일수
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])) 
        self.text(163, 77, str(data['s_d'])) 
        self.text(28, 85, str(data['e_m']))  
        self.text(47, 85, str(data['e_d']))  
        self.text(74, 85, str(data['days'])) 
        
        # 제출일 (시작일 기준)
        self.text(104.5, 105, str(data['s_m']))
        self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m']))
        self.text(118.5, 248, str(data['s_d']))

        # 성명 및 서명 이미지 배치
        self.text(158, 117, data['g_name']) 
        self.text(158, 126, data['name'])   
        if g_sig_bytes: self.image(g_sig_bytes, x=174, y=112, w=18)
        if s_sig_bytes: self.image(s_sig_bytes, x=174, y=122, w=18)

        return bytes(self.output())

# ==========================================
# 3. 앱 UI 및 로직
# ==========================================
st.sidebar.title("🏫 학교 행정 메뉴")
menu = st.sidebar.radio("메뉴 선택", ["메인 화면", "결석계 작성", "교사용 관리"])

if menu == "메인 화면":
    st.title("🏫 경기기계공고 행정 시스템")
    st.info("왼쪽 메뉴에서 업무를 선택해 주세요.")

elif menu == "결석계 작성":
    st.title("📝 결석신고서 작성")
    
    st.subheader("📅 날짜 설정")
    d1, d2 = st.columns(2)
    start_d = d1.date_input("시작일")
    end_d = d2.date_input("종료일")
    calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
    st.write(f"👉 결석 일수: **{calc_days}일**")

    with st.form("absent_form"):
        sel_student = st.selectbox("학생 이름 선택", STUDENT_OPTIONS)
        reason_detail = st.text_area("상세 사유")
        proof_file = st.file_uploader("증빙서류 사진", type=['jpg', 'jpeg', 'png'])
        g_name = st.text_input("보호자 성함")
        
        c1, c2 = st.columns(2)
        with c1: g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with c2: s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석계 제출"):
            name_only = sel_student.split("(")[0]
            num_only = int(sel_student.split("(")[1].replace("번)", ""))
            
            # 서명 및 이미지 데이터 처리
            g_sig_img = Image.fromarray(g_canvas.image_data.astype('uint8'), 'RGBA').convert('RGB')
            s_sig_img = Image.fromarray(s_canvas.image_data.astype('uint8'), 'RGBA').convert('RGB')
            
            g_sig_base64 = encode_image_to_base64(g_sig_img, quality=30, size=(200, 100))
            s_sig_base64 = encode_image_to_base64(s_sig_img, quality=30, size=(200, 100))
            proof_base64 = encode_image_to_base64(proof_file)

            # PDF 생성
            report_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                           "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
            
            pdf_gen = SchoolPDF()
            # PDF 생성을 위해 BytesIO로 변환하여 전달
            pdf_bytes_out = pdf_gen.generate_report(report_data, decode_base64_to_bytes(g_sig_base64), decode_base64_to_bytes(s_sig_base64))
            st.session_state.temp_pdf = pdf_bytes_out

            # 구글 시트 저장
            try:
                existing = conn.read(ttl=0)
                new_row = pd.DataFrame([{
                    "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "이름": name_only, "번호": num_only, "보호자": g_name,
                    "결석기간": f"{start_d}~{end_d}", "일수": calc_days, "상세사유": reason_detail,
                    "증빙서류데이터": proof_base64, "보호자서명": g_sig_base64, "학생서명": s_sig_base64
                }])
                conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                st.success("제출 완료!")
            except Exception as e: st.error(f"저장 실패: {e}")

    if 'temp_pdf' in st.session_state and st.session_state.temp_pdf:
        st.download_button("📄 결석계 PDF 다운로드", data=st.session_state.temp_pdf, file_name="결석계.pdf")

elif menu == "교사용 관리":
    st.title("👨‍🏫 교사용 관리")
    pw = st.text_input("비밀번호", type="password")
    
    if pw == ADMIN_PASSWORD:
        try:
            data = conn.read(ttl=0)
            if not data.empty:
                for i, row in data.iterrows():
                    with st.expander(f"{row['제출일시']} - {row['이름']} 학생"):
                        st.write(f"**결석기간:** {row['결석기간']} ({row['일수']}일간)")
                        st.write(f"**상세사유:** {row['상세사유']}")
                        
                        col_view, col_pdf = st.columns(2)
                        with col_view:
                            if row['증빙서류데이터']:
                                st.image(decode_base64_to_bytes(row['증빙서류데이터']), caption="증빙서류", width=300)
                        
                        with col_pdf:
                            st.write("📂 **관리용 파일 생성**")
                            # [교사용 PDF 재생성 로직]
                            if st.button(f"📄 {row['이름']} PDF 생성", key=f"btn_{i}"):
                                # 시트의 텍스트 데이터를 날짜 객체로 변환
                                try:
                                    s_date_str = row['결석기간'].split('~')[0]
                                    s_date_obj = datetime.strptime(s_date_str, "%Y-%m-%d")
                                    e_date_str = row['결석기간'].split('~')[1]
                                    e_date_obj = datetime.strptime(e_date_str, "%Y-%m-%d")
                                    
                                    admin_report_data = {
                                        "num": int(row['번호']), "name": row['이름'], 
                                        "s_m": s_date_obj.month, "s_d": s_date_obj.day,
                                        "e_m": e_date_obj.month, "e_d": e_date_obj.day,
                                        "days": int(row['일수']), "g_name": row['보호자']
                                    }
                                    
                                    pdf_gen_admin = SchoolPDF()
                                    admin_pdf = pdf_gen_admin.generate_report(
                                        admin_report_data, 
                                        decode_base64_to_bytes(row['보호자서명']), 
                                        decode_base64_to_bytes(row['학생서명'])
                                    )
                                    st.download_button(f"📥 {row['이름']} PDF 다운로드", data=admin_pdf, file_name=f"결석계_{row['이름']}.pdf")
                                except: st.error("PDF 생성 실패 (데이터 형식 오류)")
            else: st.info("데이터가 없습니다.")
        except: st.error("시트 로드 실패")
