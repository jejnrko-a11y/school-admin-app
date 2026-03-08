import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst

def show_page(conn, user, fixed_info):
    # 1. UI 및 인쇄 설정 CSS (들여쓰기 제거로 코드 블록 방지)
    st.markdown("""
<style>
[data-testid="stDataFrame"] { font-size: 12px !important; }
@media print {
    header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
    .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr { display: none !important; }
    .main .block-container { padding: 0 !important; margin: 0 !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
""", unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    st.info("신청 후 담임 선생님의 승인이 완료되면 증명서를 확인하고 출력할 수 있습니다.")
    
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except Exception:
        st.error("⚠️ 구글 시트에 '발급명부' 탭이 없습니다. '발급명부' 탭을 생성해 주세요.")
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
            with c1:
                cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            with c2:
                destination = st.text_input("장소 (행선지)", placeholder="예: 병원, 가정, 과학관")
            
            reason = st.text_input("상세 사유", placeholder="사유를 입력하세요.")

            st.write(f"⏰ **시간 선택**")
            time_range = st.select_slider("범위 선택", options=period_options, value=st.session_state.issuance_slider)
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("장소와 사유를 모두 입력해 주세요.")
                else:
                    period_str = f"{time_range[0]}~{time_range[1]}" if time_range[0] != time_range[1] else time_range[0]
                    new_data = pd.DataFrame([{
                        "일련번호": "-", 
                        "신청일시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user['name'], 
                        "번호": user['num'], 
                        "종류": cert_type,
                        "시간": f"{target_date.strftime('%m/%d')} ({period_str})",
                        "행선지": destination, 
                        "사유": reason, 
                        "상태": "신청", 
                        "승인일시": "-"
                    }])
                    updated_df = pd.concat([df_log, new_data], ignore_index=True)
                    conn.update(worksheet="발급명부", data=updated_df)
                    st.success("신청 완료!")
                    st.cache_data.clear()
                    st.rerun()

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
                        st.success(f"✅ 승인완료 (번호: {row['일련번호']})")
                        if st.button("📄 증명서 보기", key=f"view_{idx}", use_container_width=True):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 반려된 신청입니다.")
                    else:
                        st.warning("⏳ 승인 대기 중입니다.")

# ---------------------------------------------------------
# 공식 양식 렌더링 함수 (통합 양식 고도화)
# ---------------------------------------------------------
def render_certificate(row, fixed_info):
    # 1. 교사 직인 처리
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:46px; margin-left:-35px; margin-top:-10px; opacity:0.8; z-index:10;">'

    # 2. 데이터 매핑 및 명칭 설정
    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    
    # 종류별 제목 및 조사 매핑
    type_info = {
        "조퇴증": {"title": "조 퇴 증", "text": "조퇴를"},
        "외출증": {"title": "외 출 증", "text": "외출을"},
        "교내활동증": {"title": "학생 교내 활동 확인증", "text": "학생 교내 활동 확인을"}
    }
    info = type_info.get(row['종류'], {"title": "확 인 증", "text": "사항을"})
    
    # 시간 파싱
    try:
        date_part = row['시간'].split(' ')[0] # "03/10"
        m, d = date_part.split('/')
        time_detail = row['시간'].split('(')[1].replace(')', '')
        y = str(datetime.now().year)
    except:
        y, m, d, time_detail = "2026", "  ", "  ", row['시간']

    # 3. HTML 양식 (요구사항 반영: 높이 통일, 괄호 제거, 조사 수정)
    full_html = f"""
<div style="width:480px; margin:20px auto; border:2.5px solid black; padding:0; background:white; color:black; font-family:'Malgun Gothic', 'Dotum', sans-serif;">
<div style="border-bottom:2px solid black; background-color:#D9E1F2; padding:12px; text-align:center;">
<h2 style="margin:0; font-size:22px; letter-spacing:5px;">{info['title']}</h2>
</div>
<div style="background-color:#E7E6E6; height:45px; border-bottom:1.5px solid black; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:bold; letter-spacing:1px;">
{dept}과 &nbsp; {grade}학년 &nbsp; {cls}반 &nbsp; {num}번 &nbsp; 성명 : {name}
</div>
<table style="width:100%; border-collapse:collapse;">
<tr style="height:60px;">
<td style="width:18%; border:1px solid black; border-top:none; background:#f0f0f0; text-align:center; font-weight:bold; font-size:16px;">사 유</td>
<td style="width:82%; border:1px solid black; border-top:none; padding:10px; text-align:left; vertical-align:middle; font-size:16px;">{row['사유']}</td>
</tr>
<tr style="height:60px;">
<td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:16px;">장소</td>
<td style="border:1px solid black; padding-left:15px; text-align:left; vertical-align:middle; font-size:16px;">{row['행선지']}</td>
</tr>
<tr style="height:60px;">
<td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:16px;">시간</td>
<td style="border:1px solid black; text-align:center; vertical-align:middle; font-size:17px; letter-spacing:1px;">{time_detail}</td>
</tr>
</table>
<div style="text-align:center; padding:35px 0 0 0;">
<div style="font-size:18px; font-weight:bold; margin-bottom:25px;">상기 학생의 {info['text']} 확인함.</div>
<div style="font-size:18px; margin-bottom:22px; letter-spacing:2px;">{y} 년 &nbsp;&nbsp;&nbsp; {m} 월 &nbsp;&nbsp;&nbsp; {d} 일</div>
<div style="font-size:18px; font-weight:bold; margin-bottom:28px; position:relative;">
담당교사 : &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인)
{seal_html}
</div>
<div style="border-top:2px solid black; padding:15px 0; font-size:24px; font-weight:bold; letter-spacing:6px; background-color:white;">
경 기 기 계 공 업 고 등 학 교
</div>
</div>
</div>
"""
    
    st.markdown("### 🖨️ 증명서 미리보기")
    st.markdown(full_html, unsafe_allow_html=True)
    
    # 브라우저 인쇄창 호출
    components.html(f"<script>window.parent.print();</script>", height=0)
