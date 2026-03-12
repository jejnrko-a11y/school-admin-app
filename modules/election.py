import streamlit as st
import pandas as pd
from utils import load_student_list

def show_page(conn, user):
    st.title("🎉 [🎉 이벤트] 반장선거")

    # 1. CSS: 칠판 스타일
    st.markdown("""<style>.chalkboard { background-color: #2e5934; border: 15px solid #5d4037; border-radius: 20px; 
                  padding: 40px; color: white; font-family: 'Courier New', monospace; text-align: center; 
                  box-shadow: 10px 10px 20px rgba(0,0,0,0.5); margin: 20px 0; font-size: 1.5rem; }</style>""", unsafe_allow_html=True)

    # 2. 데이터 로드 및 명부 동기화
    if 'elec_data' not in st.session_state:
        try:
            df_state = conn.read(worksheet="선거상태", ttl=0)
            df_db = conn.read(worksheet="선거데이터", ttl=0)
            all_students = load_student_list(conn, exclude_admins=True)
            # 학생 번호를 1부터 시작하도록 보장 (혹시 모를 0 시작 대비)
            all_students['번호'] = pd.to_numeric(all_students['번호'], errors='coerce').fillna(0).astype(int)
            
            df_data = pd.merge(all_students[['번호', '이름']], df_db, on=['번호', '이름'], how='left')
            df_data[['역할', '투표완료여부']] = df_data[['역할', '투표완료여부']].fillna({'역할': '일반', '투표완료여부': 'X'})
            df_data['득표수'] = df_data['득표수'].fillna(0)
            st.session_state.elec_state = df_state
            st.session_state.elec_data = df_data
        except: return

    df_state = st.session_state.elec_state
    df_data = st.session_state.elec_data
    status = df_state.at[0, '상태']
    candidates = df_data[df_data['역할'] == '후보']

    # 3. 교사 제어 패널
    if user['name'] in ['교사', '관리자']:
        with st.expander("🛠 교사용 제어 패널"):
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("▶ 투표 시작"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '진행중'}])); st.session_state.elec_state.at[0,'상태']='진행중'; st.rerun()
            if c2.button("■ 투표 종료"): conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '종료'}])); st.session_state.elec_state.at[0,'상태']='종료'; st.rerun()
            if c3.button("🔄 리셋"):
                df_data[['역할', '투표완료여부', '득표수']] = ['일반', 'X', 0]; conn.update(worksheet="선거데이터", data=df_data)
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '대기'}])); st.session_state.elec_data=df_data; st.session_state.elec_state.at[0,'상태']='대기'; st.rerun()
            if c4.button("👥 투표자"): st.session_state.show_voters = not getattr(st.session_state, 'show_voters', False)

            if getattr(st.session_state, 'show_voters', False): st.dataframe(df_data[['번호', '이름', '투표완료여부']].sort_values('번호'))
            
            selected = st.selectbox("후보 등록", df_data.sort_values('번호')['이름'])
            if st.button("후보 추가"):
                df_data.loc[df_data['이름'] == selected, '역할'] = '후보'
                conn.update(worksheet="선거데이터", data=df_data); st.session_state.elec_data=df_data; st.rerun()

    # 4. 칠판 UI
    chalk = f"<h2>{'⏳ 투표 대기' if status=='대기' else '🗳️ 투표 진행중' if status=='진행중' else '🏆 최종 결과'}</h2>"
    
    if status == "대기":
        for i, row in candidates.iterrows(): chalk += f"<p>✍️ {row['이름']}</p>"
    elif status == "종료":
        if st.button("✨ 결과 확인하기"): st.session_state.show_results = True
        if getattr(st.session_state, 'show_results', False):
            if not candidates.empty:
                for _, row in candidates.iterrows(): chalk += f"<p>{row['이름']} : {int(row['득표수'])}표</p>"
                max_v = candidates['득표수'].max()
                if max_v > 0:
                    winners = candidates[candidates['득표수'] == max_v]['이름'].tolist()
                    chalk += f"<br><h3>🎉 당선: {', '.join(winners)}님!</h3>"
            else: chalk += "<p>등록된 후보가 없습니다.</p>"

    st.markdown(f'<div class="chalkboard">{chalk}</div>', unsafe_allow_html=True)

    # 5. 학생 투표
    if status == "진행중" and user['name'] not in ['교사', '관리자']:
        if df_data.loc[df_data['이름']==user['name'], '투표완료여부'].values[0] == 'O':
            st.warning("이미 투표 완료")
        else:
            options = candidates['이름'].tolist() + ['기권']
            choice = st.radio("후보 선택", options)
            if st.button("투표 제출"):
                if choice != '기권': df_data.loc[df_data['이름'] == choice, '득표수'] += 1
                df_data.loc[df_data['이름'] == user['name'], '투표완료여부'] = 'O'
                conn.update(worksheet="선거데이터", data=df_data)
                st.session_state.elec_data = df_data; st.rerun()
