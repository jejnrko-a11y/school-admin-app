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
# 1. 초기 설정 및 환경 확인
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 자동화", layout="centered")

# 파일 경로 설정 (GitHub 업로드 파일명과 일치해야 함)
font_path = "NanumGothic-Regular.ttf"
bold_font_path = "NanumGothic-Bold.ttf"
bg_image_path = "background.png"

# 구글 시트 연결
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.sidebar.error("구글 시트 Secrets 설정이 필요합니다.")

# ==========================================
# 2. PDF 생성 클래스 (좌표 가이드 기능 포함)
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)
        else:
            st.error("폰트 파일을 찾을 수 없습니다. GitHub 업로드 상태를 확인하세요.")

    def draw_grid(self):
        """좌표 조정을 위한 10mm 격자 그리기"""
        self.set_stroke_color(255, 0, 0) # 빨간색 선
        self.set_text_color(255, 0, 0)
        self.set_font('Arial', '', 8)
        # 세로선 (X축)
        for x in range(0, 211, 10):
            self.line(x, 0, x, 297)
            self.text(x + 1, 5, str(x))
        # 가로선 (Y축)
        for y in range(0, 298, 10):
            self.line(0, y, 210, y)
            self.text(1, y - 1, str(y))
        self.set_text_color(0, 0, 0) # 색상 초기화

    def generate_report(self, data, g_sig, s_sig, debug_mode=False):
        self.add_page()
        
        # 배경 이미지 삽입
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)
        
        # 디버그 모드일 때 격자 그리기
        if debug_mode:
            self.draw_grid()

        self.set_font('Nanum', '', 13)

        # --- [항목별 좌표 설정] ---
        # 1. 인적사항 (학과, 학년, 반, 번호)
        self.text(68, 48, data['dept'])      
        self.text(125, 48, str(data['grade'])) 
        self.text(147, 48, str(data['cls']))   
        self.text(169, 48, str(data['num']))   
        
        # 2. 성명
        self.set_font('Nanum', '', 15)
        self.text(138, 59, data['name'])
        
        # 3. 결석 날짜 (시작/종료)
        self.set_font('Nanum', '', 12)
        self.text(148, 77, str(data['s_m'])) 
        self.text(168, 77, str(data['s_d'])) 
        self.text(32, 88, str(data['e_m']))  
        self.text(53, 88, str(data['e_d']))  
        self.text(77, 88, str(data['days'])) 
        
        # 4. 중간 제출 날짜
        today = datetime.now()
        self.text(82, 120, str(today.year))
        self.text(108, 120, str(today.month))
        self.text(126, 120, str(today.day))

        # 5. 보호자 성함 및 서명
        self.text(118, 138, data['g_name']) 
        if g_sig:
            self.image(g_sig, x=168, y=129, w=22) 
            
        # 6. 학생 성함 및 서명
        self.text(138, 153, data['name'])   
        if s_sig:
            self.image(s_sig, x=168, y=144, w=22)

        # 7. 맨 아래 하단 날짜
        self.text(100, 246, str(today.year))
        self.text(128, 246, str(today.month))
        self.text(145, 246, str(today.day))

        return bytes(self.output())

# ==========================================
# 3. 앱 UI 인터페이스
# ==========================================
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'menu' not in st.session_state: st.session_state.menu = "메인 화면"

st.title("🏫 경기기계공고 행정 시스템")

# [개발자용] 좌표 확인 체크박스
debug_mode = st.checkbox("🔍 좌표 가이드(격자) 보기 (개발자 조정용)")

# 메뉴 선택 로직
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

    with st.form("absence_form", clear_on_submit=False):
        st.subheader("📍 1. 인적사항")
        dept = st.text_input("학과", value="컴퓨터전자과")
        c1, c2, c3 = st.columns(3)
        grade = c1.selectbox("학년", [1, 2, 3], index=2)
        cls = c2.number_input("반", 1, 15, 2)
        num = c3.number_input("번호", 1, 40, 1)
        name = st.text_input("학생 성명")

        st.subheader("📅 2. 결석 날짜")
        d1, d2 = st.columns(2)
        start_date = d1.date_input("결석 시작일")
        end_date = d2.date_input("결석 종료일")
        days = st.number_input("총 결석 일수", 1, 30, 1)

        st.subheader("✍️ 3. 보호자 및 학생 서명")
        g_name = st.text_input("보호자 성함")
        
        col_sig1, col_sig2 = st.columns(2)
        with col_sig1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=2, key="g_sig", background_color="#f8f9fa")
        with col_sig2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=2, key="s_sig", background_color="#f8f9fa")

        submit = st.form_submit_button("✅ 결석신고서 PDF 생성 및 저장")

        if submit:
            if not name or not g_name:
                st.error("이름과 보호자 성함을 반드시 입력해 주세요.")
            else:
                # 1. 서명 이미지 처리 함수
                def process_sig(canvas):
                    img = Image.fromarray(canvas.image_data.astype('uint8'), 'RGBA')
                    buf = io.BytesIO()
                    img.save(buf, format="PNG")
                    return buf

                # 2. 데이터 정리
                report_data = {
                    "dept": dept, "grade": grade, "cls": cls, "num": num, "name": name,
                    "s_m": start_date.month, "s_d": start_date.day,
                    "e_m": end_date.month, "e_d": end_date.day,
                    "days": days, "g_name": g_name
                }

                # 3. PDF 생성
                pdf_gen = SchoolPDF()
                st.session_state.pdf_data = pdf_gen.generate_report(
                    report_data, process_sig(g_canvas), process_sig(s_canvas), debug_mode=debug_mode
                )

                # 4. 구글 시트 저장 (Secrets 설정이 되어 있을 때만 작동)
                try:
                    existing_data = conn.read(ttl=0)
                    new_row = pd.DataFrame([{
                        "제출일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "이름": name, "학년": grade, "반": cls, "번호": num,
                        "보호자": g_name, "결석기간": f"{start_date}~{end_date}"
                    }])
                    updated_df = pd.concat([existing_data, new_row], ignore_index=True)
                    conn.update(data=updated_df)
                    st.success("데이터가 구글 시트에 안전하게 기록되었습니다.")
                except:
                    st.warning("구글 시트 저장에 실패했습니다. (Secrets 설정을 확인하세요)")

                st.success("PDF 파일이 생성되었습니다. 아래 버튼을 눌러 다운로드하세요.")

# 폼 외부 다운로드 버튼 (Streamlit 규칙 준수)
if st.session_state.pdf_data:
    st.markdown("---")
    st.download_button(
        label="📄 완성된 결석신고서 다운로드 (클릭)",
        data=st.session_state.pdf_data,
        file_name=f"결석신고서_{datetime.now().strftime('%m%d')}_{name}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    st.balloons()
