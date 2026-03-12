import streamlit as st
import pandas as pd
from utils import get_kst, load_student_list

def show_page(conn, user):
    st.title("🗳️ 선거 관리 시스템")
    
    # 1. 데이터 로드 및 헤더 정리
    try:
        # 시트 데이터 로드
        df_elec = conn.read(worksheet="선거관리", ttl=0)
        df_votes = conn.read(worksheet="선거_투표기록", ttl=0)
        
        # 헤더 공백 제거
        df_elec.columns = df_elec.columns.str.strip()
        df_votes.columns = df_votes.columns.str.strip()
        
        # 2. 강제 데이터 구조 보정 (KeyError 방지)
        # 만약 투표기록 시트가 아예 비어있으면 헤더를 강제로 만듦
        if '선거종류' not in df_votes.columns:
            df_votes = pd.DataFrame(columns=['번호', '이름', '선거종류', '투표일시'])
            
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        return

    # 3. 선거 종류 선택
    election_type = st.radio("선거 선택", ["반장선거", "부반장선거"], horizontal=True, key="election_type_radio")
    target_type = "반장후보" if election_type == "반장선거" else "부반장후보"
    
    # 데이터 타입 정리
    df_elec['득표수'] = pd.to_numeric(df_elec['득표수'], errors='coerce').fillna(0)
    candidates = df_elec[df_elec['구분'] == target_type]

    # 4. 관리자(교사) UI
    if user['name'] in ["교사", "관리자"]:
        st.subheader(f"📊 {election_type} 현황")
        col1, col2 = st.columns(2)
        col1.metric("후보자 수", len(candidates))
        
        # 안전한 데이터 필터링
        vote_count = 0
        if not df_votes.empty and '선거종류' in df_votes.columns:
            vote_count = len(df_votes[df_votes['선거종류'] == election_type])
        col2.metric("총 투표수", vote_count)
        
        if not candidates.empty:
            st.bar_chart(candidates.set_index('이름')['득표수'])
        
        st.divider()
        st.subheader("📋 후보자 정보")
        st.dataframe(candidates, use_container_width=True)
        return

    # 5. 학생 UI
    has_voted = False
    if not df_votes.empty and '선거종류' in df_votes.columns and '번호' in df_votes.columns:
        has_voted = not df_votes[(df_votes['선거종류'] == election_type) & 
                                 (df_votes['번호'].astype(str) == str(user['num']))].empty

    if has_voted:
        st.success(f"✅ {election_type} 투표를 완료하셨습니다.")
    else:
        st.info(f"💡 후보자의 공약을 확인하고 투표해 주세요.")
        for idx, row in candidates.iterrows():
            with st.container(border=True):
                st.subheader(f"기호 {row['기호']}. {row['이름']}")
                st.write(f"**공약:** {row['공약']}")
                
                if st.button(f"{row['이름']}에게 투표하기", key=f"btn_{target_type}_{row['기호']}_{idx}"):
                    df_elec.loc[(df_elec['구분'] == target_type) & (df_elec['이름'] == row['이름']), '득표수'] += 1
                    conn.update(worksheet="선거관리", data=df_elec)
                    
                    new_vote = pd.DataFrame([{
                        "번호": user['num'], "이름": user['name'], 
                        "선거종류": election_type, "투표일시": get_kst().strftime("%m-%d %H:%M")
                    }])
                    conn.update(worksheet="선거_투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.rerun()
