import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime, timedelta
from streamlit_drawable_canvas import st_canvas
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops
import io
import os
import base64
import requests

# ==========================================
# 1. 초기 설정 및 한국 시간
# ==========================================
st.set_page_config(page_title="경기기계공고 행정 시스템", layout="centered")

def get_kst():
    return datetime.utcnow() + timedelta(hours=9)

def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            requests.post(webhook_url, json={"content": message})
    except: pass

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
except: pass

# ==========================================
# 2. 이미지 처리 함수 (고화질 및 다중 처리)
# ==========================================
def process_multiple_images(uploaded_files):
    if not uploaded_files: return [""] * 10
    
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) 
            img = img.convert('L') # 스캔 효과를 위해 흑백
            
            # 그림자 제거 및 스캔 보정
            bg = img.filter(ImageFilter.GaussianBlur(radius=50))
            img = ImageChops.divide(img, bg)
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            
            # 해상도 최적화 (가로 1000px 내외)
            img.thumbnail((1100, 1100), Image.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=55, optimize=True)
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        # 이미지들 사이에 구분자 삽입하여 하나로 합침
        full_string = "IMAGE_SEP".join(all_encoded)
        
        # 구글 시트 셀 제한(5만자)을 피하기 위해 45,000자씩 분할
        chunk_size = 45000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        # 10개 칸을 맞추기 위해 패딩 추가
        while len(chunks) < 10: chunks.append("")
        return chunks[:10]
    except Exception as e:
        st.error(f"이미지 처리 중 오류: {e}")
        return [""] * 10

def decode_multiple_images(chunks):
    if not chunks: return []
    try:
        full_b64 = ""
        for c in chunks:
            s = str(c).strip()
            if not s or s.lower() == 'nan': continue
            # 엑셀 탈출 문자(') 제거
            if s.startswith("'"): s = s[1:]
            full_b64 += s
            
        if not full_b64: return []
        
        # 구분자로 다시 나눔
        image_data_list = full_b64.split("IMAGE_SEP")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except Exception as e:
        return []

def process_sig(canvas_data):
    if canvas_data is None: return ""
    try:
        img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
        img.thumbnail((250, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

# ==========================================
# 3. PDF 생성 클래스 (멀티 페이지 보장)
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list=None):
        # 1페이지: 신고서
        self.add_page()
        if os.path.exists(bg_image_path):
            self.image(bg_image_path, x=0, y=0, w=210, h=297)
        self.set_text_color(0, 0, 0); self.set_font('Nanum', '', 13)
        self.text(98, 55, FIXED_DEPT); self.text(140, 55, str(FIXED_GRADE))
        self.text(161, 55, str(FIXED_CLASS)); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        
        # 서명 이미지
        if g_sig_io: 
            g_sig_io.seek(0)
            self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: 
            s_sig_io.seek(0)
            self.image(s_sig_io, x=174, y=121, w=18)

        # 2페이지 이후: 증빙 서류들
        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try:
                    img_io.seek(0)
                    self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())

# ==========================================
# 4. 앱 화면 및 로직
# ==========================================
st.sidebar.title("🏫 행정 메뉴")
menu = st.sidebar.radio("이동", ["메인 화면", "결석계 작성", "교사용 관리"])

if 'submitted' not in st.session_state: st.session_state.submitted = False
if 'pdf_data' not in st.session_state: st.session_state.pdf_data = None
if 'student_name' not in st.session_state: st.session_state.student_name = ""

if menu == "메인 화면":
    st.session_state.submitted = False
    st.title("🏫 경기기계공고 행정 시스템")
    st.write(f"현재 한국 시간: {get_kst().strftime('%m-%d %H:%M')}")

elif menu == "결석계 작성":
    if st.session_state.submitted:
        st.title("✅ 제출 완료")
        st.success(f"{st.session_state.student_name} 학생의 서류가 제출되었습니다.")
        st.download_button("📄 통합 결석계 PDF 다운로드", data=st.session_state.pdf_data, 
                           file_name=f"결석계_{st.session_state.student_name}.pdf", use_container_width=True)
        if st.button("새로 작성하기"):
            st.session_state.submitted = False
            st.rerun()
    else:
        st.title("📝 결석신고서 작성")
        c1, c2 = st.columns(2)
        start_d = c1.date_input("시작일")
        end_d = c2.date_input("종료일")
        calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
        st.info(f"평일 결석 일수: **{calc_days}일**")

        with st.form("absence_form"):
            sel_student = st.selectbox("학생 이름 선택", STUDENT_OPTIONS)
            reason_detail = st.text_area("상세 사유")
            proof_files = st.file_uploader("증빙서류 사진 첨부 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
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
                    try:
                        name_only = sel_student.split("(")[0]
                        num_only = int(sel_student.split("(")[1].replace("번)", ""))
                        st.session_state.student_name = name_only
                        
                        # 인코딩
                        g_b64 = process_sig(g_canvas.image_data)
                        s_b64 = process_sig(s_canvas.image_data)
                        proof_chunks = process_multiple_images(proof_files)
                        
                        # PDF 생성 (즉시 복구 테스트)
                        evidence_ios = decode_multiple_images(proof_chunks)
                        rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                    "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                        
                        st.session_state.pdf_data = SchoolPDF().generate_report(
                            rep_data, io.BytesIO(base64.b64decode(g_b64)), io.BytesIO(base64.b64decode(s_b64)), evidence_ios
                        )

                        # 구글 시트 저장
                        existing = conn.read(ttl=0)
                        data_to_save = {
                            "결석기간": f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}", 
                            "일수": calc_days, "이름": name_only, "번호": num_only,
                            "보호자": g_name, "상세사유": reason_detail, 
                            "제출일시": get_kst().strftime("%m-%d %H:%M"),
                            "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}"
                        }
                        for idx, chunk in enumerate(proof_chunks):
                            data_to_save[f"증빙_{idx+1}"] = f"'{chunk}"
                            
                        conn.update(data=pd.concat([existing, pd.DataFrame([data_to_save])], ignore_index=True))
                        send_discord_notification(f"🔔 [결석계 제출] {name_only}({num_only}번) / {calc_days}일")
                        st.session_state.submitted = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"처리 실패: {e}")

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
                            cy = get_kst().year
                            sd_str = str(row['결석기간']).split('~')[0]
                            ed_str = str(row['결석기간']).split('~')[1] if '~' in str(row['결석기간']) else sd_str
                            sd = datetime.strptime(f"{cy}-{sd_str}", "%Y-%m-%d")
                            ed = datetime.strptime(f"{cy}-{ed_str}", "%Y-%m-%d")
                            r_d = {"num": int(float(row['번호'])), "name": str(row['이름']), "s_m": sd.month, "s_d": sd.day,
                                  "e_m": ed.month, "e_d": ed.day, "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                            
                            # 10개 조각 합치기
                            ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
                            
                            admin_pdf = SchoolPDF().generate_report(
                                r_d, 
                                io.BytesIO(base64.b64decode(str(row.get('보호자서명', ""))[1:])), 
                                io.BytesIO(base64.b64decode(str(row.get('학생서명', ""))[1:])), 
                                decode_multiple_images(ev_chunks)
                            )
                            
                            st.download_button(f"📥 {row['이름']} 통합 PDF 다운로드", data=admin_pdf, 
                                               file_name=f"{row['이름']}_결석계.pdf", key=f"dl_{i}", use_container_width=True)
                        except Exception as e: st.error(f"변환 오류: {e}")
            else: st.info("데이터 없음")
        except: st.error("시트 로드 실패")
