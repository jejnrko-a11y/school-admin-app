import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops
import io
import base64
import requests
import os

def get_kst():
    return datetime.utcnow() + timedelta(hours=9)

def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            requests.post(webhook_url, json={"content": message})
    except: pass

# 여러 장의 이미지를 처리하여 10개의 조각으로 분할
def process_multiple_images(uploaded_files):
    if not uploaded_files: return [""] * 10
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) 
            img = img.convert('L') # 흑백
            
            # 그림자 제거 및 스캔 보정
            bg = img.filter(ImageFilter.GaussianBlur(radius=50))
            img = ImageChops.divide(img, bg)
            img = ImageOps.autocontrast(img, cutoff=1)
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img.thumbnail((1100, 1100), Image.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=55, optimize=True)
            # 이미지간 확실한 구분자 사용
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        # 이미지들을 구분자 'NEXTIMG'로 연결
        full_string = "NEXTIMG".join(all_encoded)
        
        # 45,000자씩 분할 (구글 시트 5만자 제한 안전선)
        chunk_size = 45000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10: chunks.append("")
        return chunks[:10]
    except Exception as e:
        return [""] * 10

# [단일 이미지 복구] 서명용
def decode_image_safe(b64_str):
    if not b64_str or str(b64_str).lower() == 'nan': return None
    try:
        s = str(b64_str).strip()
        while s.startswith("'"): s = s[1:] # 모든 홑따옴표 제거
        return io.BytesIO(base64.b64decode(s))
    except: return None

# [다중 이미지 복구] 증빙서류용 - 2페이지 이후 안나오는 문제 해결 핵심
def decode_multiple_images_safe(chunks):
    if not chunks: return []
    try:
        combined_b64 = ""
        for c in chunks:
            if pd.isna(c) or c is None: continue
            s = str(c).strip()
            # [중요] 각 조각마다 붙어있는 홑따옴표를 모두 제거하고 합쳐야 함
            while s.startswith("'"): s = s[1:]
            combined_b64 += s
            
        if not combined_b64: return []
        
        # 구분자로 다시 나눔
        image_data_list = combined_b64.split("NEXTIMG")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except Exception as e:
        return []

# 서명 전용 인코딩
def process_sig(canvas_data):
    if canvas_data is None: return ""
    try:
        img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
        img.thumbnail((250, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode()
    except: return ""

class SchoolPDF(FPDF):
    def __init__(self, font_path, bold_font_path, bg_image_path):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.font_path, self.bold_font_path, self.bg_image_path = font_path, bold_font_path, bg_image_path
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list, fixed_info):
        # 1페이지
        self.add_page()
        if os.path.exists(self.bg_image_path):
            self.image(self.bg_image_path, x=0, y=0, w=210, h=297)
        self.set_text_color(0, 0, 0); self.set_font('Nanum', '', 13)
        self.text(98, 55, fixed_info['dept']); self.text(140, 55, str(fixed_info['grade']))
        self.text(161, 55, str(fixed_info['cls'])); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        
        if g_sig_io: g_sig_io.seek(0); self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: s_sig_io.seek(0); self.image(s_sig_io, x=174, y=121, w=18)

        # 2페이지 이후 (리스트가 비어있지 않은지 확인 후 루프)
        if evidence_io_list and len(evidence_io_list) > 0:
            for img_io in evidence_io_list:
                self.add_page()
                try:
                    img_io.seek(0)
                    self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())
