import streamlit as st
import pandas as pd
from utils import get_kst

def show_page(conn):
    st.title("📅 학급 시간표")
    st.write("3학년 2반(컴퓨터전자과) 시간표입니다.")

    try:
        # 1. 구글 시트에서 시간표 읽기
        df = conn.read(worksheet="시간표", ttl=3600) # 1시간마다 갱신
        
        if df.empty:
            st.warning("시간표 데이터가 없습니다. 구글 시트를 확인해 주세요.")
            return

        # 2. 오늘 요일 파악 (월:0, 화:1 ... 금:4, 토:5, 일:6)
        now = get_kst()
        weekday = now.weekday()
        days_kor = ["월", "화", "수", "목", "금", "토", "일"]
        today_name = days_kor[weekday]

        # 3. 상단 안내 메시지
        if weekday < 5:
            st.success(f"오늘은 **{today_name}요일**입니다. 수업 일정을 확인하세요!")
        else:
            st.info("오늘은 즐거운 주말입니다! 다음 주 시간표를 미리 확인하세요.")

        # 4. 시간표 디자인 (HTML/CSS 활용)
        # 오늘 요일 컬럼을 강조하는 스타일 적용
        def highlight_today(col):
            if col.name == today_name:
                return ['background-color: #EBF5FF; font-weight: bold; border: 2px solid #2563EB' for _ in col]
            return ['' for _ in col]

        # Pandas Styler로 시각화
        styled_df = df.style.apply(highlight_today, axis=0) \
                        .set_properties(**{
                            'text-align': 'center',
                            'padding': '10px',
                            'border': '1px solid #dee2e6'
                        }) \
                        .set_table_styles([
                            {'selector': 'th', 'props': [('background-color', '#1E3A8A'), ('color', 'white'), ('font-size', '16px')]}
                        ])

        # 화면 출력
        st.table(styled_df)
        
        st.caption("※ 시간표는 학교 사정에 따라 변경될 수 있습니다.")

    except Exception as e:
        st.error(f"시간표를 불러오는 중 오류가 발생했습니다: {e}")
