import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst, decode_image_safe, decode_multiple_images_safe, SchoolPDF
import io
import base64

def show_page(conn, password, fixed_info, paths):
    st.title("👨‍🏫 교사용 관리")
    st.info("학생들이 제출한 모든 결석계와 증빙서류를 확인하고 통합 PDF를 생성합니다.")

    try:
        # [복구] 결석명부 시트에서 데이터 읽기
        data = conn.read(worksheet="결석명부", ttl=0)
        
        if not data.empty:
            data = data.sort_values(by='제출일시', ascending=False)
            for i, row in data.iterrows():
                with st.expander(f"📌 {row['제출일시']} - {row['이름']} 학생"):
                    try:
                        cy = datetime.now().year
                        sd_str = str(row['결석기간']).split('~')[0]
                        ed_str = str(row['결석기간']).split('~')[1] if '~' in str(row['결석기간']) else sd_str
                        sd = datetime.strptime(f"{cy}-{sd_str}", "%Y-%m-%d")
                        ed = datetime.strptime(f"{cy}-{ed_str}", "%Y-%m-%d")
                        
                        r_d = {"num": int(float(row['번호'])), "name": str(row['이름']), "s_m": sd.month, "s_d": sd.day,
                                "e_m": ed.month, "e_d": ed.day, "days": int(float(row['일수'])), "g_name": str(row['보호자'])}
                        
                        ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
                        
                        # PDF 생성 버튼과 다운로드를 하나로 통합
                        admin_pdf = SchoolPDF(paths['font'], paths['bold_font'], paths['bg']).generate_report(
                            r_d, 
                            decode_image_safe(row.get('보호자서명', "")), 
                            decode_image_safe(row.get('학생서명', "")), 
                            decode_multiple_images_safe(ev_chunks),
                            fixed_info,
                            is_admin=True # 선생님 확인용 표시
                        )
                        
                        st.download_button(
                            label=f"📥 {row['이름']} 통합 PDF 다운로드", 
                            data=admin_pdf, 
                            file_name=f"{row['이름']}_결석계.pdf", 
                            key=f"dl_{i}", 
                            use_container_width=True
                        )
                    except Exception as e:
                        st.error(f"데이터 변환 오류: {e}")
        else:
            st.info("제출된 결석계가 없습니다.")
    except Exception as e:
        st.error(f"시트 로드 실패: {e}")
