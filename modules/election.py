import streamlit as st
import pandas as pd
from utils import load_student_list

# API 호출 횟수를 획기적으로 줄이는 캐싱 함수
@st.cache_data(ttl=60)
def get_latest_data(_conn):
    try:
        # 한 번의 호출로 데이터를 가져옵니다.
        df_state = _conn.read(worksheet="선거상태", ttl=0)
        df_db = _conn.read(worksheet="선거데이터", ttl=0)
        all_students = load_student_list(_conn, exclude_admins=True)
        return df_state, df_db, all_students
    except Exception as e:
        st.error(f"구글 시트 연결 오류: {e}")
        return None, None, None

def show_page(conn, user):
    st.title("🎉 [🎉 이벤트] 반장선거")
    
    # 1. 캐시된 데이터 로드
    df_state, df_db, all_students = get_latest_data(conn)
    if df_state is None: return

    # 병합
    df_data = pd.merge(all_students[['번호', '이름']], df_db, on=['번호', '이름'], how='left')
    df_data[['역할', '투표완료여부']] = df_data[['역할', '투표완료여부']].fillna({'역할': '일반', '투표완료여부': 'X'})
    df_data['득표수'] = pd.to_numeric(df_data['득표수'], errors='coerce').fillna(0).astype(int)
    
    status = df_state.at[0, '상태']

    # 2. 교사 제어 패널
    if user['name'] in ['교사', '관리자']:
        with st.expander("🛠 교사용 제어 패널"):
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("▶ 투표 시작"): 
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '진행중'}]))
                st.cache_data.clear(); st.rerun()
            if c2.button("■ 투표 종료"): 
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '종료'}]))
                st.cache_data.clear(); st.rerun()
            # ... (나머지 리셋/투표자 확인 동일)


    # 4. 칠판 UI
    chalk = f"<h2>{'⏳ 투표 대기' if status=='대기' else '🗳️ 투표 진행중' if status=='진행중' else '🏁 투표 종료'}</h2>"
    
    if status == "대기":
        for i, row in candidates.iterrows(): chalk += f"<p>✍️ 기호 {i+1}번. {row['이름']}</p>"
    elif status == "종료":
        # 결과 확인 전: 투표 현황만 표시
        total_voted = len(df_data[df_data['투표완료여부'] == 'O'])
        total_votes = candidates['득표수'].sum()
        abstain_count = total_voted - total_votes
        
        chalk += f"<p>총 투표자: {total_voted}명</p><p>기권표: {abstain_count}표</p>"
        
        if st.button("✨ 결과 확인하기"): st.session_state.show_results = True
        
        if getattr(st.session_state, 'show_results', False):
            chalk = "<h2>🏆 최종 결과</h2>"
            for i, row in candidates.iterrows(): chalk += f"<p>기호 {i+1}번 {row['이름']} : {int(row['득표수'])}표</p>"
            if not candidates.empty and candidates['득표수'].max() > 0:
                winners = candidates[candidates['득표수'] == candidates['득표수'].max()]['이름'].tolist()
                chalk += f"<br><h3>🎉 당선: {', '.join(winners)}님!</h3>"

    st.markdown(f'<div class="chalkboard">{chalk}</div>', unsafe_allow_html=True)

    # 5. 학생 투표
    if status == "진행중" and user['name'] not in ['교사', '관리자']:
        if df_data.loc[df_data['이름']==user['name'], '투표완료여부'].values[0] == 'O':
            st.info("✨ 소중한 투표 감사합니다! 개표를 기다려주세요.")
        else:
            options = candidates['이름'].tolist() + ['기권']
            choice = st.radio("후보 선택", options)
            if st.button("투표 제출"):
                if choice != '기권':
                    df_data.loc[df_data['이름'] == choice, '득표수'] += 1
                df_data.loc[df_data['이름'] == user['name'], '투표완료여부'] = 'O'
                conn.update(worksheet="선거데이터", data=df_data)
                st.success("투표 완료!"); st.rerun()
