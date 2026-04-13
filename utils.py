import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
import io
import base64
import requests
import os
import math

# --- 동적 데이터 로드 함수 (새로 추가) ---
@st.cache_data(ttl=60)
def load_class_info(_conn):
    """구글 시트 '반정보' 탭에서 동적으로 학급 정보를 불러옵니다."""
    try:
        df = _conn.read(worksheet="반정보")
        row = df.iloc[0] # 첫 번째 행 데이터 읽기
        return {
            # 데이터 로드 시점부터 소수점 제거 방어 로직 추가
            "dept": str(row.get("학과", "미상")).replace('.0', ''),
            "grade": str(row.get("학년", "0")).replace('.0', ''),
            "cls": str(row.get("반", "0")).replace('.0', ''),
            "student_count": int(row.get("학생수", 0))
        }
    except Exception as e:
        return {"dept": "미상", "grade": "0", "cls": "0", "student_count": 0}

@st.cache_data(ttl=60)
def load_student_list(_conn, exclude_admins=True):
    """구글 시트 '학생명부' 탭에서 학생 데이터를 불러옵니다.
    exclude_admins=True일 경우 교사 및 특수 계정을 제외한 순수 학생만 반환합니다."""
    try:
        df = _conn.read(worksheet="학생명부")
        
        if exclude_admins:
            # 특수 계정 제외 필터링
            excludes = ['교사', '테스트계정', '관리자']
            df = df[~df['이름'].isin(excludes)]
            
            # 결측치 제거 및 번호순 정렬
            df['번호'] = pd.to_numeric(df['번호'], errors='coerce')
            df = df.dropna(subset=['번호'])
            df['번호'] = df['번호'].astype(int)
            df = df.sort_values(by='번호')
            
        return df
    except Exception as e:
        return pd.DataFrame()
        
# 1. 한국 시간(KST) 계산 함수
def get_kst():
    return datetime.utcnow() + timedelta(hours=9)

# 2. 디스코드 알림 전송 함수
def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            requests.post(webhook_url, json={"content": message})
    except: pass

# 3. [개선] 이미지 처리 함수 (에러 원인 ImageChops 제거)
def process_multiple_images(uploaded_files):
    if not uploaded_files:
        return [""] * 10
    
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            # 이미지 열기 및 기본 보정
            img = Image.open(file)
            img = ImageOps.exif_transpose(img)
            
            # 흑백 변환 및 대비 극대화 (스캔 효과)
            img = img.convert('L') 
            img = ImageOps.autocontrast(img, cutoff=2) # 배경 밝게, 글씨 진하게
            
            # 그림자 제거를 위한 필터 (연한 회색을 흰색으로 강제 변환)
            img = img.point(lambda p: p if p < 180 else 255)
            
            # 선명도 및 대비 2차 강화
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            
            # 해상도 최적화
            img.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50, optimize=True)
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        # 이미지들을 구분자 'NEXT'로 결합
        full_string = "NEXT".join(all_encoded)
        
        # 구글 시트 셀 제한 대응 (안전하게 44,000자씩 분할)
        chunk_size = 44000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10: chunks.append("")
        return chunks[:10]
    except Exception as e:
        # 에러 발생 시 화면에 출력하여 원인 파악
        st.error(f"⚠️ 이미지 변환 과정에서 문제가 발생했습니다: {e}")
        return [""] * 10

# 4. 단일 이미지 복구
def decode_image_safe(b64_str):
    if not b64_str or str(b64_str).lower() == 'nan' or str(b64_str).strip() == "":
        return None
    try:
        s = str(b64_str).strip()
        while s.startswith("'"): s = s[1:]
        return io.BytesIO(base64.b64decode(s))
    except: return None

# 5. 다중 이미지 복구
def decode_multiple_images_safe(chunks):
    if not chunks: return []
    try:
        combined_b64 = ""
        for c in chunks:
            if pd.isna(c) or str(c).lower() == 'nan': continue
            s = str(c).strip()
            while s.startswith("'"): s = s[1:]
            combined_b64 += s
        if not combined_b64: return []
        
        image_data_list = combined_b64.split("NEXT")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except: return []

# 6. 서명 인코딩
def process_sig(canvas_data):
    if canvas_data is None: return ""
    try:
        img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
        img.thumbnail((250, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

# 7. PDF 클래스 (동그라미 추가 버전)
class SchoolPDF(FPDF):
    def __init__(self, font_path, bold_font_path, bg_image_path):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.font_path, self.bold_font_path, self.bg_image_path = font_path, bold_font_path, bg_image_path
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list, fixed_info, is_admin=False):
        self.add_page()
        if os.path.exists(self.bg_image_path):
            self.image(self.bg_image_path, x=0, y=0, w=210, h=297)
        self.set_text_color(0, 0, 0); self.set_font('Nanum', '', 13)
        
        # 📌 [핵심 수정 부분] PDF에 글씨를 쓰기 직전에 소수점(.0)을 한 번 더 완벽하게 제거합니다.
        dept_str = str(fixed_info.get('dept', '')).replace('.0', '')
        grade_str = str(fixed_info.get('grade', '')).replace('.0', '')
        cls_str = str(fixed_info.get('cls', '')).replace('.0', '')
        num_str = str(data.get('num', '')).replace('.0', '')
        
        # 수정된 변수로 텍스트 출력
        self.text(98, 55, dept_str)
        self.text(140, 55, grade_str)
        self.text(161, 55, cls_str)
        self.text(177, 55, num_str)
        
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(46, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        
        # 결석 동그라미
        self.set_draw_color(0, 0, 0); self.set_line_width(0.5)
        self.ellipse(95, 80, 11, 7, style='D')

        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 249.5, str(data['s_m'])); self.text(118.5, 249.5, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        
        if g_sig_io: g_sig_io.seek(0); self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: s_sig_io.seek(0); self.image(s_sig_io, x=174, y=121, w=18)
        
        if is_admin:
            self.set_font('Nanum', '', 14); self.text(158, 258, "오정은")
            if os.path.exists("teacher_seal.png"):
                self.image("teacher_seal.png", x=174, y=248.5, w=18)

        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try: img_io.seek(0); self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())
