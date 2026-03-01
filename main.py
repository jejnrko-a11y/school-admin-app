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

# [핵심 수정] 이미지를 50,000자 이하로 압축하는 함수
def encode_image_compressed(uploaded_file):
    if uploaded_file is not None:
        try:
            # 1. 이미지 열기
            img = Image.open(uploaded_file)
            # 2. RGB 모드로 변경 (RGBA나 다른 모드일 경우 에러 방지)
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            # 3. 크기 조절 (가로 400px 기준으로 비율 유지)
            base_width = 400
            w_percent = (base_width / float(img.size[0]))
            h_size = int((float(img.size[1]) * float(w_percent)))
            img = img.resize((base_width, h_size), Image.LANCZOS)
            
            # 4. 압축하여 버퍼에 저장 (JPEG 화질 50%로 낮춤)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=50, optimize=True)
            
            # 5. Base64 변환
            encoded = base64.b64encode(buffer.getvalue()).decode()
            
            # 6. 구글 시트 제한(50,000자) 확인
            if len(encoded) > 50000:
                # 더 작게 한 번 더 압축
                img = img.resize((200, int(h_size * 0.5)), Image.LANCZOS)
                buffer = io.BytesIO()
                img.save(buffer, format="JPEG", quality=30)
                encoded = base64.b64encode(buffer.getvalue()).decode()
                
            return encoded
        except Exception as e:
            st.warning(f"사진 압축 실패: {e}")
            return "압축실패"
    return ""

# ==========================================
# 2. PDF 생성 클래스 (기존 좌표 유지)
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
# 3. 앱 UI
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"

st.title("🏫 경기기계공고 행정 시스템")

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    st.subheader("📅 결석 날짜 설정")
    d1, d2 = st.columns(2)
    start_date = d1.date_input("시작일")
    end_date = d2.date_input("종료일")
    
    if start_date <= end_date:
        business_days = pd.bdate_range(start_date, end_date)
        calc_days = len(business_days)
        st.info(f"평일 결석 일수: **{calc_days}일** (주말 제외)")
    else:
        st.error("날짜를 확인하세요.")
        calc_days = 0

    with st.form("absence_form"):
        st.subheader("📍 1. 학생 선택")
        sel_student = st.selectbox("이름을 선택하세요", STUDENT_OPTIONS)
        
        st.subheader("❓ 2. 사유 및 서류")
        reason_cat = st.radio("구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세내용")
        
        # [수정] PDF는 압축이 어려우므로 사진(JPG, PNG) 위주로 권장
        proof_file = st.file_uploader("증빙서류 사진 첨부 (JPG, PNG)", type=['jpg', 'jpeg', 'png'])

        st.subheader("✍️ 3. 서명란")
        g_name = st.text_input("보호자 성함")
        
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with col_sig2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        submit = st.form_submit_button("✅ 결석신고서 제출 및 저장")

        if submit:
            if not g_name or calc_days == 0:
                st.error("보호자 성함과 날짜를 다시 확인해 주세요.")
            else:
                # [압축 함수 호출]
                img_text = encode_image_compressed(proof_file)
                
                def process_sig(canvas):
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                report_data = {
                    "num": int(sel_student.split("(")[1].replace("번)", "")), 
                    "name": sel_student.split("(")[0],
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": calc_days, "g_name": g_name
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(report_data, process_sig(g_canvas), process_sig(s_canvas))

                try:
                    existing = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": report_data["name"], "번호": report_data["num"], "보호자": g_name,
                        "결석기간": f"{start_date}~{end_date}", "일수": calc_days,
                        "상세사유": reason_detail, "증빙서류데이터": img_text
                    }])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                    st.success("성공적으로 제출되었습니다!")
                except Exception as e:
                    st.error(f"시트 저장 실패: {e}")

if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{datetime.now().strftime('%m%d')}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
