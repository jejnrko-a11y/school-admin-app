import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops
import io
import base64
import requests
import os

# 1. 한국 시간(KST) 계산 함수
def get_kst():
    # 서버 시간(UTC)에 9시간을 더해 한국 시간을 반환합니다.
    return datetime.utcnow() + timedelta(hours=9)

# 2. 디스코드 알림 전송 함수
def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            data = {"content": message}
            requests.post(webhook_url, json=data)
    except:
        pass # 알림 실패가 앱 중단으로 이어지지 않게 처리

# 3. 이미지 처리 함수 (여러 장 대응 & 지능형 스캔 보정)
def process_multiple_images(uploaded_files):
    if not uploaded_files:
        return [""] * 10
    
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) # 스마트폰 사진 방향 자동 수정
            img = img.convert('L') # 흑백 변환 (용량 절감 및 스캔 효과)
            
            # --- 지능형 스캔 보정 (그림자 제거) ---
            bg = img.filter(ImageFilter.GaussianBlur(radius=50))
            img = ImageChops.divide(img, bg)
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            
            # 해상도 조절 (A4 출력에 적합한 1100px)
            img.thumbnail((1100, 1100), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=55, optimize=True)
            # 이미지간 확실한 구분자 '|' 사용
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        # 모든 이미지를 하나로 합침
        full_string = "|".join(all_encoded)
        
        # 구글 시트 5만자 제한을 피하기 위해 조각 분할 (안전하게 45,000자씩)
        chunk_size = 45000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10: chunks.append("")
        return chunks[:10] # 최대 10개 조각 반환
    except Exception as e:
        st.error(f"이미지 처리 중 오류 발생: {e}")
        return [""] * 10

# 4. 단일 이미지 복구 함수 (서명용)
def decode_image_safe(b64_str):
    if not b64_str or str(b64_str).lower() == 'nan' or str(b64_str).strip() == "":
        return None
    try:
        s = str(b64_str).strip()
        # 구글 시트 수식 방지 문자(') 제거
        while s.startswith("'"):
            s = s[1:]
        return io.BytesIO(base64.b64decode(s))
    except:
        return None

# 5. 다중 이미지 복구 함수 (증빙서류용)
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
        
        # 구분자로 다시 나눔
        image_data_list = combined_b64.split("|")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except:
        return []

# 6. 서명 데이터 처리 함수 (투명 PNG)
def process_sig(canvas_data):
    if canvas_data is None: return ""
    try:
        img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
        img.thumbnail((250, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

# 7. PDF 생성 클래스 (경기기계공고 전용)
class SchoolPDF(FPDF):
    def __init__(self, font_path, bold_font_path, bg_image_path):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.font_path = font_path
        self.bold_font_path = bold_font_path
        self.bg_image_path = bg_image_path
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list, fixed_info, is_admin=False):
        # --- 1페이지: 결석신고서 ---
        self.add_page()
        if os.path.exists(self.bg_image_path):
            self.image(self.bg_image_path, x=0, y=0, w=210, h=297)
        
        self.set_text_color(0, 0, 0)
        self.set_font('Nanum', '', 13)
        # 인적사항 기입 (정밀 좌표)
        self.text(98, 55, fixed_info['dept'])
        self.text(140, 55, str(fixed_info['grade']))
        self.text(161, 55, str(fixed_info['cls']))
        self.text(177, 55, str(data['num']))
        
        self.set_font('Nanum', '', 15)
        self.text(150, 65, data['name'])
        
        self.set_font('Nanum', '', 12)
        # 기간 정보
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d']))
        self.text(74, 85, str(data['days']))
        
        # 중간/하단 날짜 (시작일 기준)
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        
        # 이름 기입
        self.text(158, 117, data.get('g_name', '')); self.text(158, 126, data['name'])
        
        # 서명 이미지 삽입 (seek(0) 필수)
        if g_sig_io:
            g_sig_io.seek(0)
            self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io:
            s_sig_io.seek(0)
            self.image(s_sig_io, x=174, y=121, w=18)
            
        # 교사용 관리 페이지에서 생성할 때만 담임 성함 추가
        if is_admin:
            self.set_font('Nanum', '', 14)
            self.text(160, 258, "교사")

        # --- 2페이지 이후: 증빙서류 ---
        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try:
                    img_io.seek(0)
                    # 이미지를 A4에 가득 차게 배치 (좌우 여백 5mm)
                    self.image(img_io, x=5, y=5, w=200)
                except:
                    continue
                    
        return bytes(self.output())
