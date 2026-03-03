import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from fpdf import FPDF
from PIL import Image, ImageOps, ImageEnhance, ImageFilter
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

# 3. 증빙서류 처리 (여러 장 대응 & 지능형 스캔 & 10분할)
def process_multiple_images(uploaded_files):
    if not uploaded_files:
        return [""] * 10
    
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0) # 파일 읽기 위치 초기화
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) # 사진 방향 자동 보정
            img = img.convert('L') # 흑백 변환
            
            # --- 지능형 스캔 보정 (에러 없는 버전) ---
            # 1. 자동 대비 조정 (어두운 곳과 밝은 곳의 차이를 키움)
            img = ImageOps.autocontrast(img, cutoff=2)
            
            # 2. 그림자 제거 (밝은 회색 영역을 강제로 흰색으로 밀어냄)
            img = img.point(lambda p: p if p < 175 else 255)
            
            # 3. 글자 선명도 및 대비 강화
            img = ImageEnhance.Contrast(img).enhance(2.2) 
            img = ImageEnhance.Sharpness(img).enhance(1.5) 
            
            # 해상도 조절 (가로 1000px)
            img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=50, optimize=True)
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        # 이미지들을 구분자 'NEXT'로 결합
        full_string = "NEXT".join(all_encoded)
        
        # 구글 시트 셀 제한(5만자) 대응 분할 (안전하게 44,000자씩)
        chunk_size = 44000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10:
            chunks.append("")
        return chunks[:10]
    except Exception as e:
        st.error(f"이미지 변환 에러: {e}")
        return [""] * 10

# 4. 단일 이미지 복구 (서명용)
def decode_image_safe(b64_str):
    if not b64_str or str(b64_str).lower() == 'nan' or str(b64_str).strip() == "":
        return None
    try:
        s = str(b64_str).strip()
        while s.startswith("'"): # 구글 시트 수식 방지 문자 제거
            s = s[1:]
        return io.BytesIO(base64.b64decode(s))
    except:
        return None

# 5. 다중 이미지 복구 (증빙서류용 - 2페이지 이후 문제 해결)
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
        
        # 구분자로 다시 나눔
        image_data_list = combined_b64.split("NEXT")
        return [io.BytesIO(base64.b64decode(data)) for data in image_data_list if data]
    except Exception as e:
        return []

# 6. 서명 인코딩 (투명 PNG 유지)
def process_sig(canvas_data):
    if canvas_data is None: return ""
    try:
        img = Image.fromarray(canvas_data.astype('uint8'), 'RGBA')
        img.thumbnail((250, 150))
        buf = io.BytesIO()
        img.save(buf, format="PNG") # PNG 포맷으로 투명도 유지
        return base64.b64encode(buf.getvalue()).decode()
    except:
        return ""

# 7. PDF 생성 클래스 (멀티페이지 대응)
class SchoolPDF(FPDF):
    def __init__(self, font_path, bold_font_path, bg_image_path):
        super().__init__(orientation='P', unit='mm', format='A4')
        self.font_path, self.bold_font_path, self.bg_image_path = font_path, bold_font_path, bg_image_path
        if os.path.exists(font_path):
            self.add_font('Nanum', '', font_path)
            self.add_font('NanumB', '', bold_font_path)

    def generate_report(self, data, g_sig_io, s_sig_io, evidence_io_list, fixed_info, is_admin=False):
        # 1페이지: 결석신고서
        self.add_page()
        if os.path.exists(self.bg_image_path):
            self.image(self.bg_image_path, x=0, y=0, w=210, h=297)
        
        self.set_text_color(0, 0, 0); self.set_font('Nanum', '', 13)
        # 인적사항 기입 (기존 좌표 유지)
        self.text(98, 55, fixed_info['dept']); self.text(140, 55, str(fixed_info['grade']))
        self.text(161, 55, str(fixed_info['cls'])); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(46, 85, str(data['e_d'])); self.text(73, 85, str(data['days']))
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 250, str(data['s_m'])); self.text(118.5, 250, str(data['s_d']))
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        
        # 서명 배치 (seek(0) 필수)
        if g_sig_io: g_sig_io.seek(0); self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: s_sig_io.seek(0); self.image(s_sig_io, x=174, y=121, w=18)
        
        if is_admin:
            self.set_font('Nanum', '', 14)
            # [수정 완료] "교사" -> "오정은" / X좌표를 160에서 159로 살짝 조정 (세 글자라 왼쪽으로 이동)
            self.text(159, 258, "오정은") 

        # 2페이지 이후: 증빙서류들
        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try:
                    img_io.seek(0)
                    self.image(img_io, x=5, y=5, w=200)
                except:
                    continue
        return bytes(self.output())
