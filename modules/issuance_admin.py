import streamlit as st
import pandas as pd
from utils import get_kst

def show_page(conn):
    st.title("👨‍🏫 증명서 승인 관리")
    
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
        if "반려사유" not in df_log.columns:
            df_log["반려사유"] = ""
    except:
        st.error("데이터베이스를 찾을 수 없습니다."); return

    pending = df_log[df_log['상태'] == "신청"]
    st.subheader(f"📥 미승인 신청 건수: {len(pending)}건")
    
    if pending.empty:
        st.info("새로운 신청 내역이 없습니다.")
    else:
        for idx, row in pending.iterrows():
            with st.container(border=True):
                c1, c2 = st.columns([2, 1])
                with c1:
                    st.write(f"**[{row['종류']}] {row['번호']}번 {row['이름']}**")
                    st.write(f"📝 신청시간: {row['시간']}")
                    st.caption(f"사유: {row['사유']} | 행선지: {row['행선지']}")
                    
                    # 승인용 실제 시간 입력
                    actual_time = st.text_input("✅ 실제 허가 시간 입력", placeholder="예: 10:40 ~ 15:20", key=f"time_{idx}")
                    # 반려용 사유 입력
                    reject_reason = st.text_input("❌ 반려 사유 입력 (반려 시에만)", placeholder="예: 수업 결손 과다, 서류 미비 등", key=f"rej_res_{idx}")
                
                with c2:
                    if st.button("✅ 승인", key=f"app_{idx}", use_container_width=True):
                        if not actual_time:
                            st.warning("시간을 입력해야 승인이 가능합니다.")
                        else:
                            now = get_kst()
                            serial = f"{now.year}-{len(df_log[df_log['상태']=='승인'])+1:03d}"
                            df_log.at[idx, '상태'] = "승인"
                            df_log.at[idx, '일련번호'] = serial
                            df_log.at[idx, '시간'] = actual_time 
                            df_log.at[idx, '승인일시'] = now.strftime("%m-%d %H:%M")
                            conn.update(worksheet="발급명부", data=df_log)
                            st.success("승인 완료!"); st.cache_data.clear(); st.rerun()
                    
                    if st.button("❌ 반려", key=f"rej_{idx}", use_container_width=True):
                        if not reject_reason:
                            st.warning("반려 사유를 입력해 주세요.")
                        else:
                            df_log.at[idx, '상태'] = "반려"
                            df_log.at[idx, '반려사유'] = reject_reason
                            conn.update(worksheet="발급명부", data=df_log)
                            st.warning("반려 처리됨!"); st.cache_data.clear(); st.rerun()

    st.divider()
    with st.expander("📚 전체 발급 이력 보기"):
        st.dataframe(df_log.sort_values(by="신청일시", ascending=False), use_container_width=True, hide_index=True)
