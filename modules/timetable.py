import streamlit as st
import pandas as pd
from utils import get_kst

def show_page(conn):
    st.title("📅 학급 시간표")
    st.write("3학년 2반(컴퓨터전자과) 시간표입니다.")

    try:
        # 1. 구글 시트에서 시간표 읽기
        df = conn.read(worksheet="시간표", ttl=60) 
        
        if df.empty:
            st.warning("시간표 데이터가 없습니다. 구글 시트를 확인해 주세요.")
            return

        # 2. 데이터 전처리: nan을 빈칸으로 변경
        df = df.fillna('')

        # 3. 오늘 요일 파악
        now = get_kst()
        weekday = now.weekday()
        days_kor = ["월", "화", "수", "목", "금", "토", "일"]
        today_name = days_kor[weekday]

        # 4. 강제 중앙 정렬 및 인덱스 숨기기를 위한 CSS
        # st.table의 기본 스타일을 덮어씌웁니다.
        st.markdown("""
            <style>
            .styled-table {
                width: 100%;
                border-collapse: collapse;
                text-align: center;
            }
            .styled-table th {
                background-color: #1E3A8A !important;
                color: white !important;
                text-align: center !important;
                padding: 12px !important;
            }
            .styled-table td {
                text-align: center !important;
                padding: 10px !important;
                border: 1px solid #dee2e6 !important;
            }
            /* 오늘 요일 강조색 */
            .today-highlight {
                background-color: #EBF5FF !important;
                font-weight: bold !important;
            }
            </style>
        """, unsafe_allow_html=True)

        # 5. 오늘 요일 하이라이트 함수
        def apply_styles(row):
            styles = ['' * len(row)]
            # 로직은 아래 HTML 생성 시 처리
            return styles

        # 6. HTML 테이블 직접 생성 (가장 확실한 중앙 정렬 및 인덱스 제거 방법)
        html = '<table class="styled-table"><thead><tr>'
        
        # 헤더 생성
        for col in df.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'

        # 본문 생성
        for _, row in df.iterrows():
            html += '<tr>'
            for col_name, value in row.items():
                # 오늘 요일인 칸에만 하이라이트 클래스 추가
                highlight_class = 'today-highlight' if col_name == today_name else ''
                html += f'<td class="{highlight_class}">{value}</td>'
            html += '</tr>'
        html += '</tbody></table>'

        # 7. 요일 안내 메시지
        if weekday < 5:
            st.success(f"오늘은 **{today_name}요일**입니다.")
        else:
            st.info("주말입니다. 다음 주 시간표를 미리 확인하세요.")

        # 8. 최종 결과물 출력
        st.markdown(html, unsafe_allow_html=True)
        
        st.caption("\n※ 시간표는 학교 사정에 따라 변경될 수 있습니다.")

    except Exception as e:
        st.error(f"시간표 로드 오류: {e}")
