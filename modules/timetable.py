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
        subject_info = df[['과목', '담당교사']].replace('', None).dropna().drop_duplicates()

        # 3. 오늘 요일 파악
        now = get_kst()
        weekday = now.weekday()
        days_kor = ["월", "화", "수", "목", "금", "토", "일"]
        today_name = days_kor[weekday]

        # 4. 스타일 정의 (중앙 정렬 및 디자인)
        st.markdown("""
            <style>
            .timetable-container {
                margin-top: 20px;
                margin-bottom: 30px;
            }
            .styled-table {
                width: 100%;
                border-collapse: collapse;
                border-radius: 10px;
                overflow: hidden;
                box-shadow: 0 0 20px rgba(0, 0, 0, 0.1);
            }
            .styled-table th {
                background-color: #1E3A8A !important;
                color: white !important;
                text-align: center !important;
                padding: 15px !important;
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
            .subject-card {
                background-color: white;
                padding: 15px;
                border-radius: 10px;
                border-left: 5px solid #2563EB;
                margin-bottom: 10px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.05);
            }
            </style>
        """, unsafe_allow_html=True)

        # 5. 주간 시간표 HTML 생성
        html = '<div class="timetable-container"><table class="styled-table"><thead><tr>'
        for col in timetable_main.columns:
            html += f'<th>{col}</th>'
        html += '</tr></thead><tbody>'

        for _, row in timetable_main.iterrows():
            html += '<tr>'
            for col_name, value in row.items():
                highlight = 'today-highlight' if col_name == today_name else ''
                # 엑셀의 화살표(∇) 기호가 있을 경우 디자인적 허용 또는 처리
                display_value = value if value != '▽' else '<span style="color:#ccc;">"</span>'
                html += f'<td class="{highlight}">{display_value}</td>'
            html += '</tr>'
        html += '</tbody></table></div>'

        # 6. 상단 요일 안내
        if weekday < 5:
            st.success(f"📢 오늘은 **{today_name}요일**입니다. 수업 일정을 확인하세요!")
        else:
            st.info("😎 즐거운 주말입니다! 다음 주 시간표를 미리 확인하세요.")

        # 7. 시간표 출력
        st.markdown(html, unsafe_allow_html=True)

        # 8. 하단 과목 상세 정보 (카드 형태)
        with st.expander("🔍 과목별 상세 정보 및 담당 선생님", expanded=True):
            cols = st.columns(2)
            for idx, (_, row) in enumerate(subject_info.iterrows()):
                target_col = cols[idx % 2]
                target_col.markdown(f"""
                <div class="subject-card">
                    <small style="color: #6B7280;">과목명</small>< dream style="display:block; font-weight:bold; color: #1E3A8A;">{row['과목']}</dream>
                    <small style="color: #6B7280;">담당</small><span style="display:block;">{row['담당교사']} 선생님</span>
                </div>
                """, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"시간표를 불러오는 중 오류가 발생했습니다. 시트 구성을 확인해주세요. ({e})")
