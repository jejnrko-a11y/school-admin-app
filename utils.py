# ... (상단 import 동일)

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
        self.text(98, 55, fixed_info['dept']); self.text(140, 55, str(fixed_info['grade']))
        self.text(161, 55, str(fixed_info['cls'])); self.text(177, 55, str(data['num']))
        self.set_font('Nanum', '', 15); self.text(150, 65, data['name'])
        self.set_font('Nanum', '', 12)
        self.text(146, 77, str(data['s_m'])); self.text(163, 77, str(data['s_d']))
        self.text(28, 85, str(data['e_m'])); self.text(47, 85, str(data['e_d'])); self.text(74, 85, str(data['days']))
        
        # 날짜 (시작일 기준)
        self.text(104.5, 105, str(data['s_m'])); self.text(117.8, 105, str(data['s_d']))
        self.text(105.5, 248, str(data['s_m'])); self.text(118.5, 248, str(data['s_d']))
        
        # 이름 기입
        self.text(158, 117, data['g_name']); self.text(158, 126, data['name'])
        
        # 서명 이미지 복구 (seek(0) 필수)
        if g_sig_io: 
            g_sig_io.seek(0); self.image(g_sig_io, x=174, y=111, w=18)
        if s_sig_io: 
            s_sig_io.seek(0); self.image(s_sig_io, x=174, y=121, w=18)

        # [추가] 교사용일 경우 담임 선생님 성함 기입
        if is_admin:
            self.set_font('Nanum', '', 14)
            self.text(160, 258, "선생님") # 담임 성함 위치

        if evidence_io_list:
            for img_io in evidence_io_list:
                self.add_page()
                try: img_io.seek(0); self.image(img_io, x=5, y=5, w=200)
                except: continue
        return bytes(self.output())

# ... (나머지 decode, process 함수들은 이전 버전 유지)
