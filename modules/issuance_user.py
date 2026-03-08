import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst

def show_page(conn, user, fixed_info):
    # ==========================================
    # 1. UI 및 인쇄 설정 CSS
    # ==========================================
    st.markdown("""
        <style>
        /* 화면용 표 글자 크기 */
        [data-testid="stDataFrame"] { font-size: 12px !important; }
        
        /* 인쇄 최적화 설정 */
        @media print {
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { 
                display: none !important; 
            }
            .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr, .stMarkdown { 
                display: none !important; 
            }
            /* 인쇄 시 미리보기 영역만 표시 */
            .print-area { display: block !important; }
            .main .block-container { padding: 0 !important; margin: 0 !important; }
            /* 배경색 및 이미지 강제 출력 */
            * { -webkit-print-color-adjust: exact !important; print-color-adjust: exact !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    st.info("신청서를 작성하고 담임 선생님의 승인이 완료되면 '내 신청 내역'에서 증명서를 출력할 수 있습니다.")
    
    # 데이터 로드
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except Exception:
        st.error("⚠️ 구글 시트에 '발급명부' 탭이 없습니다. 시트에 '발급명부' 이름의 탭을 먼저 생성해 주세요.")
        return

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # ---------------------------------------------------------
    # PART 1: 신규 신청서 작성
    # ---------------------------------------------------------
    with tab1:
        # 날짜 선택 (폼 외부 배치하여 교시 슬라이더 즉시 업데이트)
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date = get_kst().date()
            
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date)

        # 요일별 교시 로직 (화요일 7교시 감지)
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
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
                destination = st.text_input("행선지(또는 장소)", placeholder="예: 병원, 가정, 과학실 등")
            
            reason = st.text_input("상세 사유", placeholder="사유를 상세히 입력해 주세요.")

            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][weekday]}) 시간 선택**")
            time_range = st.select_slider(
                "드래그하여 시작/종료 범위를 선택하세요", 
                options=period_options, 
                value=st.session_state.issuance_slider
            )
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("행선지(장소)와 사유를 모두 입력해 주세요.")
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
                    
                    try:
                        updated_df = pd.concat([df_log, new_data], ignore_index=True)
                        conn.update(worksheet="발급명부", data=updated_df)
                        st.success("✅ 신청이 완료되었습니다! [내 신청 내역] 탭에서 상태를 확인하세요.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"데이터 저장 실패: {e}")

    # ---------------------------------------------------------
    # PART 2: 내 내역 확인 및 인쇄
    # ---------------------------------------------------------
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("신청 내역이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status_icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
                    st.write(f"**시간:** {row['시간']} | **장소/행선지:** {row['행선지']}")
                    st.write(f"**사유:** {row['사유']}")
                    
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인완료 (번호: {row['일련번호']})")
                        if st.button("🖨️ 증명서 보기/인쇄", key=f"print_{idx}"):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 담임 선생님께서 신청을 반려하셨습니다.")

# ---------------------------------------------------------
# PART 3: 공식 양식 렌더링 함수
# ---------------------------------------------------------
def render_certificate(row, fixed_info):
    # 1. 교사 직인 이미지 처리 (teacher_seal.png 로드)
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:46px; margin-left:-35px; margin-top:-10px; opacity:0.8; z-index:10;">'

    # 2. 데이터 정리 및 날짜 파싱
    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    
    try:
        date_part = row['시간'].split(' ')[0] # "MM/DD"
        m, d = date_part.split('/')
        y = str(datetime.now().year)
    except:
        y, m, d = "2026", "  ", "  "

    # 3. 종류별 HTML 구조 (이미지 양식 완벽 재현)
    if row['종류'] == "교내활동증":
        title = "학 생 교 내 활 동 확 인 증"
        teacher_label = "담당교사 :"
        content_table = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:40px; border-bottom:1.5px solid black;">
                <td colspan="2" style="text-align:center; font-size:17px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:90px;">
                <td style="width:18%; border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; line-height:1.3; font-size:15px;">교내<br>활동<br>사유</td>
                <td style="width:82%; border:1px solid black; padding:10px; text-align:left; vertical-align:top; font-size:16px;">{row['사유']}</td>
            </tr>
            <tr style="height:50px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:15px;">장소</td>
                <td style="border:1px solid black; padding-left:15px; text-align:left; font-size:16px;">{row['행선지']}</td>
            </tr>
            <tr style="height:50px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:15px;">시간</td>
                <td style="border:1px solid black; text-align:center; font-size:18px; letter-spacing:1px;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:35px; font-size:19px; font-weight:bold;">상기 학생의 교내활동을 확인함.</div>
        """
    else:
        title = "조 퇴 ,  외 출 증"
        teacher_label = "담 임 :"
        content_table = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:40px; border-bottom:1.5px solid black;">
                <td colspan="2" style="text-align:center; font-size:17px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:120px;">
                <td style="width:18%; border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:19px; letter-spacing:5px;">사유</td>
                <td style="width:82%; border:1px solid black; padding:15px; text-align:left; vertical-align:top; font-size:18px;">
                    {row['사유']} <br><br> <span style="font-size:15px; color:#333;">(행선지: {row['행선지']})</span>
                </td>
            </tr>
            <tr style="height:50px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:19px; letter-spacing:5px;">시간</td>
                <td style="border:1px solid black; text-align:center; font-size:18px;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:35px; font-size:19px; font-weight:bold;">상기 학생의 조퇴, 외출을 허가함.</div>
        """

    # 4. 전체 디자인 결합
    full_html = f"""
    <div class="print-area" style="width:500px; margin:20px auto; border:2.5px solid black; padding:0; background:white; color:black; font-family:'Malgun Gothic', 'Dotum', sans-serif;">
        <!-- 파란색 헤더 -->
        <div style="border-bottom:2px solid black; background-color:#D9E1F2; padding:12px; text-align:center;">
            <h2 style="margin:0; font-size:24px; letter-spacing:5px;">{title}</h2>
        </div>
        
        <!-- 중앙 테이블 -->
        <div style="padding:0px;">
            {content_table}
        </div>

        <!-- 하단 섹션 -->
        <div style="text-align:center; padding:30px 0 0 0;">
            <div style="font-size:20px; margin-bottom:20px; letter-spacing:3px;">
                {y} 년 &nbsp;&nbsp;&nbsp; {m} 월 &nbsp;&nbsp;&nbsp; {d} 일
            </div>
            <div style="font-size:20px; font-weight:bold; margin-bottom:30px; position:relative;">
                {teacher_label} &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인)
                {seal_html}
            </div>
            <div style="border-top:2px solid black; padding:15px 0; font-size:25px; font-weight:bold; letter-spacing:8px; background-color:white;">
                경 기 기 계 공 업 고 등 학 교
            </div>
        </div>
    </div>
    """
    
    # 미리보기 렌더링
    st.markdown("### 🖨️ 증명서 미리보기")
    st.markdown(full_html, unsafe_allow_html=True)
    
    # 브라우저 인쇄 창 호출
    components.html(f"<script>window.parent.print();</script>", height=0)
