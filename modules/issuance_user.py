import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn, user, fixed_info):
    st.title("📜 증명서 신청 및 내역")
    
    # 데이터 로드
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except:
        df_log = pd.DataFrame(columns=["일련번호", "신청일시", "이름", "번호", "종류", "시간", "행선지", "사유", "상태", "승인일시"])

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # --- 탭 1: 신청서 작성 ---
    with tab1:
        with st.form("request_form"):
            c1, c2 = st.columns(2)
            with c1:
                cert_type = st.selectbox("종류", ["조퇴증", "외출증", "교내활동증"])
                target_date = st.date_input("발짜", value=get_kst().date())
            with c2:
                destination = st.text_input("행선지(장소)", placeholder="예: 병원, 가정, 과학관")
                reason = st.text_input("상세 사유", placeholder="예: 치과 진료")

            # 요일별 교시 로직
            weekday = target_date.weekday()
            period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
            if weekday == 1: period_options.append("7교시")
            period_options.append("종례")

            time_range = st.select_slider("⏰ 시간(교시) 범위", options=period_options, value=(period_options[0], period_options[-1]))
            
            if st.form_submit_button("🚀 신청서 제출", use_container_width=True):
                new_data = pd.DataFrame([{
                    "일련번호": "-", "신청일시": get_kst().strftime("%m-%d %H:%M"),
                    "이름": user['name'], "번호": user['num'], "종류": cert_type,
                    "시간": f"{target_date.strftime('%m/%d')} ({time_range[0]}~{time_range[1]})",
                    "행선지": destination, "사유": reason, "상태": "신청", "승인일시": "-"
                }])
                conn.update(worksheet="발급명부", data=pd.concat([df_log, new_data], ignore_index=True))
                st.success("신청되었습니다! 교사 승인 후 인쇄가 가능합니다.")
                st.cache_data.clear(); st.rerun()

    # --- 탭 2: 내 내역 확인 및 인쇄 ---
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("신청 내역이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status_color = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_color} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
                    st.write(f"**시간:** {row['시간']} / **행선지:** {row['행선지']}")
                    st.write(f"**사유:** {row['사유']}")
                    
                    if row['상태'] == "승인":
                        st.success(f"승인번호: {row['일련번호']} (승인일시: {row['승인일시']})")
                        if st.button("🖨️ 증명서 보기/인쇄", key=f"print_{idx}"):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("이 신청은 반려되었습니다. 담임 선생님께 문의하세요.")

def render_certificate(row, fixed_info):
    # 증명서 HTML 양식 (이전 디자인 참조)
    html_layout = f"""
    <div style="border:2px solid black; padding:30px; background:white; color:black; font-family:sans-serif; position:relative;">
        <div style="text-align:right;">제 {row['일련번호']} 호</div>
        <h1 style="text-align:center; text-decoration:underline; letter-spacing:10px;">{row['종류']}</h1>
        <table style="width:100%; border-collapse:collapse; margin-top:20px;">
            <tr style="border:1px solid black;"><td style="padding:10px; border:1px solid black; background:#f0f0f0;">성 명</td><td style="padding:10px; border:1px solid black;">{row['이름']}</td><td style="padding:10px; border:1px solid black; background:#f0f0f0;">학 번</td><td style="padding:10px; border:1px solid black;">{fixed_info['grade']}학년 {fixed_info['cls']}반 {row['번호']}번</td></tr>
            <tr style="border:1px solid black;"><td style="padding:10px; border:1px solid black; background:#f0f0f0;">일 시</td><td colspan="3" style="padding:10px; border:1px solid black;">{row['시간']}</td></tr>
            <tr style="border:1px solid black;"><td style="padding:10px; border:1px solid black; background:#f0f0f0;">행선지</td><td colspan="3" style="padding:10px; border:1px solid black;">{row['행선지']}</td></tr>
            <tr style="border:1px solid black;"><td style="padding:10px; border:1px solid black; background:#f0f0f0;">사 유</td><td colspan="3" style="padding:10px; border:1px solid black;">{row['사유']}</td></tr>
        </table>
        <p style="text-align:center; margin-top:30px;">위 학생은 위와 같은 사유로 {row['종류'].replace('증','')}함을 증명합니다.</p>
        <div style="text-align:center; margin-top:40px; font-size:20px; font-weight:bold;">경기기계공업고등학교장 (직인)</div>
    </div>
    <style>@media print {{ header, footer, .stButton {{ display:none; }} }}</style>
    """
    st.markdown(html_layout, unsafe_allow_html=True)
    components.html("<script>window.parent.print();</script>", height=0)
