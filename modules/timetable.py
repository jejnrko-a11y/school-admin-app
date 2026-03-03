import streamlit as st
import pandas as pd
from utils import get_kst

def show_page(conn):
    st.title("📅 학급 시간표")
    st.markdown("### 3학년 2반 (컴퓨터전자과)")

    try:
        # 1. 구글 시트에서 시간표 읽기
        df = conn.read(worksheet="시간표", ttl=60) 
        
        if df.empty:
            st.warning("시간표 데이터가 없습니다. 구글 시트를 확인해 주세요.")
            return

        # 2. 데이터 전처리
        df = df.fillna('')
        
        # 주간 시간표 본체 (교시 ~ 금요일까지만 선택)
        timetable_main = df[['교시', '월', '화', '수', '목', '금']]
        
        # 과목 상세 정보 (과목, 담당교사 컬럼만 추출하여 중복 제거)
        subject_info = df[['과목', '담당교사']]
        subject_info = subject_info[subject_info['과목'] != ''].drop_duplicates()

        # 3. 오늘 요일 파악
        now = get_kst()
        weekday = now.weekday()
        days_kor = ["월", "화", "수", "목", "금", "토", "일"]
        today_name = days_kor[weekday]

        # 4. 스타일 정의 (중앙 정렬 및 디자인)
        st.markdown("""
            <style>
            .timetable-container {
                margin-top: 10px;
                margin-bottom: 30px;
            }
            .styled-table {
                width: 100%;
                border-collapse: collapse;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .styled-table th {
                background-color: #1E3A8A !important;
                color: white !important;
                text-align: center !important;
                padding: 12px !important;
                font-weight: bold;
            }
            .styled-table td {
                text-align: center !important;
                padding: 12px !important;
                border: 1px solid #f3f4f6 !important;
                font-size: 15px;
            }
            .today-highlight {
                background-color: #DBEAFE !important;
                font-weight: bold !important;
                color: #1E40AF !important;
            }
            .arrow-style {
                color: #9CA3AF;
                font-size: 18px;
            }
            .subject-card {
                background-color: #ffffff;
                padding: 12px 15px;
                border-radius: 8px;
                border-left: 5px solid #2563EB;
                margin-bottom: 8px;
                border-top: 1px solid #eee;
                border-right: 1px solid #eee;
                border-bottom: 1px solid #eee;
            }
            .subject-label {
                color: #6B7280;
                font-size: 12px;
                margin-bottom: 2px;
            }
            .subject-name {
                display: block;
                font-weight: bold;
                color: #1E3A8A;
                font-size: 14px;
                margin-bottom: 4px;
            }
            .teacher-name {
                display: block;
                font-size: 13px;
                color: #374151;
            }
            </style>
        """, unsafe_allow_html=True)

        # 5. 상단 요일 안내
        if weekday < 5:
            st.success(f"📢 오늘은 **{today_name}요일**입니다. 수업 일정을 확인하세요!")
        else:
            st.info("😎 즐거운 주말입니다! 다음 주 시간표를 미리 확인하세요.")

        # 6. 주간 시간표 HTML 생성
        html = '<div class="timetable-container"><table class="styled-table"><thead><tr>'
        for col in timetable_main.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'

        for _, row in timetable_main.iterrows():
            html += '<tr>'
            for col_name, value in row.items():
                highlight = 'today-highlight' if col_name == today_name else ''
                # 화살표 기호일 경우 스타일 적용
                display_value = f'<span class="arrow-style">▽</span>' if value == '▽' else value
                html += f'<td class="{highlight}">{display_value}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

        # 시간표 출력
        st.markdown(html, unsafe_allow_html=True)

        # 7. 하단 과목 상세 정보 (카드 형태)
        st.markdown("---")
        with st.expander("🔍 과목별 상세 정보 및 담당 선생님", expanded=True):
            cols = st.columns(2)
            for idx, (_, row) in enumerate(subject_info.iterrows()):
                target_col = cols[idx % 2]
                target_col.markdown(f"""
                <div class="subject-card">
                    <div class="subject-label">과목명</div>
                    <div class="subject-name">{row['과목']}</div>
                    <div class="subject-label">담당 교사</div>
                    <div class="teacher-name">{row['담당교사']} 선생님</div>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"시간표를 불러오는 중 오류가 발생했습니다. ({e})")
