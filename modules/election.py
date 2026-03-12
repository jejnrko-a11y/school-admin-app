import streamlit as st
import pandas as pd
import time
from utils import get_kst, load_student_list

def show_page(conn, user):
    st.title("🗳️ 실시간 반장/부반장 선거")
    
    # 1. 데이터 로드
    try:
        df_all = load_student_list(conn, exclude_admins=True) # 학생 명부 불러오기
        df_elec = conn.read(worksheet="선거관리", ttl=0)
        df_votes = conn.read(worksheet="선거_투표기록", ttl=0)
        df_set = conn.read(worksheet="선거_설정", ttl=0)
        
        df_elec.columns = df_elec.columns.str.strip()
        df_votes.columns = df_votes.columns.str.strip()
        df_set.columns = df_set.columns.str.strip()
    except Exception as e:
        st.error(f"데이터 로드 실패: {e}")
        return

    # 2. 교사용 관리 UI
    if user['name'] in ["교사", "관리자"]:
        st.subheader("🛠️ 교사 관리 도구")
        
        # [변경] 후보자 등록: 텍스트 입력 대신 명부에서 선택
        with st.expander("➕ 후보자 즉석 등록"):
            with st.form("add_candidate"):
                # 학생 명부에서 이름 목록 가져오기
                student_names = df_all['이름'].tolist()
                selected_student = st.selectbox("후보 선택", student_names)
                new_type = st.selectbox("구분", ["반장후보", "부반장후보"])
                
                if st.form_submit_button("등록"):
                    # 중복 등록 방지
                    if selected_student in df_elec['이름'].values:
                        st.error("이미 등록된 후보입니다.")
                    else:
                        new_df = pd.DataFrame([{
                            "구분": new_type, 
                            "기호": len(df_elec) + 1, 
                            "이름": selected_student, 
                            "공약": "공약없음", 
                            "득표수": 0
                        }])
                        conn.update(worksheet="선거관리", data=pd.concat([df_elec, new_df], ignore_index=True))
                        st.rerun()

        # 투표 상태 변경
        current_status = df_set.iloc[0]['상태']
        if st.button(f"현재 상태: {current_status} (클릭하여 변경)"):
            new_status = "종료" if current_status == "진행중" else "진행중"
            df_set.at[0, '상태'] = new_status
            conn.update(worksheet="선거_설정", data=df_set)
            st.rerun()

        # 결과 카운트 다운
        if st.button("📊 결과 긴장감 있게 보기"):
            st.write("### 득표 현황 카운트다운!")
            chart_placeholder = st.empty()
            for i in range(11): 
                temp_df = df_elec.copy()
                temp_df['득표수'] = (temp_df['득표수'] * (i/10)).astype(int)
                chart_placeholder.bar_chart(temp_df.set_index('이름')['득표수'])
                time.sleep(0.05)
            
            # 기권자 명단 출력
            voted_nums = df_votes['번호'].unique().tolist()
            abstainers = df_all[~df_all['번호'].isin(voted_nums)]
            st.warning(f"기권자: {', '.join(abstainers['이름'].tolist())}")
        return

    # 3. 학생 투표 UI
    if df_set.iloc[0]['상태'] == "종료":
        st.error("🚫 투표가 종료되었습니다.")
        return

    election_type = st.radio("선거 선택", ["반장선거", "부반장선거"], horizontal=True)
    target_type = "반장후보" if election_type == "반장선거" else "부반장후보"
    candidates = df_elec[df_elec['구분'] == target_type]

    # 이미 투표했는지 체크
    has_voted = not df_votes[(df_votes['선거종류'] == election_type) & 
                             (df_votes['번호'].astype(str) == str(user['num']))].empty

    if has_voted:
        st.success(f"✅ {election_type} 투표를 완료하셨습니다.")
    else:
        st.info("💡 후보자의 공약을 확인하고 투표해 주세요.")
        for _, row in candidates.iterrows():
            with st.container(border=True):
                st.subheader(f"기호 {row['기호']}. {row['이름']}")
                st.write(f"공약: {row['공약']}")
                if st.button(f"{row['이름']}에게 투표하기", key=f"v_{row['기름']}"):
                    df_elec.loc[df_elec['이름']==row['이름'], '득표수'] += 1
                    conn.update(worksheet="선거관리", data=df_elec)
                    new_vote = pd.DataFrame([{"번호": user['num'], "이름": user['name'], "선거종류": election_type, "투표일시": get_kst().strftime("%H:%M")}])
                    conn.update(worksheet="선거_투표기록", data=pd.concat([df_votes, new_vote], ignore_index=True))
                    st.rerun()
