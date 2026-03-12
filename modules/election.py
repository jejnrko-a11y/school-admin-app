import streamlit as st
import pandas as pd
from utils import get_kst, load_student_list

def show_page(conn, user):
    st.title("🗳️ 선거 관리 시스템")
    
    # 1. 데이터 로드 및 헤더 강제 설정
    try:
        # worksheet의 헤더가 1행에 있음을 명시적으로 처리
        df_elec = conn.read(worksheet="선거관리", ttl=0, usecols=None)
        df_votes = conn.read(worksheet="선거_투표기록", ttl=0, usecols=None)
        
        # 컬럼 이름의 공백 제거 및 데이터 타입 정리
        df_elec.columns = df_elec.columns.str.strip()
        df_votes.columns = df_votes.columns.str.strip()
        
    except Exception as e:
        st.error(f"데이터베이스 연결 오류: {e}")
        st.info("구글 시트에 '선거관리', '선거_투표기록' 탭이 있는지 확인하세요.")
        return

    # 필수 컬럼 확인 (디버깅용)
    if not all(col in df_elec.columns for col in ['구분', '기호', '이름', '공약', '득표수']):
        st.error(f"시트 헤더 오류: 현재 시트 컬럼은 {df_elec.columns.tolist()} 입니다.")
        st.warning("구글 시트 '선거관리' 탭 1행에 [구분, 기호, 이름, 공약, 득표수]가 정확히 있는지 확인하세요.")
        return

    # 2. 선거 종류 선택
    election_type = st.radio("선거 선택", ["반장선거", "부반장선거"], horizontal=True, key="election_type_radio")
    target_type = "반장후보" if election_type == "반장선거" else "부반장후보"
    
    # 데이터 처리
    df_elec['득표수'] = pd.to_numeric(df_elec['득표수'], errors='coerce').fillna(0)
    candidates = df_elec[df_elec['구분'] == target_type]

    # 3. 관리자(교사) UI
    if user['name'] in ["교사", "관리자"]:
        st.subheader(f"📊 {election_type} 현황")
        col1, col2 = st.columns(2)
        col1.metric("후보자 수", len(candidates))
        col2.metric("총 투표수", len(df_votes[df_votes['선거종류'] == election_type]))
        
        if not candidates.empty:
            st.bar_chart(candidates.set_index('이름')['득표수'])
        
        st.divider()
        st.subheader("📋 후보자 정보 및 관리")
        st.dataframe(candidates, use_container_width=True)
        return

    # 4. 학생 UI
    # 투표 여부 확인
    voted_list = df_votes[(df_votes['선거종류'] == election_type) & (df_votes['번호'].astype(str) == str(user['num']))]
    has_voted = not voted_list.empty

    if has_voted:
        st.success(f"✅ {election_type} 투표를 완료하셨습니다.")
    else:
        st.info(f"💡 후보자의 공약을 확인하고 투표해 주세요.")
        for idx, row in candidates.iterrows():
            with st.container(border=True):
                st.subheader(f"기호 {row['기호']}. {row['이름']}")
                st.write(f"**공약:** {row['공약']}")
                
                # 버튼 클릭 시 처리
                if st.button(f"{row['이름']}에게 투표하기", key=f"btn_{target_type}_{row['기호']}"):
                    # 득표수 1 증가
                    df_elec.loc[(df_elec['구분'] == target_type) & (df_elec['이름'] == row['이름']), '득표수'] += 1
                    conn.update(worksheet="선거관리", data=df_elec)
                    
                    # 투표 기록 추가
                    new_vote = pd.DataFrame([{
                        "번호": user['num'], "이름": user['name'], 
                        "선거종류": election_type, "투표일시": get_kst().strftime("%m-%d %H:%M")
                    }])
                    conn.update(worksheet="선거_투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.rerun()
