import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter, ImageChops
import io
import base64
import requests
import os

# 한국 시간 계산
def get_kst():
    return datetime.utcnow() + timedelta(hours=9)

# 디스코드 알림
def send_discord_notification(message):
    try:
        if "discord" in st.secrets:
            webhook_url = st.secrets["discord"]["webhook_url"]
            requests.post(webhook_url, json={"content": message})
    except: pass

# 이미지 인코딩 (고화질 스캔 + 분할)
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
            img = ImageOps.exif_transpose(img)
            img = img.convert('L')
            bg = img.filter(ImageFilter.GaussianBlur(radius=50))
            img = ImageChops.divide(img, bg)
            img = ImageOps.autocontrast(img, cutoff=2)
            img = ImageEnhance.Contrast(img).enhance(2.5)
            img = ImageEnhance.Sharpness(img).enhance(2.0)
            img.thumbnail((1500, 1500), Image.LANCZOS)
            quality = 70
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=quality, optimize=True)
            encoded = base64.b64encode(buf.getvalue()).decode()
            chunk_size = 45000
            chunks = [encoded[i:i + chunk_size] for i in range(0, len(encoded), chunk_size)]
            while len(chunks) < 10: chunks.append("")
            return chunks[:10]
    except: return [""] * 10 if mode == "evidence" else ""

# 이미지 복구
def decode_image_safe(chunks):
    if chunks is None: return None
    if isinstance(chunks, str): chunks = [chunks]
    try:
        combined_b64 = ""
        for c in chunks:
            s = str(c).strip()
            if s.lower() == 'nan' or not s: continue
            if s.startswith("'"): s = s[1:]
            combined_b64 += s
        if not combined_b64: return None
        return io.BytesIO(base64.b64decode(combined_b64))
    except: return None

# PDF 클래스
class SchoolPDF(FPDF):
    def __init__(self, font_path, bold_font_path, bg_image_path):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.font_path = font_path
        self.bold_font_path = bold_font_path
        self.bg_image_path = bg_image_path
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list, fixed_info):
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
        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try: img_io.seek(0); self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())
