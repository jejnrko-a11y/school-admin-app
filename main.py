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
st.set_page_config(page_title="경기기계공고 행정 자동화", layout="centered")

# [고정 정보]
FIXED_DEPT = "컴퓨터전자과"
FIXED_GRADE = 3
FIXED_CLASS = 2

# [학생 명부] - 나중에 이 리스트만 업데이트하면 됩니다.
STUDENT_LIST = [
    {"name": "가나다", "num": 1},
    {"name": "마바사", "num": 2},
    {"name": "홍길동", "num": 3},
]
# 셀렉트박스용 표시 텍스트 생성
STUDENT_OPTIONS = [f"{s['name']}({s['num']}번)" for s in STUDENT_LIST]

font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"
bg_image_path = "background.png"

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.sidebar.warning("구글 시트 연결 대기 중...")

# ==========================================
# 2. PDF 생성 클래스
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)
        else:
            st.error("폰트 파일을 찾을 수 없습니다.")

    def draw_grid(self):
        self.set_draw_color(255, 0, 0)
        self.set_text_color(255, 0, 0)
        self.set_font('Arial', '', 8)
        for x in range(0, 211, 10):
            self.line(x, 0, x, 297)
            self.text(x + 1, 5, str(x))
        for y in range(0, 298, 10):
            self.line(0, y, 210, y)
            self.text(1, y - 1, str(y))
        self.set_text_color(0, 0, 0)

    def generate_report(self, data, g_sig, s_sig, debug_mode=False):
        self.add_page()
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)
        if debug_mode:
            self.draw_grid()

        self.set_font('Nanum', '', 13)

        # --- [보정된 좌표값] ---
        # 1. 인적사항 (고정값 반영)
        self.text(98, 55, FIXED_DEPT)      
        self.text(140, 55, str(FIXED_GRADE)) 
        self.text(161, 55, str(FIXED_CLASS))   
        self.text(177, 55, str(data['num']))   
        
        # 2. 성명
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        
        # 3. 결석 날짜 및 자동 계산된 일수
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])) 
        self.text(163, 77, str(data['s_d'])) 
        self.text(28, 85, str(data['e_m']))  
        self.text(47, 85, str(data['e_d']))  
        self.text(74, 85, str(data['days'])) 
        
        # 4. 중간 제출 날짜 (한글 형식)
        today = datetime.now()
        self.text(104.5, 105, str(today.month))
        self.text(117.8, 105, str(today.day))

        # 5. 보호자 성함 및 투명 서명
        self.text(158, 117, data['g_name']) 
        if g_sig:
            self.image(g_sig, x=174, y=112, w=18) 
            
        # 6. 학생 성함 및 투명 서명
        self.text(158, 126, data['name'])   
        if s_sig:
            self.image(s_sig, x=174, y=122, w=18)

        # 7. 맨 아래 하단 날짜
        self.text(105.5, 248, str(today.month))
        self.text(118.5, 248, str(today.day))

        return bytes(self.output())

# ==========================================
# 3. 앱 UI
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"

st.title("🏫 경기기계공고 행정 시스템")

debug_mode = st.checkbox("🔍 좌표 가이드 보기 (개발자용)")

if st.session_state.menu == "메인 화면":
    col1, col2 = st.columns(2)
    if col1.button("📝\n결석신고서 작성", use_container_width=True):
        st.session_state.menu = "결석계"
        st.rerun()
    if col2.button("🏃\n조퇴/외출증 (준비중)", use_container_width=True):
        st.info("준비 중인 기능입니다.")

elif st.session_state.menu == "결석계":
    if st.button("⬅️ 메인으로 돌아가기"):
        st.session_state.menu = "메인 화면"
        st.rerun()

    with st.form("absence_form"):
        st.subheader("📍 1. 인적사항 (컴퓨터전자과 3-2 고정)")
        
        # [학생 선택 명부]
        selected_student = st.selectbox("학생 이름을 선택하세요", STUDENT_OPTIONS)
        # 선택된 이름과 번호 분리
        name_only = selected_student.split("(")[0]
        num_only = int(selected_student.split("(")[1].replace("번)", ""))

        st.subheader("📅 2. 결석 날짜 (자동 일수 계산)")
        d1, d2 = st.columns(2)
        start_date = d1.date_input("결석 시작일", format="YYYY/MM/DD")
        end_date = d2.date_input("결석 종료일", format="YYYY/MM/DD")
        
        # [결석 일수 자동 계산]
        calc_days = (end_date - start_date).days + 1
        if calc_days < 1:
            st.error("종료일이 시작일보다 빠를 수 없습니다.")
            calc_days = 0
        st.write(f"👉 선택된 결석 일수: **{calc_days}일**")

        st.subheader("✍️ 3. 보호자 및 학생 서명")
        g_name = st.text_input("보호자 성함")
        
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("보호자 서명")
            # 배경을 투명하게 설정 (rgba(0,0,0,0))
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", 
                                 background_color="rgba(0,0,0,0)", update_streamlit=True)
        with col_sig2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", 
                                 background_color="rgba(0,0,0,0)", update_streamlit=True)

        submit = st.form_submit_button("✅ 결석신고서 PDF 생성")

        if submit:
            if not g_name:
                st.error("보호자 성함을 입력해 주세요.")
            elif calc_days == 0:
                st.error("날짜 설정을 확인해 주세요.")
            else:
                def process_sig(canvas):
                    # 서명이미지를 불러와서 투명도 유지하며 PNG로 변환
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                report_data = {
                    "dept": FIXED_DEPT, "grade": FIXED_GRADE, "cls": FIXED_CLASS, 
                    "num": num_only, "name": name_only,
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": calc_days, "g_name": g_name
                }

                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(
                    report_data, process_sig(g_canvas), process_sig(s_canvas), debug_mode=debug_mode
                )

                # 구글 시트 저장
                try:
                    existing_data = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name_only, "학년": FIXED_GRADE, "반": FIXED_CLASS, "번호": num_only,
                        "보호자": g_name, "결석기간": f"{start_date}~{end_date}", "일수": calc_days
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                except:
                    pass

                st.success(f"{name_only} 학생의 신고서 생성 완료!")

if st.session_state.pdf_data:
    st.download_button(
        label="📄 완성된 결석신고서 다운로드",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{datetime.now().strftime('%m%d')}_{name_only}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
