import streamlit as st
import pandas as pd
from utils import get_kst, load_student_list

def show_page(conn, user):
    # 1. UI 헤더 및 상단 메뉴
    st.title("🗳️ 선거 관리 시스템")
    
    # 2. 데이터 로드
    try:
        # 학생 명부에서 학생 리스트 로드
        df_all = load_student_list(conn, exclude_admins=True)
        # 선거관리 시트 로드
        df_elec = conn.read(worksheet="선거관리", ttl=0)
        # 투표기록 시트 로드
        df_votes = conn.read(worksheet="선거_투표기록", ttl=0)
    except Exception as e:
        st.error(f"데이터를 불러오는 중 오류 발생: {e}")
        st.info("구글 시트에 '선거관리', '선거_투표기록' 탭이 있는지 확인하세요.")
        return

    # 3. 선거 종류 선택
    election_type = st.radio("선거 선택", ["반장선거", "부반장선거"], horizontal=True)
    target_type = "반장후보" if election_type == "반장선거" else "부반장후보"
    candidates = df_elec[df_elec['구분'] == target_type]

    # 4. 관리자 UI
    if user['name'] in ["교사", "관리자"]:
        st.subheader(f"📊 {election_type} 현황")
        col1, col2 = st.columns(2)
        col1.metric("후보자 수", len(candidates))
        col2.metric("총 투표수", len(df_votes[df_votes['선거종류'] == election_type]))
        
        st.bar_chart(candidates.set_index('이름')['득표수'])
        
        st.divider()
        st.subheader("📋 후보자 상세 정보")
        st.dataframe(candidates, use_container_width=True)
        return

    # 5. 학생 UI
    # 투표 여부 확인
    voted_list = df_votes[(df_votes['선거종류'] == election_type) & (df_votes['번호'] == user['num'])]
    has_voted = not voted_list.empty

    if has_voted:
        st.success(f"✅ {election_type} 투표를 완료하셨습니다.")
    else:
        st.info(f"💡 후보자의 공약을 확인하고 투표해 주세요.")
        for _, row in candidates.iterrows():
            with st.container(border=True):
                st.subheader(f"기호 {row['기호']}. {row['이름']}")
                st.write(f"**공약:** {row['공약']}")
                
                if st.button(f"{row['이름']}에게 투표", key=f"vote_{target_type}_{row['기호']}"):
                    # 득표수 업데이트
                    df_elec.loc[(df_elec['구분'] == target_type) & (df_elec['이름'] == row['이름']), '득표수'] += 1
                    conn.update(worksheet="선거관리", data=df_elec)
                    
                    # 투표 기록 저장
                    new_vote = pd.DataFrame([{
                        "번호": user['num'], "이름": user['name'], 
                        "선거종류": election_type, "투표일시": get_kst().strftime("%m-%d %H:%M")
                    }])
                    conn.update(worksheet="선거_투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.rerun()
