import streamlit as st
import pandas as pd
from datetime import datetime
# utils에서 필요한 모든 함수를 정확히 불러와야 합니다.
from utils import get_kst, decode_image_safe, decode_multiple_images_safe, SchoolPDF
import io
import base64

def show_page(conn, password, fixed_info, paths):
    st.title("👨‍🏫 교사용 관리")
    pw = st.text_input("비밀번호를 입력하세요", type="password")
    
    if pw == password:
        st.success("인증되었습니다.")
        try:
            # 구글 시트에서 데이터 로드
            data = conn.read(ttl=0)
            if not data.empty:
                # 제출일시 기준 내림차순 정렬
                data = data.sort_values(by='제출일시', ascending=False)
                
                for i, row in data.iterrows():
                    with st.expander(f"📌 {row['제출일시']} - {row['이름']} 학생"):
                        try:
                            # 1. 날짜 데이터 복구
                            cy = datetime.now().year
                            period_raw = str(row['결석기간']).split('(')[0].strip()
                            sd_str = period_raw.split('~')[0].strip()
                            ed_str = period_raw.split('~')[1].strip() if '~' in period_raw else sd_str
                            
                            sd = datetime.strptime(f"{cy}-{sd_str}", "%Y-%m-%d")
                            ed = datetime.strptime(f"{cy}-{ed_str}", "%Y-%m-%d")
                            
                            # 2. PDF용 데이터 정리
                            r_d = {
                                "num": int(float(row['번호'])), 
                                "name": str(row['이름']), 
                                "s_m": sd.month, "s_d": sd.day,
                                "e_m": ed.month, "e_d": ed.day,
                                "days": int(float(row['일수'])), 
                                "g_name": str(row['보호자'])
                            }
                            
                            # 3. 이미지 복구 (조각 합치기)
                            ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
                            
                            # [핵심] utils의 함수들을 사용하여 이미지/서명 복구
                            g_sig = decode_image_safe(row.get('보호자서명', ""))
                            s_sig = decode_image_safe(row.get('학생서명', ""))
                            ev_list = decode_multiple_images_safe(ev_chunks)
                            
                            # 4. PDF 생성
                            pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                            admin_pdf = pdf_gen.generate_report(r_d, g_sig, s_sig, ev_list, fixed_info)
                            
                            # 5. 다운로드 버튼
                            st.download_button(
                                label=f"📥 {row['이름']} 통합 PDF 다운로드", 
                                data=admin_pdf, 
                                file_name=f"{row['제출일시'].split(' ')[0]}_{row['이름']}_결석계.pdf", 
                                key=f"dl_{i}", 
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"변환 오류: {e}")
            else:
                st.info("현재 접수된 데이터가 없습니다.")
        except Exception as e:
            st.error(f"데이터 로드 실패: {e}")
    elif pw != "":
        st.error("비밀번호가 일치하지 않습니다.")
