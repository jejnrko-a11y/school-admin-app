import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst, send_discord_notification

def show_page(conn, user, fixed_info):
    # 1. UI 및 인쇄 설정 CSS
    st.markdown("""
<style>
[data-testid="stDataFrame"] { font-size: 12px !important; }
@media print {
    header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
    .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr, .stMarkdown { display: none !important; }
    h3 { display: none !important; }
    .main .block-container { padding: 0 !important; margin: 0 !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
""", unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    
    # 데이터 로드
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
        # 반려사유 컬럼이 없을 경우 대비
        if "반려사유" not in df_log.columns:
            df_log["반려사유"] = ""
    except Exception:
        st.error("⚠️ '발급명부' 탭을 찾을 수 없습니다.")
        return

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # --- 탭 1: 신청서 작성 ---
    with tab1:
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date = get_kst().date()
            
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date)
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
        period_options.append("종례")

        if target_date != st.session_state.issuance_date:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])
            st.session_state.issuance_date = target_date

        if 'issuance_slider' not in st.session_state:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])

        with st.form("request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1: cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            with c2: destination = st.text_input("장소 (행선지)", placeholder="예: 병원, 가정, 과학관")
            reason = st.text_input("상세 사유", placeholder="사유를 입력하세요.")

            st.write(f"⏰ **{target_date.strftime('%m/%d')} 교시 선택**")
            selected_range = st.select_slider("드래그하여 범위를 선택하세요", options=period_options, value=st.session_state.issuance_slider)
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("장소와 사유를 모두 입력해 주세요.")
                else:
                    p_str = f"{selected_range[0]}~{selected_range[1]}" if selected_range[0] != selected_range[1] else selected_range[0]
                    new_data = pd.DataFrame([{
                        "일련번호": "-", "신청일시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user['name'], "번호": user['num'], "종류": cert_type,
                        "시간": f"{target_date.strftime('%m/%d')} ({p_str})",
                        "행선지": destination, "사유": reason, "상태": "신청", "승인일시": "-", "반려사유": ""
                    }])
                    conn.update(worksheet="발급명부", data=pd.concat([df_log, new_data], ignore_index=True))
                    send_discord_notification(f"🔔 [신청] {user['name']} : {cert_type} ({reason})")
                    st.success("신청 완료!"); st.cache_data.clear(); st.rerun()

    # --- 탭 2: 내 내역 확인 ---
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("신청 내역이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status_icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인완료 (일련번호: {row['일련번호']})")
                        if st.button("📄 증명서 보기", key=f"view_{idx}", use_container_width=True):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error(f"❌ 반려됨")
                        st.info(f"🚩 **선생님 반려 사유:** {row['반려사유'] if row['반려사유'] else '사유 없음'}")
                    else:
                        st.write("⏳ 선생님의 승인을 기다리고 있습니다.")

# ---------------------------------------------------------
# 공식 양식 렌더링 함수 (크기 60% 축소 버전)
# ---------------------------------------------------------
def render_certificate(row, fixed_info):
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            # 직인 크기도 같이 축소 (48px -> 32px)
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:32px; margin-left:-25px; margin-top:-8px; opacity:0.8; z-index:10;">'

    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    
    type_map = {
        "조퇴증": {"title": "조 퇴 증", "text": "조퇴를", "header": "조퇴"},
        "외출증": {"title": "외 출 증", "text": "외출을", "header": "외출"},
        "교내활동증": {"title": "학생 교내 활동 확인증", "text": "학생 교내 활동 확인을", "header": "학생 교내 활동 확인"}
    }
    info = type_map.get(row['종류'], {"title": "확 인 증", "text": "사항을", "header": "증명서"})
    now = get_kst()

    # 전체 너비를 500px -> 320px로 축소 (약 60%) 및 폰트 사이즈 조정
    full_html = f"""
<div style="width:320px; margin:10px auto; border:1px solid black; padding:0; background:white; color:black; font-family:'Malgun Gothic', sans-serif; line-height:1.2;">
<div style="border-bottom:1px solid black; background-color:#D9E1F2; padding:8px; text-align:center;">
<h1 style="margin:0; font-size:24px; letter-spacing:6px; font-weight:bold;">{info['title']}</h1>
</div>
<div style="background-color:#D9E1F2; height:30px; border-bottom:1px solid black; display:flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold;">
{dept}과 &nbsp; {grade}학년 &nbsp; {cls}반 &nbsp; {num}번 &nbsp; 성명 : {name}
</div>
<table style="width:100%; border-collapse:collapse; table-layout:fixed; border:none;">
<tr style="height:40px;">
<td style="width:20%; border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:11px;">사 유</td>
<td style="width:80%; border-bottom:1px solid black; padding:4px 8px; text-align:left; vertical-align:middle; font-size:11px;">{str(row['사유']).replace('nan', '')}</td>
</tr>
<tr style="height:40px;">
<td style="border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:11px;">장소</td>
<td style="border-bottom:1px solid black; padding:4px 8px; text-align:left; vertical-align:middle; font-size:11px;">{str(row['행선지']).replace('nan', '')}</td>
</tr>
<tr style="height:40px;">
<td style="border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:11px;">시간</td>
<td style="border-bottom:1px solid black; padding:4px 8px; text-align:center; vertical-align:middle; font-size:12px; font-weight:bold;">{row['시간']}</td>
</tr>
</table>
<div style="text-align:center; padding:15px 0 10px 0;">
<div style="font-size:12px; font-weight:bold; margin-bottom:12px;">상기 학생의 {info['text']} 확인함.</div>
<div style="font-size:11px; margin-bottom:10px;">{now.year} 년 &nbsp;&nbsp; {now.month:02d} 월 &nbsp;&nbsp; {now.day:02d} 일</div>
<div style="font-size:12px; font-weight:bold; margin-bottom:15px; position:relative;">
담당교사 : &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp; (인)
{seal_html}
</div>
<div style="border-top:1px solid black; padding:8px 0; font-size:15px; font-weight:bold; letter-spacing:4px;">
경 기 기 계 공 업 고 등 학 교
</div>
</div>
</div>
"""
    st.markdown(f"### 🖨️ {info['header']} 증명서 확인")
    st.markdown(full_html, unsafe_allow_html=True)
