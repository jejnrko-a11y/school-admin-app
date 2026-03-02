import streamlit as st
import pandas as pd

def show_page(conn, user):
    st.title("⚙️ 비밀번호 변경")
    st.info(f"현재 {user['name']} 학생으로 로그인되어 있습니다.")
    
    with st.form("pw_change_form"):
        current_pw = st.text_input("현재 비밀번호", type="password")
        new_pw = st.text_input("새 비밀번호 (4자리 이상)", type="password")
        confirm_pw = st.text_input("새 비밀번호 확인", type="password")
        
        submit = st.form_submit_button("비밀번호 변경하기")
        
        if submit:
            try:
                # 최신 학생명부 데이터 읽기
                df = conn.read(worksheet="학생명부", ttl=0)
                # 현재 유저의 실제 데이터 위치 찾기
                user_idx = df[df['이름'] == user['name']].index[0]
                db_pw = str(df.loc[user_idx, '비밀번호'])
                
                if str(current_pw) != db_pw:
                    st.error("현재 비밀번호가 일치하지 않습니다.")
                elif new_pw != confirm_pw:
                    st.error("새 비밀번호가 서로 일치하지 않습니다.")
                elif len(new_pw) < 4:
                    st.error("비밀번호는 최소 4자리 이상이어야 합니다.")
                else:
                    # 비밀번호 업데이트
                    df.loc[user_idx, '비밀번호'] = str(new_pw)
                    conn.update(worksheet="학생명부", data=df)
                    st.success("✅ 비밀번호가 성공적으로 변경되었습니다! 다음 로그인부터 적용됩니다.")
            except Exception as e:
                st.error(f"오류가 발생했습니다: {e}")
