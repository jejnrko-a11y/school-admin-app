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
# 2. 이미지 처리 및 안전한 복구 함수 (강화됨)
# ==========================================
def process_image_advanced(image_data, mode="evidence"):
    if image_data is None: return ["", "", ""] if mode == "evidence" else ""
    try:
        if mode == "signature":
            img = Image.fromarray(image_data.astype('uint8'), 'RGBA')
            img.thumbnail((250, 150)) 
            buf = io.BytesIO()
            img.save(buf, format="PNG") 
            return base64.b64encode(buf.getvalue()).decode()
        else:
            if hasattr(image_data, 'seek'): image_data.seek(0)
            img = Image.open(image_data)
            img = ImageOps.exif_transpose(img) # 방향 자동 수정
            img = ImageOps.grayscale(img)      # 흑백 변환
            
            # 스캔 품질 극대화 (음영 제거 및 대비 강화)
            img = ImageOps.autocontrast(img, cutoff=2)
            img = img.point(lambda p: p if p < 165 else 255) # 연한 그림자 제거
            img = ImageEnhance.Contrast(img).enhance(2.5) 
            img = ImageEnhance.Sharpness(img).enhance(2.0) 
            
            # 고해상도 유지 (1500px)
            img.thumbnail((1500, 1500), Image.LANCZOS)
            
            quality = 75
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode()
            
            # 5만자 제한을 피해 3개 조각으로 분할 (총 13.5만자 확보)
            chunk_size = 45000
            chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
            
            while len(chunks) > 3:
                quality -= 10
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality)
                encoded = base64.b64encode(buf.getvalue()).decode()
                chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
            
            while len(chunks) < 3: chunks.append("")
            return chunks
    except:
        return ["", "", ""] if mode == "evidence" else ""

# [에러 해결] 시트 수식 오류 방지 및 완전 복구 함수
def decode_image_safe(chunks):
    if chunks is None: return None
    if isinstance(chunks, str): chunks = [chunks]
    
    try:
        combined_b64 = ""
        for c in chunks:
            s = str(c).strip()
            if s.lower() == 'nan' or not s: continue
            # 구글 시트 탈출 문자(') 제거
            if s.startswith("'"): s = s[1:]
            combined_b64 += s
            
        if not combined_b64: return None
        return io.BytesIO(base64.b64decode(combined_b64))
    except Exception as e:
        return None

# ==========================================
# 3. PDF 생성 클래스 (멀티페이지 로직 고정)
# ==========================================
class SchoolPDF(FPDF):
    def __init__(self):
        super().__init__(orientation='P', unit='mm', format='A4')
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io=None):
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
        
        # 서명 배치 (투명 PNG)
        if g_sig_io: self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: self.image(s_sig_io, x=174, y=121, w=18)

        # 2페이지: 증빙서류 (정상 출력 보장)
        if evidence_io is not None:
            self.add_page()
            # 포인터가 끝에 있을 수 있으므로 리셋 시도
            try: evidence_io.seek(0)
            except: pass
            self.image(evidence_io, x=5, y=5, w=200)
            
        return bytes(self.output())

# ==========================================
# 4. 앱 UI
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
            proof_file = st.file_uploader("증빙서류 사진 첨부 (JPG/PNG)", type=['jpg', 'png', 'jpeg'])
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
                        g_b64 = process_image_advanced(g_canvas.image_data, mode="signature")
                        s_b64 = process_image_advanced(s_canvas.image_data, mode="signature")
                        proof_chunks = process_image_advanced(proof_file, mode="evidence")
                        
                        # 복구
                        g_io = decode_image_safe(g_b64)
                        s_io = decode_image_safe(s_b64)
                        p_io = decode_image_safe(proof_chunks)
                        
                        # PDF 생성
                        rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                    "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                        
                        st.session_state.pdf_data = SchoolPDF().generate_report(rep_data, g_io, s_io, p_io)

                        # 구글 시트 저장 (분할 조각 저장)
                        sub_time = get_kst().strftime("%m-%d %H:%M")
                        per_str = f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}"
                        existing = conn.read(ttl=0)
                        new_row = pd.DataFrame([{
                            "결석기간": per_str, "일수": calc_days, "이름": name_only, "번호": num_only,
                            "보호자": g_name, "상세사유": reason_detail, "제출일시": sub_time,
                            "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}", 
                            "증빙_1": f"'{proof_chunks[0]}", "증빙_2": f"'{proof_chunks[1]}", "증빙_3": f"'{proof_chunks[2]}"
                        }])
                        conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                        
                        send_discord_notification(f"🔔 **[결석계 제출]** {name_only}({num_only}번) / {per_str}")
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
                            sd_part = str(row['결석기간']).split('~')[0]
                            ed_part = str(row['결석기간']).split('~')[1] if '~' in str(row['결석기간']) else sd_part
                            sd = datetime.strptime(f"{cy}-{sd_part}", "%Y-%m-%d")
                            ed = datetime.strptime(f"{cy}-{ed_part}", "%Y-%m-%d")
                            r_d = {"num": int(float(row['번호'])), "name": str(row['이름']), "s_m": sd.month, "s_d": sd.day,
                                  "e_m": ed.month, "e_d": ed.day, "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                            
                            ev_chunks = [row.get('증빙_1', ""), row.get('증빙_2', ""), row.get('증빙_3', "")]
                            
                            # 교사용 PDF 재생성
                            admin_pdf = SchoolPDF().generate_report(r_d, 
                                                                    decode_image_safe(row.get('보호자서명', "")), 
                                                                    decode_image_safe(row.get('학생서명', "")), 
                                                                    decode_image_safe(ev_chunks))
                            
                            st.download_button(f"📥 {row['이름']} 통합 PDF 다운로드", data=admin_pdf, 
                                               file_name=f"{row['이름']}_결석계.pdf", key=f"dl_{i}", use_container_width=True)
                        except Exception as e: st.error(f"변환 오류: {e}")
            else: st.info("데이터 없음")
        except: st.error("시트 로드 실패")
