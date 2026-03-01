import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image
import io
import os

# ==========================================
# 1. 초기 설정 및 학생 명부
# ==========================================
st.set_page_config(page_title="경기기계공고 결석신고서", layout="centered")

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
# 2. PDF 생성 클래스 (좌표 및 날짜 로직 수정)
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
        
        # 1. 학생 정보 (학과, 학년, 반, 번호)
        self.set_font('Nanum', '', 13)
        self.text(68, 48, FIXED_DEPT)      
        self.text(125, 48, str(FIXED_GRADE)) 
        self.text(147, 48, str(FIXED_CLASS))   
        self.text(169, 48, str(data['num']))   
        
        # 성명 (성명 칸 옆)
        self.set_font('NanumB', '', 15)
        self.text(138, 59, data['name']) # 위치 재조정
        
        # 2. 결석 기간 및 일수
        self.set_font('Nanum', '', 12)
        self.text(148, 77, str(data['s_m'])) 
        self.text(168, 77, str(data['s_d'])) 
        self.text(32, 88, str(data['e_m']))  
        self.text(53, 88, str(data['e_d']))  
        self.text(77, 88, str(data['days'])) 

        # 3. 신고 날짜 (결석 시작일 기준으로 세팅)
        self.set_font('Nanum', '', 13)
        self.text(82, 120, str(data['s_y']))  # 결석 시작 연도
        self.text(108, 120, str(data['s_m'])) # 결석 시작 월
        self.text(126, 120, str(data['s_d'])) # 결석 시작 일

        # 4. 보호자 및 학생 성명/서명
        self.text(118, 138, data['g_name']) # 보호자 이름 노출 수정
        if g_sig:
            self.image(g_sig, x=168, y=129, w=22) 
            
        self.text(138, 153, data['name'])   # 학생 이름 노출 수정
        if s_sig:
            self.image(s_sig, x=168, y=144, w=22)

        # 5. 하단 날짜 (마찬가지로 시작일 기준)
        self.text(100, 246, str(data['s_y']))
        self.text(128, 246, str(data['s_m']))
        self.text(145, 246, str(data['s_d']))

        return bytes(self.output())

# ==========================================
# 3. 앱 UI (순서 재구성 및 증빙서류 추가)
# ==========================================
st.title("🏫 경기기계공고 결석신고서")

if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None

if st.session_state.menu == "메인 화면":
    if st.button("📝 결석신고서 작성 시작", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    # 1. 학생 정보
    st.subheader("📍 1. 학생 정보")
    selected_student = st.selectbox("학생 이름을 선택하세요", STUDENT_OPTIONS)
    name_only = selected_student.split("(")[0]
    num_only = int(selected_student.split("(")[1].replace("번)", ""))

    # 2. 결석 날짜 (실시간 계산)
    st.subheader("📅 2. 결석 날짜")
    col_d1, col_d2 = st.columns(2)
    s_date = col_d1.date_input("결석 시작일")
    e_date = col_d2.date_input("결석 종료일")
    
    # 주말 제외 평일 계산
    if s_date <= e_date:
        calc_days = len(pd.bdate_range(s_date, e_date))
        st.info(f"계산된 결석 일수: **{calc_days}일** (주말 제외)")
    else:
        st.error("날짜를 다시 확인해 주세요.")
        calc_days = 0

    # 3. 결석 사유 및 서명 (Form 시작)
    with st.form("absent_form"):
        st.subheader("❓ 3. 결석 사유")
        reason_cat = st.radio("사유 구분", ["질병", "인정", "기타"], horizontal=True)
        reason_detail = st.text_area("상세 사유 (병원명, 사유 등)")
        
        # 증빙 서류 업로드
        st.subheader("📎 4. 증빙서류 첨부")
        proof_file = st.file_uploader("병원 진단서, 확인서 등을 업로드하세요", type=['jpg', 'jpeg', 'png', 'pdf'])

        st.subheader("✍️ 5. 보호자 확인 및 서명")
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

        submit = st.form_submit_button("✅ 결석신고서 생성 및 제출")

        if submit:
            if not g_name or not reason_detail:
                st.error("상세 사유와 보호자 성함을 입력해 주세요.")
            else:
                def process_sig(canvas):
                    if canvas.image_data is not None:
                        img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                        buf = io.BytesIO()
                        img.save(buf, format="PNG")
                        return buf
                    return None

                # PDF용 데이터 구성 (시작일 정보 포함)
                report_data = {
                    "num": num_only, "name": name_only,
                    "s_y": s_date.year, "s_m": s_date.month, "s_d": s_date.day,
                    "e_m": e_date.month, "e_d": e_date.day,
                    "days": calc_days, "g_name": g_name, "reason_cat": reason_cat
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(
                    report_data, process_sig(g_canvas), process_sig(s_canvas)
                )

                # 구글 시트 저장 (증빙서류 유무 포함)
                try:
                    existing_data = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "번호": num_only, "사유": reason_cat,
                        "상세사유": reason_detail, "보호자": g_name,
                        "기간": f"{s_date}~{e_date}", "증빙서류": "유" if proof_file else "무"
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                except:
                    pass

                st.success("신고서 생성이 완료되었습니다!")

# 다운로드 버튼
if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 PDF 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{name_only}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
