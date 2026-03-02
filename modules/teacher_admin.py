import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst, decode_image_safe, decode_multiple_images_safe, SchoolPDF
import io
import base64

def show_page(conn, password, fixed_info, paths):
    st.title("👨‍🏫 교사용 관리")
    pw = st.text_input("관리자 비밀번호를 입력하세요", type="password")
    
    if pw == password:
        st.success("인증되었습니다.")
        try:
            data = conn.read(ttl=0)
            if not data.empty:
                data = data.sort_values(by='제출일시', ascending=False)
                for i, row in data.iterrows():
                    with st.expander(f"📌 {row['제출일시']} - {row['이름']} 학생"):
                        try:
                            cy = datetime.now().year
                            period_raw = str(row['결석기간']).split('(')[0].strip()
                            sd_str = period_raw.split('~')[0].strip()
                            ed_str = period_raw.split('~')[1].strip() if '~' in period_raw else sd_str
                            sd = datetime.strptime(f"{cy}-{sd_str}", "%Y-%m-%d")
                            ed = datetime.strptime(f"{cy}-{ed_str}", "%Y-%m-%d")
                            
                            r_d = {"num": int(float(row['번호'])), "name": str(row['이름']), "s_m": sd.month, "s_d": sd.day,
                                  "e_m": ed.month, "e_d": ed.day, "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                            
                            # 증빙 조각 리스트
                            ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
                            
                            pdf_bytes = SchoolPDF(paths['font'], paths['bold_font'], paths['bg']).generate_report(
                                r_d, decode_image_safe(row.get('보호자서명', "")), decode_image_safe(row.get('학생서명', "")), 
                                decode_multiple_images_safe(ev_chunks), fixed_info
                            )
                            
                            st.download_button(f"📥 {row['이름']} 통합 PDF 다운로드", data=pdf_bytes, 
                                               file_name=f"{row['이름']}_결석계.pdf", key=f"dl_{i}", use_container_width=True)
                        except Exception as e: st.error(f"변환 오류: {e}")
            else: st.info("데이터 없음")
        except Exception as e: st.error(f"시트 로드 실패: {e}")
