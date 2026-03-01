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

# 구글 드라이브 업로드 함수
def upload_to_drive(file, folder_id):
    # Secrets에 저장된 정보를 가져와 인증
    creds_info = st.secrets["connections"]["gsheets"]
    creds = service_account.Credentials.from_service_account_info(creds_info)
    service = build('drive', 'v3', credentials=creds)

    file_metadata = {
        'name': f"{datetime.now().strftime('%m%d')}_{file.name}",
        'parents': [folder_id]
    }
    
    # 파일 타입에 맞춰 업로드
    media = MediaIoBaseUpload(file, mimetype=file.type, resumable=True)
    
    uploaded_file = service.files().create(
        body=file_metadata,
        media_body=media,
        fields='id'
    ).execute()
    
    return uploaded_file.get('id')
    
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
# 2. PDF 생성 클래스 (사용자 지정 좌표값 유지)
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

        # 텍스트 색상 검정 고정
        self.set_text_color(0, 0, 0)

        # [제공해주신 좌표값 그대로 적용]
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
        
        # 중간 날짜 (결석 시작일 기준)
        self.text(104.5, 105, str(data['s_m']))
        self.text(117.8, 105, str(data['s_d']))

        # 서명 위치 및 크기 유지
        if g_sig: self.image(g_sig, x=174, y=112, w=18) 
        if s_sig: self.image(s_sig, x=174, y=122, w=18)

        # 하단 날짜 (결석 시작일 기준)
        self.text(105.5, 248, str(data['s_m']))
        self.text(118.5, 248, str(data['s_d']))
        
        # 보호자 성함 위치 (서명 옆 빈칸 보정)
        self.set_font('Nanum', '', 12)
        self.text(158, 117, data['g_name']) # 보호자 이름
        self.text(158, 126, data['name'])   # 학생 이름

        return bytes(self.output())

# ==========================================
# 3. 앱 UI (순서 및 기능 수정)
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

    # --- 1. 학생 정보 ---
    st.subheader("📍 1. 학생 정보")
    selected_student = st.selectbox("학생 이름을 선택하세요", STUDENT_OPTIONS)
    name_only = selected_student.split("(")[0]
    num_only = int(selected_student.split("(")[1].replace("번)", ""))

    # --- 2. 결석 날짜 ---
    st.subheader("📅 2. 결석 날짜")
    d1, d2 = st.columns(2)
    start_date = d1.date_input("결석 시작일", value=datetime.now())
    end_date = d2.date_input("결석 종료일", value=datetime.now())

    if start_date <= end_date:
        business_days = pd.bdate_range(start=start_date, end=end_date)
        calc_days = len(business_days)
        st.info(f"선택하신 기간 중 **평일은 총 {calc_days}일**입니다. (주말 제외)")
    else:
        st.error("종료일이 시작일보다 빠를 수 없습니다.")
        calc_days = 0

    # --- 3. 결석 사유 및 4. 서명/증빙 (Form) ---
    with st.form("absence_form"):
        st.subheader("❓ 3. 결석 사유")
        reason_cat = st.radio("사유 구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세 사유 (병원명, 질병명, 구체적 사유 등)")

        st.subheader("✍️ 4. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        
        # 증빙서류 업로드 기능 추가
        st.subheader("📎 증빙서류 첨부 (선택)")
        proof_file = st.file_uploader("진단서, 처방전 등 사진이나 PDF 첨부", type=['jpg', 'jpeg', 'png', 'pdf'])
        
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
                def process_sig(canvas):
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        return buf
                    return None

                # 날짜 데이터 (결석 시작일 기준)
                report_data = {
                    "num": num_only, "name": name_only,
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": calc_days, "g_name": g_name
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(
                    report_data, process_sig(g_canvas), process_sig(s_canvas)
                )

                # 구글 시트 저장
                try:
                    existing_data = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "학년": FIXED_GRADE, "반": FIXED_CLASS, "번호": num_only,
                        "보호자": g_name, "결석기간": f"{start_date}~{end_date}", "일수": calc_days,
                        "사유": reason_cat, "상세사유": reason_detail,
                        "증빙서류": "유" if proof_file else "무"
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                except:
                    pass

                st.success("신고서 생성이 완료되었습니다!")

# 다운로드 버튼
if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name_only}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
