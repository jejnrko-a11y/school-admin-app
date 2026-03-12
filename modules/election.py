import streamlit as st
import pandas as pd
from utils import load_student_list

def show_page(conn, user):
    st.title("🎉 [🎉 이벤트] 반장선거")

    # --- CSS: 칠판 스타일 ---
    st.markdown("""
        <style>
        .chalkboard {
            background-color: #2e5934; border: 15px solid #5d4037; border-radius: 20px; 
            padding: 40px; color: white; font-family: 'Courier New', monospace; text-align: center; 
            box-shadow: 10px 10px 20px rgba(0,0,0,0.5); margin: 20px 0; font-size: 1.5rem;
        }
        </style>
    """, unsafe_allow_html=True)

    # --- 1. 안전한 데이터 로드 (자체 TTL 캐싱 활용) ---
    # conn.read의 ttl=5 덕분에 아무리 새로고침을 연타해도 5초에 1번만 구글에 요청을 보냅니다.
    try:
        df_state = conn.read(worksheet="선거상태", ttl=5)
        df_db = conn.read(worksheet="선거데이터", ttl=5)
        all_students = load_student_list(conn, exclude_admins=True)
    except Exception as e:
        st.error("⚠️ 구글 시트 접근 제한(API 초과)이 발생했습니다.")
        st.info("💡 캐시 초기화로 인해 발생한 일시적 현상입니다. 딱 1분만 기다렸다가 [새로고침] 해주시면 정상 작동합니다!")
        return

    # 데이터 정제 및 병합
    all_students['번호'] = pd.to_numeric(all_students['번호'], errors='coerce').fillna(0).astype(int)
    
    df_data = pd.merge(all_students[['번호', '이름']], df_db, on=['번호', '이름'], how='left')
    df_data[['역할', '투표완료여부']] = df_data[['역할', '투표완료여부']].fillna({'역할': '일반', '투표완료여부': 'X'})
    df_data['득표수'] = pd.to_numeric(df_data['득표수'], errors='coerce').fillna(0).astype(int)
    
    status = str(df_state.at[0, '상태']).strip()

    # 후보자 세팅
    candidates = df_data[df_data['역할'] == '후보'].copy().reset_index(drop=True)
    candidates['기호'] = range(1, len(candidates) + 1)

    # --- 2. 교사용 제어 패널 ---
    if user['name'] in ['교사', '관리자']:
        with st.expander("🛠 교사용 제어 패널", expanded=True):
            c1, c2, c3, c4 = st.columns(4)
            
            if c1.button("▶ 투표 시작"): 
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '진행중'}]))
                st.success("✅ 투표가 시작되었습니다! (최대 5초 내 화면 반영)"); st.rerun()
                
            if c2.button("■ 투표 종료"): 
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '종료'}]))
                st.session_state.show_results = False
                st.success("✅ 투표가 종료되었습니다! (최대 5초 내 화면 반영)"); st.rerun()
                
            if c3.button("🔄 리셋"):
                df_data[['역할', '투표완료여부', '득표수']] =['일반', 'X', 0]
                final_df = df_data[['번호', '이름', '역할', '투표완료여부', '득표수']]
                conn.update(worksheet="선거데이터", data=final_df)
                conn.update(worksheet="선거상태", data=pd.DataFrame([{'상태': '대기'}]))
                st.session_state.show_results = False
                st.success("✅ 초기화 완료! (최대 5초 내 화면 반영)"); st.rerun()
                
            if c4.button("👥 투표자 확인"): 
                st.session_state.show_voters = not getattr(st.session_state, 'show_voters', False)

            if getattr(st.session_state, 'show_voters', False): 
                st.dataframe(df_data[['번호', '이름', '투표완료여부']].sort_values('번호'), use_container_width=True)
            
            # 후보 추가
            selected = st.selectbox("후보 등록", df_data.sort_values('번호')['이름'])
            if st.button("후보 추가"):
                df_data.loc[df_data['이름'] == selected, '역할'] = '후보'
                final_df = df_data[['번호', '이름', '역할', '투표완료여부', '득표수']]
                conn.update(worksheet="선거데이터", data=final_df)
                st.success(f"✅ {selected} 후보 등록 완료! (구글 시트 동기화 중... 최대 5초 내 칠판에 나타납니다)"); st.rerun()

    # --- 3. 칠판 UI ---
    chalk = f"<h2>{'⏳ 투표 대기 중' if status=='대기' else '🗳️ 투표 진행 중' if status=='진행중' else '🏁 투표가 종료되었습니다.'}</h2>"
    
    if status == "대기":
        for _, row in candidates.iterrows(): 
            chalk += f"<p>✍️ 기호 {row['기호']}번. {row['이름']}</p>"
            
    elif status == "종료":
        if st.button("✨ 결과 확인하기"): 
            st.session_state.show_results = True
            
        if getattr(st.session_state, 'show_results', False):
            chalk = "<h2>🏆 최종 결과</h2>"
            for _, row in candidates.iterrows(): 
                chalk += f"<p>기호 {row['기호']}번 {row['이름']} : {int(row['득표수'])}표</p>"
            
            if not candidates.empty:
                max_v = candidates['득표수'].max()
                if max_v > 0:
                    winners = candidates[candidates['득표수'] == max_v]['이름'].tolist()
                    chalk += f"<br><h3>🎉 당선을 축하합니다! {', '.join(winners)}님! 🎈</h3>"
                else:
                    chalk += "<br><h3>투표된 표가 없습니다.</h3>"
            else:
                chalk += "<br><h3>등록된 후보가 없습니다.</h3>"

    st.markdown(f'<div class="chalkboard">{chalk}</div>', unsafe_allow_html=True)

    # --- 4. 학생 투표 로직 ---
    if status == "진행중" and user['name'] not in ['교사', '관리자']:
        my_idx = df_data[df_data['이름'] == user['name']].index
        
        if not my_idx.empty and df_data.at[my_idx[0], '투표완료여부'] == 'O':
            st.info("✨ 소중한 투표 감사합니다! 개표를 기다려주세요.")
        else:
            options = [f"기호 {row['기호']}번. {row['이름']}" for _, row in candidates.iterrows()] + ['기권']
            choice = st.radio("후보 선택", options)
            
            if st.button("투표 제출"):
                if choice != '기권':
                    selected_name = choice.split(". ")[1]
                    cand_idx = df_data[df_data['이름'] == selected_name].index[0]
                    df_data.at[cand_idx, '득표수'] += 1
                    
                df_data.at[my_idx[0], '투표완료여부'] = 'O'
                
                final_df = df_data[['번호', '이름', '역할', '투표완료여부', '득표수']]
                conn.update(worksheet="선거데이터", data=final_df)
                
                st.success("투표가 완료되었습니다!"); st.rerun()
