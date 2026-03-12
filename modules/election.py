import streamlit as st
import pandas as pd
from utils import load_student_list

def show_page(conn, user):
    st.title("🎉 [🎉 이벤트] 반장선거")
    st.markdown("""<style>.chalkboard { background-color: #2e5934; border: 15px solid #5d4037; border-radius: 20px; 
                  padding: 40px; color: white; font-family: 'Courier New', monospace; text-align: center; 
                  box-shadow: 10px 10px 20px rgba(0,0,0,0.5); margin: 20px 0; font-size: 1.5rem; }</style>""", unsafe_allow_html=True)

    # 1. 데이터 로드 및 초기화
    if 'elec_data' not in st.session_state:
        df_state = conn.read(worksheet="선거상태", ttl=0)
        df_db = conn.read(worksheet="선거데이터", ttl=0)
        all_students = load_student_list(conn, exclude_admins=True)
        
        # [데이터 구조 강제] 명부와 병합 후 정확한 컬럼 순서 유지
        df_data = pd.merge(all_students[['번호', '이름']], df_db, on=['번호', '이름'], how='left')
        df_data['역할'] = df_data['역할'].fillna('일반')
        df_data['투표완료여부'] = df_data['투표완료여부'].fillna('X')
        df_data['득표수'] = pd.to_numeric(df_data['득표수'], errors='coerce').fillna(0).astype(int)
        
        st.session_state.elec_state = df_state
        st.session_state.elec_data = df_data

    df_data = st.session_state.elec_data
    status = st.session_state.elec_state.at[0, '상태']

    # 2. 교사 제어
    if user['name'] in ['교사', '관리자']:
        with st.expander("🛠 교사용 제어 패널"):
            c1, c2, c3, c4 = st.columns(4)
            if c1.button("▶ 투표 시작"): 
                st.session_state.elec_state.at[0, '상태'] = '진행중'
                conn.update(worksheet="선거상태", data=st.session_state.elec_state); st.rerun()
            if c2.button("■ 투표 종료"): 
                st.session_state.elec_state.at[0, '상태'] = '종료'
                conn.update(worksheet="선거상태", data=st.session_state.elec_state); st.rerun()
            if c3.button("🔄 리셋"):
                df_data[['역할', '투표완료여부', '득표수']] = ['일반', 'X', 0]
                conn.update(worksheet="선거데이터", data=df_data)
                st.session_state.elec_state.at[0, '상태'] = '대기'; conn.update(worksheet="선거상태", data=st.session_state.elec_state)
                st.session_state.elec_data = df_data; st.rerun()
            if c4.button("👥 투표자 확인"): st.session_state.show_voters = not getattr(st.session_state, 'show_voters', False)

            if getattr(st.session_state, 'show_voters', False): st.dataframe(df_data)
            
            selected = st.selectbox("후보 등록", df_data.sort_values('번호')['이름'])
            if st.button("후보 추가"):
                df_data.loc[df_data['이름'] == selected, '역할'] = '후보'
                conn.update(worksheet="선거데이터", data=df_data); st.rerun()

    # 3. 칠판 UI
    candidates = df_data[df_data['역할'] == '후보'].reset_index(drop=True)
    chalk = f"<h2>{'⏳ 투표 대기' if status=='대기' else '🗳️ 투표 진행중' if status=='진행중' else '🏆 종료'}</h2>"
    
    if status == "대기":
        for i, row in candidates.iterrows(): chalk += f"<p>✍️ 기호 {i+1}번. {row['이름']}</p>"
    elif status == "종료":
        st.warning("선거가 종료되었습니다.")
        if st.button("✨ 결과 확인"): st.session_state.show_results = True
        if getattr(st.session_state, 'show_results', False):
            for i, row in candidates.iterrows(): chalk += f"<p>기호 {i+1}번 {row['이름']} : {int(row['득표수'])}표</p>"
            if not candidates.empty and candidates['득표수'].max() > 0:
                winners = candidates[candidates['득표수'] == candidates['득표수'].max()]['이름'].tolist()
                chalk += f"<h3>🎉 당선: {', '.join(winners)}님!</h3>"

    st.markdown(f'<div class="chalkboard">{chalk}</div>', unsafe_allow_html=True)

    # 4. 학생 투표
    if status == "진행중" and user['name'] not in ['교사', '관리자']:
        my_idx = df_data[df_data['이름'] == user['name']].index[0]
        if df_data.at[my_idx, '투표완료여부'] == 'O':
            st.info("✨ 소중한 투표 감사합니다! 개표를 기다려주세요.")
        else:
            options = candidates['이름'].tolist() + ['기권']
            choice = st.radio("후보 선택", options)
            if st.button("투표 제출"):
                if choice != '기권':
                    # [핵심] 득표수 업데이트 (데이터프레임 순서 유지)
                    cand_idx = df_data[df_data['이름'] == choice].index[0]
                    df_data.at[cand_idx, '득표수'] += 1
                df_data.at[my_idx, '투표완료여부'] = 'O'
                
                # 시트 업데이트 (정확한 컬럼 순서로)
                final_df = df_data[['번호', '이름', '역할', '투표완료여부', '득표수']]
                conn.update(worksheet="선거데이터", data=final_df)
                st.session_state.elec_data = df_data
                st.success("투표 완료!"); st.rerun()
