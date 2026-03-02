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

        # [수정] 2. 데이터 전처리: nan을 빈칸으로 변경
        df = df.fillna('')

        # 3. 오늘 요일 파악
        now = get_kst()
        weekday = now.weekday()
        days_kor = ["월", "화", "수", "목", "금", "토", "일"]
        today_name = days_kor[weekday]

        # 4. 시간표 디자인 및 가운데 정렬 설정
        def highlight_today(col):
            if col.name == today_name:
                return ['background-color: #EBF5FF; font-weight: bold;' for _ in col]
            return ['' for _ in col]

        # Pandas Styler 적용
        styled_df = df.style.hide(axis='index') \
                        .apply(highlight_today, axis=0) \
                        .set_properties(**{
                            'text-align': 'center',
                            'vertical-align': 'middle'
                        }) \
                        .set_table_styles([
                            # 헤더(제목) 가운데 정렬 및 스타일
                            {'selector': 'th', 'props': [
                                ('background-color', '#1E3A8A'), 
                                ('color', 'white'), 
                                ('text-align', 'center'),
                                ('font-size', '16px')
                            ]},
                            # 모든 셀 가로 정렬
                            {'selector': 'td', 'props': [
                                ('text-align', 'center')
                            ]}
                        ])

        # 5. 요일 안내 메시지
        if weekday < 5:
            st.success(f"오늘은 **{today_name}요일**입니다.")
        else:
            st.info("주말입니다. 다음 주 시간표를 확인하세요.")

        # 6. 테이블 출력
        st.table(styled_df)
        
        st.caption("※ 시간표는 학교 사정에 따라 변경될 수 있습니다.")

    except Exception as e:
        st.error(f"시간표 로드 오류: {e}")
