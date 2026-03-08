import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst, send_discord_notification

def show_page(conn, user, fixed_info):
    # 1. UI 및 화면 레이아웃 설정 CSS
    st.markdown("""
<style>
[data-testid="stDataFrame"] { font-size: 12px !important; }
/* 인쇄 시 불필요한 요소 숨김 (수동 인쇄 대비) */
@media print {
    header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
    .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr, .stMarkdown { display: none !important; }
    .main .block-container { padding: 0 !important; margin: 0 !important; }
    * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
}
</style>
""", unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    st.info("신청 후 담임 선생님이 승인(시간 확정)을 완료하면 증명서를 확인할 수 있습니다.")
    
    # 데이터 로드
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

        # 요일별 교시 옵션 설정
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: # 화요일
            period_options.append("7교시")
        period_options.append("종례")

        # 날짜 변경 시 슬라이더 초기화
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

            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][weekday]}) 교시 선택**")
            selected_range = st.select_slider(
                "드래그하여 시작/종료 교시를 선택하세요", 
                options=period_options, 
                value=st.session_state.issuance_slider
            )
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("장소와 사유를 모두 입력해 주세요.")
                else:
                    # 범위 텍스트 생성
                    p_str = f"{selected_range[0]}~{selected_range[1]}" if selected_range[0] != selected_range[1] else selected_range[0]
                    
                    new_data = pd.DataFrame([{
                        "일련번호": "-", 
                        "신청일시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user['name'], 
                        "번호": user['num'], 
                        "종류": cert_type,
                        "시간": f"{target_date.strftime('%m/%d')} ({p_str})",
                        "행선지": destination, 
                        "사유": reason, 
                        "상태": "신청", 
                        "승인일시": "-"
                    }])
                    
                    # 데이터 저장 및 알림
                    updated_df = pd.concat([df_log, new_data], ignore_index=True)
                    conn.update(worksheet="발급명부", data=updated_df)
                    
                    send_discord_notification(f"🔔 [신청] {user['name']} 학생 : {cert_type} (사유: {reason})")
                    
                    st.success("신청이 완료되었습니다!")
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
                        st.success(f"✅ 승인완료 (일련번호: {row['일련번호']})")
                        if st.button("📄 증명서 보기", key=f"view_{idx}", use_container_width=True):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 반려된 신청입니다.")
                    else:
                        st.write("⏳ 선생님의 승인을 기다리고 있습니다.")

# ---------------------------------------------------------
# 공식 양식 렌더링 함수 (통합 디자인)
# ---------------------------------------------------------
def render_certificate(row, fixed_info):
    # 1. 교사 직인 이미지 처리
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:48px; margin-left:-35px; margin-top:-10px; opacity:0.8; z-index:10;">'

    # 2. 데이터 매핑 및 문구 설정
    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    
    # 종류별 텍스트 매핑 (제목, 내용 조사, UI용 제목)
    type_map = {
        "조퇴증": {"title": "조 퇴 증", "text": "조퇴를", "header": "조퇴"},
        "외출증": {"title": "외 출 증", "text": "외출을", "header": "외출"},
        "교내활동증": {"title": "학생 교내 활동 확인증", "text": "학생 교내 활동 확인을", "header": "학생 교내 활동 확인"}
    }
    info = type_map.get(row['종류'], {"title": "확 인 증", "text": "사항을", "header": "증명서"})

    # 날짜 (현재 기준)
    now = get_kst()

    # 3. HTML 양식 (상단 2줄 하늘색, 1px 실선, 65px 높이 통일)
    full_html = f"""
<div style="width:500px; margin:20px auto; border:1px solid black; padding:0; background:white; color:black; font-family:'Malgun Gothic', sans-serif;">
    <!-- 첫 번째 줄: 제목 -->
    <div style="border-bottom:1px solid black; background-color:#D9E1F2; padding:15px; text-align:center;">
        <h1 style="margin:0; font-size:40px; letter-spacing:10px; font-weight:bold;">{info['title']}</h1>
    </div>
    
    <!-- 두 번째 줄: 학생 정보 -->
    <div style="background-color:#D9E1F2; height:45px; border-bottom:1px solid black; display:flex; align-items:center; justify-content:center; font-size:16px; font-weight:bold;">
        {dept}과 &nbsp;&nbsp; {grade}학년 &nbsp;&nbsp; {cls}반 &nbsp;&nbsp; {num}번 &nbsp;&nbsp; 성명 : {name}
    </div>
    
    <!-- 본문 테이블 (실선 1px, 높이 65px 고정) -->
    <table style="width:100%; border-collapse:collapse; table-layout:fixed; border:none;">
        <tr style="height:65px;">
            <td style="width:20%; border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:17px;">사 유</td>
            <td style="width:80%; border-bottom:1px solid black; padding:0 15px; text-align:left; vertical-align:middle; font-size:17px;">{str(row['사유']).replace('nan', '')}</td>
        </tr>
        <tr style="height:65px;">
            <td style="border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:17px;">장소</td>
            <td style="border-bottom:1px solid black; padding:0 15px; text-align:left; vertical-align:middle; font-size:17px;">{str(row['행선지']).replace('nan', '')}</td>
        </tr>
        <tr style="height:65px;">
            <td style="border-right:1px solid black; border-bottom:1px solid black; background:#f4f4f4; text-align:center; font-weight:bold; font-size:17px;">시간</td>
            <td style="border-bottom:1px solid black; padding:0 15px; text-align:center; vertical-align:middle; font-size:19px; font-weight:bold;">{row['시간']}</td>
        </tr>
    </table>

    <!-- 하단 확인 섹션 -->
    <div style="text-align:center; padding:35px 0 20px 0;">
        <div style="font-size:19px; font-weight:bold; margin-bottom:25px;">상기 학생의 {info['text']} 확인함.</div>
        <div style="font-size:18px; margin-bottom:15px;">{now.year} 년 &nbsp;&nbsp; {now.month:02d} 월 &nbsp;&nbsp; {now.day:02d} 일</div>
        <div style="font-size:19px; font-weight:bold; margin-bottom:25px; position:relative;">
            담당교사 : &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인)
            {seal_html}
        </div>
        <div style="border-top:1px solid black; padding:15px 0; font-size:24px; font-weight:bold; letter-spacing:8px;">
            경 기 기 계 공 업 고 등 학 교
        </div>
    </div>
</div>
"""
    
    # 미리보기 상단 제목 설정
    st.markdown(f"### 🖨️ {info['header']} 증명서")
    st.markdown(full_html, unsafe_allow_html=True)
