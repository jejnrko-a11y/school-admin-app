import streamlit as st
import pandas as pd

def show_page(conn, user):
    st.title("⚙️ 비밀번호 변경")
    st.write(f"**{user['name']}** 학생의 비밀번호를 안전하게 변경합니다.")
    
    with st.form("pw_change_form"):
        curr_pw = st.text_input("현재 비밀번호", type="password")
        new_pw = st.text_input("새 비밀번호 (4자리 이상)", type="password")
        conf_pw = st.text_input("새 비밀번호 확인", type="password")
        
        submit = st.form_submit_button("비밀번호 변경 완료")
        
        if submit:
            try:
                # 최신 명부 데이터 로드
                df = conn.read(worksheet="학생명부", ttl=0)
                user_idx = df[df['이름'] == user['name']].index[0]
                db_pw = str(df.loc[user_idx, '비밀번호'])
                
                if str(curr_pw) != db_pw:
                    st.error("현재 비밀번호가 일치하지 않습니다.")
                elif new_pw != conf_pw:
                    st.error("새 비밀번호가 서로 일치하지 않습니다.")
                elif len(new_pw) < 4:
                    st.error("비밀번호는 최소 4자리 이상이어야 합니다.")
                else:
                    # 구글 시트에 업데이트
                    df.loc[user_idx, '비밀번호'] = str(new_pw)
                    conn.update(worksheet="학생명부", data=df)
                    st.success("✅ 비밀번호가 변경되었습니다! 다음 로그인부터 적용됩니다.")
            except Exception as e:
                st.error(f"변경 중 오류가 발생했습니다: {e}")
