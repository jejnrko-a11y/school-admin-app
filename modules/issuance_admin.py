import streamlit as st
import pandas as pd
from utils import get_kst

def show_page(conn):
    st.title("👨‍🏫 증명서 승인 관리")
    
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except:
        st.error("데이터베이스를 찾을 수 없습니다."); return

    pending = df_log[df_log['상태'] == "신청"]
    
    st.subheader(f"📥 미승인 신청 건수: {len(pending)}건")
    
    if pending.empty:
        st.info("새로운 신청 내역이 없습니다.")
    else:
        for idx, row in pending.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.write(f"**[{row['종류']}] {row['번호']}번 {row['이름']}**")
                    st.write(f"⏰ 시간: {row['시간']} | 📍 행선지: {row['행선지']}")
                    st.caption(f"사유: {row['사유']} (신청일시: {row['신청일시']})")
                with c2:
                    if st.button("✅ 승인", key=f"app_{idx}", use_container_width=True):
                        # 승인 로직: 일련번호 생성 및 상태 변경
                        now = get_kst()
                        serial = f"{now.year}-{len(df_log[df_log['상태']=='승인'])+1:03d}"
                        df_log.at[idx, '상태'] = "승인"
                        df_log.at[idx, '일련번호'] = serial
                        df_log.at[idx, '승인일시'] = now.strftime("%m-%d %H:%M")
                        conn.update(worksheet="발급명부", data=df_log)
                        st.success("승인되었습니다."); st.cache_data.clear(); st.rerun()
                    
                    if st.button("❌ 반려", key=f"rej_{idx}", use_container_width=True):
                        df_log.at[idx, '상태'] = "반려"
                        conn.update(worksheet="발급명부", data=df_log)
                        st.warning("반려 처리되었습니다."); st.cache_data.clear(); st.rerun()

    st.divider()
    with st.expander("📚 전체 발급 이력 보기"):
        st.dataframe(df_log.sort_values(by="신청일시", ascending=False), use_container_width=True, hide_index=True)
