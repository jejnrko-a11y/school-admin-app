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
# 1. 초기 설정 및 한국 시간
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

def get_kst():
    # 서버 시간에 관계없이 한국 시간으로 계산
    return datetime.utcnow() + timedelta(hours=9)

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

# [화질 극대화 & 용량 최적화] 이미지 처리 함수
def process_image(image_data, mode="evidence"):
    if image_data is None: return ""
    try:
        if mode == "signature":
            img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
            img.thumbnail((250, 150)) 
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            return base64.b64encode(buf.getvalue()).decode()
        else:
            # --- 증빙서류 고화질 스캔 모드 ---
            img = Image.open(image_data)
            img = ImageOps.exif_transpose(img) # 방향 수정
            img = ImageOps.grayscale(img)      # 흑백 (용량 1/3 절감)
            
            # 대비 및 선명도 강화 (글자 가독성 핵심)
            img = ImageEnhance.Contrast(img).enhance(2.2) 
            img = ImageEnhance.Sharpness(img).enhance(2.0) 

            # 구글 시트 5만자 제한(약 37KB) 내에서 최대 화질 찾기
            max_chars = 49500
            quality = 70
            size = 1200 # 시작 해상도
            
            while True:
                temp_img = img.copy()
                temp_img.thumbnail((size, size), Image.LANCZOS)
                buf = io.BytesIO()
                temp_img.save(buf, format="JPEG", quality=quality, optimize=True)
                encoded = base64.b64encode(buf.getvalue()).decode()
                
                if len(encoded) < max_chars:
                    return encoded # 성공
                
                # 용량 초과 시 단계적 축소
                if quality > 30:
                    quality -= 10
                else:
                    size -= 100
                    quality = 50
                    
                if size < 300: # 최소 하한선
                    return encoded
    except Exception as e:
        return f"Error: {e}"

def decode_image(base64_string):
    if not base64_string or base64_string.startswith("Error"): return None
    try:
        return io.BytesIO(base64.b64decode(base64_string))
    except:
        return None

# ==========================================
# 2. PDF 생성 클래스 (자동 회전 대응)
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
            # 이미지가 A4에 꽉 차도록 여백 최소화 (상단 제목 삭제됨)
            self.image(evidence_img, x=5, y=5, w=200)
        return bytes(self.output())

# ==========================================
# 3. 앱 UI 및 메인 로직
# ==========================================
st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("이동", ["메인 화면", "결석계 작성", "교사용 관리"])

if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""

if menu == "메인 화면":
    st.session_state.submitted = False
    st.title("🏫 경기기계공고 행정 시스템")
    st.write(f"현재 시간(KST): {get_kst().strftime('%Y-%m-%d %H:%M')}")
    st.info("왼쪽 메뉴에서 '결석계 작성'을 선택하세요.")

elif menu == "결석계 작성":
    if st.session_state.submitted:
        st.title("✅ 제출 완료")
        st.success(f"{st.session_state.student_name} 학생의 결석계가 접수되었습니다.")
        st.download_button("📄 통합 결석계 PDF 다운로드", data=st.session_state.pdf_data, 
                           file_name=f"결석계_{st.session_state.student_name}.pdf", use_container_width=True)
        if st.button("새로 작성하기"):
            st.session_state.submitted = False
            st.rerun()
    else:
        st.title("📝 결석신고서 작성")
        c1, c2 = st.columns(2)
        start_d = c1.date_input("시작일", get_kst())
        end_d = c2.date_input("종료일", get_kst())
        calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
        st.info(f"평일 결석 일수: **{calc_days}일**")

        with st.form("absence_form"):
            sel_student = st.selectbox("학생 이름 선택", STUDENT_OPTIONS)
            reason_detail = st.text_area("상세 사유")
            proof_file = st.file_uploader("증빙서류(진단서 등) 사진 첨부", type=['jpg', 'png', 'jpeg'])
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
                    st.error("입력 정보를 확인해 주세요.")
                else:
                    name_only = sel_student.split("(")[0]
                    st.session_state.student_name = name_only
                    num_only = int(sel_student.split("(")[1].replace("번)", ""))
                    
                    # 1. 이미지 인코딩 (여기서 화질 결정됨)
                    g_b64 = process_image(g_canvas.image_data, mode="signature")
                    s_b64 = process_image(s_canvas.image_data, mode="signature")
                    proof_b64 = process_image(proof_file, mode="evidence")

                    # 2. PDF 생성
                    rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                    
                    st.session_state.pdf_data = SchoolPDF().generate_report(rep_data, decode_image(g_b64), decode_image(s_b64), decode_image(proof_b64))

                    # 3. 데이터 저장 (실패 시 원인 표시)
                    try:
                        existing = conn.read(ttl=0)
                        new_row = pd.DataFrame([{
                            "제출일시": get_kst().strftime("%Y-%m-%d %H:%M:%S"),
                            "이름": name_only, "번호": num_only, "보호자": g_name,
                            "결석기간": f"{start_d}~{end_d}", "일수": calc_days, "상세사유": reason_detail,
                            "증빙서류데이터": proof_b64, "보호자서명": g_b64, "학생서명": s_b64
                        }])
                        conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                        st.session_state.submitted = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"⚠️ 저장 실패: {e}")
                        st.info("사진 용량이 너무 클 수 있습니다. 더 밝은 곳에서 글자 위주로 찍어보세요.")

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
                        try:
                            # 원클릭 통합 PDF 다운로드
                            dt = str(row['결석기간']).split('(')[0].strip()
                            sd = datetime.strptime(dt.split('~')[0].strip(), "%Y-%m-%d")
                            ed = datetime.strptime(dt.split('~')[1].strip(), "%Y-%m-%d")
                            r_data = {"num": int(float(row['번호'])), "name": str(row['이름']), 
                                      "s_m": sd.month, "s_d": sd.day, "e_m": ed.month, "e_d": ed.day,
                                      "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                            
                            admin_pdf = SchoolPDF().generate_report(r_data, decode_image(row.get('보호자서명')), 
                                                                    decode_image(row.get('학생서명')), 
                                                                    decode_image(row.get('증빙서류데이터')))
                            
                            st.download_button(f"📥 {row['이름']} 통합 PDF 다운로드", data=admin_pdf, 
                                               file_name=f"결석계_{row['이름']}.pdf", key=f"dl_{i}", use_container_width=True)
                        except Exception as e: st.error(f"오류: {e}")
            else: st.info("데이터가 없습니다.")
        except: st.error("시트 로드 실패")
