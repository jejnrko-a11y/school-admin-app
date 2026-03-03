import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops # ImageChops 추가
import io
import base64
import requests
import os

# 1. 한국 시간(KST) 계산 함수
def get_kst():
    return datetime.utcnow() + timedelta(hours=9)

# 2. 디스코드 알림 전송 함수
def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            requests.post(webhook_url, json={"content": message})
    except:
        pass

# 3. 증빙서류 처리 (그림자 제거 및 10분할 저장)
def process_multiple_images(uploaded_files):
    if not uploaded_files:
        return [""] * 10
    
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) 
            img = img.convert('L') # 흑백
            
            # --- 지능형 스캔 보정 ---
            # 배경 조명 맵 생성으로 그림자 제거
            bg = img.filter(ImageFilter.GaussianBlur(radius=50))
            img = ImageChops.divide(img, bg) # ImageChops 에러 방지 완료
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Contrast(img).enhance(2.2) 
            img = ImageEnhance.Sharpness(img).enhance(1.5) 
            
            img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50, optimize=True)
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        full_string = "NEXT".join(all_encoded)
        chunk_size = 44000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10:
            chunks.append("")
        return chunks[:10]
    except Exception as e:
        # 에러 발생 시 사용자에게 알림
        st.error(f"이미지 변환 에러 발생: {e}")
        return [""] * 10

# 4. 단일 이미지 복구 (서명용)
def decode_image_safe(b64_str):
    if not b64_str or str(b64_str).lower() == 'nan' or str(b64_str).strip() == "":
        return None
    try:
        s = str(b64_str).strip()
        while s.startswith("'"):
            s = s[1:]
        return io.BytesIO(base64.b64decode(s))
    except:
        return None

# 5. 다중 이미지 복구 (증빙서류용)
def decode_multiple_images_safe(chunks):
    if not chunks: return []
    try:
        combined_b64 = ""
        for c in chunks:
            if pd.isna(c) or str(c).lower() == 'nan': continue
            s = str(c).strip()
            while s.startswith("'"):
                s = s[1:]
            combined_b64 += s
            
        if not combined_b64: return []
        image_data_list = combined_b64.split("NEXT")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except Exception as e:
        return []

# 6. 서명 인코딩 (투명 PNG)
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

# 7. PDF 생성 클래스 (결석 항목 동그라미 추가)
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
        # 인적사항
        self.text(98, 55, fixed_info['dept']); self.text(140, 55, str(fixed_info['grade']))
        self.text(161, 55, str(fixed_info['cls'])); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        
        self.set_font('Nanum', '', 12)
        # 기간 정보
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        
        # [추가] '결석' 글자에 동그라미 그리기
        self.set_draw_color(0, 0, 0) # 검은색 선
        self.set_line_width(0.5)
        # x=108, y=82.5 지점에 가로 10mm, 세로 7mm 타원 그리기 (결석 글자 위치)
        self.ellipse(106, 81.5, 11, 7, style='D')

        # 날짜
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 249.5, str(data['s_m'])); self.text(118.5, 249.5, str(data['s_d']))
        self.text(148, 114, data['g_name']); self.text(158, 126, data['name'])
        
        # 서명
        if g_sig_io: g_sig_io.seek(0); self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: s_sig_io.seek(0); self.image(s_sig_io, x=174, y=121, w=18)
        
        # 교사용 관리 페이지 전용 서명
        if is_admin:
            self.set_font('Nanum', '', 14)
            self.text(159, 258, "오정은") 
            seal_path = "teacher_seal.png"
            if os.path.exists(seal_path):
                self.image(seal_path, x=174, y=248.5, w=18)

        # 2페이지 이후 증빙서류
        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try: img_io.seek(0); self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())
