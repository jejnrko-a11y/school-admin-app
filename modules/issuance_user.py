import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst, send_discord_notification

def show_page(conn, user, fixed_info):
    # 인쇄 설정에서 자동 인쇄 스크립트 제거 및 화면 최적화
    st.markdown("""
<style>
[data-testid="stDataFrame"] { font-size: 12px !important; }
/* 인쇄 버튼을 눌렀을 때만 작동하도록 설정 */
@media print {
    header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
    .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr, .stMarkdown { display: none !important; }
    .main .block-container { padding: 0 !important; margin: 0 !important; }
}
</style>
""", unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except Exception:
        st.error("⚠️ 데이터 로드 실패")
        return

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # --- 탭 1: 신청서 작성 (기존 로직 유지) ---
    with tab1:
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date = get_kst().date()
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date)
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
        period_options.append("종례")

        with st.form("request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            with c2: destination = st.text_input("장소 (행선지)", placeholder="예: 병원, 가정")
            reason = st.text_input("상세 사유", placeholder="사유를 입력하세요.")
            time_range = st.select_slider("⏰ 교시 선택 (참고용)", options=period_options)
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                period_str = f"{time_range[0]}~{time_range[1]}" if time_range[0] != time_range[1] else time_range[0]
                new_data = pd.DataFrame([{
                    "일련번호": "-", "신청일시": get_kst().strftime("%m-%d %H:%M"),
                    "이름": user['name'], "번호": user['num'], "종류": cert_type,
                    "시간": f"{target_date.strftime('%m/%d')} ({period_str})", # 신청 시엔 교시 저장
                    "행선지": destination, "사유": reason, "상태": "신청", "승인일시": "-"
                }])
                conn.update(worksheet="발급명부", data=pd.concat([df_log, new_data], ignore_index=True))
                send_discord_notification(f"🔔 [신청] {user['name']} : {cert_type}")
                st.success("신청 완료!"); st.cache_data.clear(); st.rerun()

    # --- 탭 2: 내 내역 확인 및 증명서 보기 ---
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("내역이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status_icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인완료 (번호: {row['일련번호']})")
                        if st.button("📄 증명서 보기 (확인용)", key=f"view_{idx}", use_container_width=True):
                            render_certificate(row, fixed_info)
                    else:
                        st.write(f"상태: {row['상태']}")

def render_certificate(row, fixed_info):
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:48px; margin-left:-35px; margin-top:-10px; opacity:0.8;">'

    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    
    # 교사가 입력한 최종 시간 데이터를 그대로 가져옴
    time_display = row['시간'] 
    
    # 제목 및 문구 설정
    type_map = {"조퇴증": ["조 퇴 증", "조퇴를"], "외출증": ["외 출 증", "외출을"], "교내활동증": ["학생 교내 활동 확인증", "교내활동을"]}
    info = type_map.get(row['종류'], ["증 명 서", "사항을"])

    # 날짜 (현재 날짜 기준)
    now = get_kst()

    full_html = f"""
    <div style="width:500px; margin:10px auto; border:1px solid #000; padding:0; background:white; color:black; font-family:sans-serif;">
        <div style="border-bottom:1px solid #000; background-color:#D9E1F2; padding:15px; text-align:center;">
            <h1 style="margin:0; font-size:35px; letter-spacing:10px; font-weight:bold;">{info[0]}</h1>
        </div>
        <div style="background-color:#D9E1F2; height:40px; border-bottom:1px solid #000; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:bold;">
            {dept}과 &nbsp;&nbsp; {grade}학년 &nbsp;&nbsp; {cls}반 &nbsp;&nbsp; {num}번 &nbsp;&nbsp; 성명 : {row['이름']}
        </div>
        <table style="width:100%; border-collapse:collapse; table-layout:fixed;">
            <tr style="height:60px;">
                <td style="width:20%; border-right:1px solid #000; border-bottom:1px solid #000; background:#f4f4f4; text-align:center; font-weight:bold;">사유</td>
                <td style="width:80%; border-bottom:1px solid #000; padding-left:15px; font-size:16px;">{row['사유']}</td>
            </tr>
            <tr style="height:60px;">
                <td style="border-right:1px solid #000; border-bottom:1px solid #000; background:#f4f4f4; text-align:center; font-weight:bold;">장소</td>
                <td style="border-bottom:1px solid #000; padding-left:15px; font-size:16px;">{row['행선지']}</td>
            </tr>
            <tr style="height:60px;">
                <td style="border-right:1px solid #000; border-bottom:1px solid #000; background:#f4f4f4; text-align:center; font-weight:bold;">시간</td>
                <td style="border-bottom:1px solid #000; text-align:center; font-size:18px; font-weight:bold;">{time_display}</td>
            </tr>
        </table>
        <!-- 표와 하단 텍스트 사이 간격 및 정렬 수정 -->
        <div style="text-align:center; padding:30px 0 20px 0;">
            <div style="font-size:18px; font-weight:bold; margin-bottom:20px;">상기 학생의 {info[1]} 확인함.</div>
            <div style="font-size:17px; margin-bottom:15px;">{now.year} 년 &nbsp;&nbsp; {now.month:02d} 월 &nbsp;&nbsp; {now.day:02d} 일</div>
            <div style="font-size:18px; font-weight:bold; margin-bottom:25px; position:relative;">
                담당교사 : &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp; (인)
                {seal_html}
            </div>
            <div style="border-top:1px solid #000; padding:15px 0; font-size:22px; font-weight:bold; letter-spacing:5px;">
                경 기 기 계 공 업 고 등 학 교
            </div>
        </div>
    </div>
    """
    st.markdown(full_html, unsafe_allow_html=True)
    # 자동 인쇄창 호출(window.print) 코드 삭제함
