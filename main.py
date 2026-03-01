import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from google.oauth2 import service_account

# ==========================================
# 1. 환경 설정 및 학생 명부
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

# [중요!] 본인의 구글 드라이브 폴더 ID를 여기에 입력하세요
FOLDER_ID = "1so-vV-aebr9ot5FEPjxNayrNG1eFQ57Y"

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

# 구글 서비스 인증 함수
def get_gdrive_service():
    creds_info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(creds_info)
    return build('drive', 'v3', credentials=creds)

try:
    conn = st.connection("gsheets", type=GSheetsConnection)
    drive_service = get_gdrive_service()
except:
    st.sidebar.warning("구글 서비스 연결 확인 중...")

# 구글 드라이브 업로드 함수
def upload_file_to_drive(file, student_name):
    if file is not None:
        file_metadata = {
            'name': f"{datetime.now().strftime('%m%d')}_{student_name}_{file.name}",
            'parents': [FOLDER_ID]
        }
        media = MediaIoBaseUpload(io.BytesIO(file.read()), mimetype=file.type)
        uploaded = drive_service.files().create(body=file_metadata, media_body=media, fields='webViewLink').execute()
        return uploaded.get('webViewLink')
    return "없음"

# ==========================================
# 2. PDF 생성 클래스 (좌표 정밀 수정)
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
        
        # 1. 인적사항 좌표 (이전 검증 완료된 좌표)
        self.set_font('Nanum', '', 13)
        self.text(98, 55, FIXED_DEPT)      
        self.text(140, 55, str(FIXED_GRADE)) 
        self.text(161, 55, str(FIXED_CLASS))   
        self.text(177, 55, str(data['num']))   
        
        # 성명
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        
        # 2. 결석 날짜 및 일수
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])) 
        self.text(163, 77, str(data['s_d'])) 
        self.text(28, 85, str(data['e_m']))  
        self.text(47, 85, str(data['e_d']))  
        self.text(74, 85, str(data['days'])) 
        
        # 3. 모든 날짜 칸은 '결석 시작일' 기준
        self.text(104.5, 105, str(data['s_m']))
        self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m']))
        self.text(118.5, 248, str(data['s_d']))

        # 4. 이름 텍스트 추가 (서명 옆)
        self.text(158, 117, data['g_name']) 
        self.text(158, 126, data['name'])   

        # 5. 서명 이미지
        if g_sig: self.image(g_sig, x=174, y=112, w=18) 
        if s_sig: self.image(s_sig, x=174, y=122, w=18)

        return bytes(self.output())

# ==========================================
# 3. 앱 UI 및 로직 (순서 재구성)
# ==========================================
st.title("🏫 경기기계공고 행정 자동화")

if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    # --- 1. 학생 정보 ---
    st.subheader("📍 1. 학생 정보")
    sel_student = st.selectbox("이름을 선택하세요", STUDENT_OPTIONS)
    name_only = sel_student.split("(")[0]
    num_only = int(sel_student.split("(")[1].replace("번)", ""))

    # --- 2. 결석 날짜 (실시간 계산) ---
    st.subheader("📅 2. 결석 날짜")
    d1, d2 = st.columns(2)
    start_d = d1.date_input("결석 시작일", value=datetime.now())
    end_d = d2.date_input("결석 종료일", value=datetime.now())

    if start_d <= end_d:
        calc_days = len(pd.bdate_range(start_d, end_d))
        st.info(f"평일 기준 **총 {calc_days}일** 결석 (주말 제외)")
    else:
        st.error("날짜 설정을 확인하세요.")
        calc_days = 0

    with st.form("absent_form"):
        # --- 3. 결석 사유 ---
        st.subheader("❓ 3. 결석 사유")
        reason_cat = st.radio("사유 구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세 사유")

        # --- 4. 증빙서류 및 서명 ---
        st.subheader("✍️ 4. 서명 및 증빙서류")
        g_name = st.text_input("보호자 성함")
        proof_file = st.file_uploader("증빙서류(사진/PDF) 첨부", type=['jpg', 'jpeg', 'png', 'pdf'])
        
        col_s1, col_s2 = st.columns(2)
        with col_s1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with col_s2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        submit = st.form_submit_button("✅ 결석신고서 제출")

        if submit:
            if not g_name or calc_days == 0:
                st.error("정보를 모두 입력해 주세요.")
            else:
                # [파일 업로드]
                file_url = upload_file_to_drive(proof_file, name_only)
                
                # [PDF 생성]
                def process_sig(canvas):
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                report_data = {
                    "num": num_only, "name": name_only,
                    "s_m": start_d.month, "s_d": start_d.day,
                    "e_m": end_d.month, "e_d": end_d.day,
                    "days": calc_days, "g_name": g_name
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(report_data, process_sig(g_canvas), process_sig(s_canvas))

                # [시트 저장]
                try:
                    existing = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "번호": num_only, "보호자": g_name,
                        "결석기간": f"{start_d}~{end_d}", "일수": calc_days,
                        "증빙서류링크": file_url
                    }])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                except:
                    pass
                st.success("신고서 생성 및 제출 완료!")

if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name_only}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
