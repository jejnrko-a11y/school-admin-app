import streamlit as st
import pandas as pd
from datetime import datetime
import io
import zipfile
from utils import get_kst, decode_image_safe, decode_multiple_images_safe, SchoolPDF

def show_page(conn, password, fixed_info, paths):
    st.title("👨‍🏫 교사용 행정 관리")
    st.info("학생들이 제출한 결석계를 월별로 확인하고, 한 달 치 서류를 ZIP 파일로 일괄 다운로드할 수 있습니다.")

    try:
        # 1. 데이터 로드 및 전처리
        data = conn.read(worksheet="결석명부", ttl=0)
        
        if data.empty:
            st.warning("제출된 결석계가 없습니다.")
            return

        # '결석기간'에서 월(Month) 정보를 추출하여 임시 컬럼 생성 (정렬 및 필터링용)
        # 데이터 포맷: MM-DD~MM-DD 또는 MM-DD
        def get_month(period):
            try:
                return int(str(period).split('-')[0])
            except:
                return 0

        data['월'] = data['결석기간'].apply(get_month)
        
        # 2. 월별 탭 구성 (3월 ~ 12월)
        months = [f"{m}월" for m in range(3, 13)]
        tabs = st.tabs(months)

        for i, tab in enumerate(tabs):
            current_month = i + 3 # 3월부터 시작
            with tab:
                # 해당 월 데이터 필터링
                month_data = data[data['월'] == current_month].copy()
                
                if month_data.empty:
                    st.write(f"📅 {current_month}월에 제출된 서류가 없습니다.")
                    continue

                # --- 월별 ZIP 일괄 다운로드 기능 ---
                st.subheader(f"📦 {current_month}월 서류 꾸러미")
                
                if st.button(f"📥 {current_month}월 결석계 전체 다운로드 (ZIP)", key=f"zip_{current_month}"):
                    zip_buffer = io.BytesIO()
                    
                    with st.spinner(f"{current_month}월 서류 압축 중..."):
                        with zipfile.ZipFile(zip_buffer, "a", zipfile.ZIP_DEFLATED, False) as zip_file:
                            for idx, row in month_data.iterrows():
                                try:
                                    # PDF 생성 로직 (기존 SchoolPDF 활용)
                                    pdf_bytes = generate_student_pdf(row, fixed_info, paths)
                                    
                                    # 파일명 포맷팅: {월일}_{번호}_{이름}_결석계.pdf
                                    # 기간의 시작일 추출 (예: 03-05~03-07 -> 0305)
                                    date_prefix = str(row['결석기간']).split('~')[0].replace('-', '')
                                    student_num = int(float(row['번호']))
                                    filename = f"{date_prefix}_{student_num:02d}번_{row['이름']}_결석계.pdf"
                                    
                                    # ZIP 파일에 추가
                                    zip_file.writestr(filename, pdf_bytes)
                                except Exception as e:
                                    st.error(f"{row['이름']} 학생 서류 생성 실패: {e}")
                        
                        st.download_button(
                            label=f"💾 {current_month}월 ZIP 파일 받기",
                            data=zip_buffer.getvalue(),
                            file_name=f"{current_month}월_결석계_일괄출력.zip",
                            mime="application/zip",
                            use_container_width=True
                        )
                
                st.divider()

                # --- 개별 학생 리스트 출력 (기존 기능) ---
                st.subheader("👤 학생별 개별 확인")
                month_data = month_data.sort_values(by='제출일시', ascending=False)
                
                for idx, row in month_data.iterrows():
                    with st.expander(f"📌 {row['제출일시']} - {row['이름']} ({row['결석기간']})"):
                        try:
                            individual_pdf = generate_student_pdf(row, fixed_info, paths)
                            st.download_button(
                                label=f"📥 {row['이름']} PDF 다운로드", 
                                data=individual_pdf, 
                                file_name=f"{row['이름']}_결석계.pdf", 
                                key=f"dl_{current_month}_{idx}", 
                                use_container_width=True
                            )
                        except Exception as e:
                            st.error(f"데이터 변환 오류: {e}")

    except Exception as e:
        st.error(f"시트 로드 실패: {e}")

# 학생 개별 PDF 생성을 위한 헬퍼 함수
def generate_student_pdf(row, fixed_info, paths):
    cy = datetime.now().year
    # 결석기간 파싱
    period_str = str(row['결석기간'])
    sd_str = period_str.split('~')[0]
    ed_str = period_str.split('~')[1] if '~' in period_str else sd_str
    
    sd = datetime.strptime(f"{cy}-{sd_str}", "%Y-%m-%d")
    ed = datetime.strptime(f"{cy}-{ed_str}", "%Y-%m-%d")
    
    r_d = {
        "num": int(float(row['번호'])), 
        "name": str(row['이름']), 
        "s_m": sd.month, "s_d": sd.day,
        "e_m": ed.month, "e_d": ed.day, 
        "days": int(float(row['일수'])), 
        "g_name": str(row['보호자'])
    }
    
    ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
    
    return SchoolPDF(paths['font'], paths['bold_font'], paths['bg']).generate_report(
        r_d, 
        decode_image_safe(row.get('보호자서명', "")), 
        decode_image_safe(row.get('학생서명', "")), 
        decode_multiple_images_safe(ev_chunks),
        fixed_info,
        is_admin=True # 선생님 확인용 (직인 표시 등)
    )
