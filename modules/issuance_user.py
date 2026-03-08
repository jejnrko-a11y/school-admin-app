import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst

def show_page(conn, user, fixed_info):
    # CSS 설정 (인쇄 및 UI)
    st.markdown("""
        <style>
        [data-testid="stDataFrame"] { font-size: 12px !important; }
        @media print {
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
            .stButton, .no-print, [data-testid="stForm"], .stTabs [role="tablist"] { display: none !important; }
            .cert-container { border: 2px solid #000 !important; padding: 40px !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📜조퇴/외출/교내활동증 신청")
    
    # 데이터 로드 (에러 방지 처리)
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except Exception:
        st.error("⚠️ 구글 시트에 '발급명부' 탭이 없습니다. 시트에 '발급명부' 이름의 탭을 생성해 주세요.")
        return

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # --- 탭 1: 신청서 작성 ---
    with tab1:
        # [출석체크 로직 반영] 날짜를 폼 외부로 빼서 슬라이더가 즉시 반응하게 함
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date = get_kst().date()
            
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date, key="date_picker")

        # 요일별 교시 로직 (화요일 감지)
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
                destination = st.text_input("행선지(장소)", placeholder="예: 병원, 가정, 과학관")
            
            reason = st.text_input("상세 사유", placeholder="예: 독감으로 인한 병원 진료 등")

            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][weekday]}) 교시 선택**")
            time_range = st.select_slider(
                "드래그하여 범위를 선택하세요", 
                options=period_options, 
                value=st.session_state.issuance_slider
            )
            
            if st.form_submit_button("🚀 신청서 제출", use_container_width=True):
                if not destination or not reason:
                    st.error("행선지와 사유를 모두 입력해 주세요.")
                else:
                    # 데이터 정리
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
                        st.success("신청되었습니다! 교사용 메뉴에서 승인 후 인쇄 가능합니다.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f"데이터 저장 실패: {e}")

    # --- 탭 2: 내 내역 확인 및 인쇄 ---
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("신청 내역이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status_icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
                    st.write(f"**시간:** {row['시간']} | **행선지:** {row['행선지']}")
                    st.write(f"**사유:** {row['사유']}")
                    
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인번호: {row['일련번호']} (승인일시: {row['승인일시']})")
                        if st.button("🖨️ 증명서 보기/인쇄", key=f"print_{idx}"):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 이 신청은 반려되었습니다. 선생님께 사유를 문의하세요.")

import base64
import os

def render_certificate(row, fixed_info):
    # 1. 직인 이미지 처리 (Base64 변환하여 HTML 삽입)
    seal_path = "teacher_seal.png"
    seal_base64 = ""
    if os.path.exists(seal_path):
        with open(seal_path, "rb") as f:
            seal_base64 = base64.b64encode(f.read()).decode()
    
    # 2. 날짜 데이터 파싱 (2026-03-08 -> 2026, 03, 08)
    # row['시간']에 포함된 날짜나 신청일시를 기준으로 추출
    try:
        current_date = datetime.strptime(row['신청일시'].split(' ')[0], "%m-%d")
        year = "2026" # 현재 연도
        month = current_date.strftime("%m")
        day = current_date.strftime("%d")
    except:
        year, month, day = "20  ", "  ", "  "

    # 3. 양식 선택 및 제목 설정
    is_activity = row['종류'] == "교내활동증"
    title = "학 생 교 내 활 동 확 인 증" if is_activity else "조 퇴, 외 출 증"
    confirm_text = "상기학생의 교내활동을 확인함." if is_activity else "상기학생의 조퇴, 외출을 허가함."
    teacher_label = "담당교사 :" if is_activity else "담임 :"

    # 4. HTML/CSS 레이아웃 (A4 가로 최적화)
    html_layout = f"""
    <style>
        @media print {{
            @page {{ size: A4 landscape; margin: 10mm; }}
            body {{ margin: 0; padding: 0; }}
            .no-print {{ display: none !important; }}
        }}
        .cert-wrapper {{
            width: 140mm; /* A4 가로의 절반 정도 크기 */
            margin: 0 auto;
            padding: 10px;
            font-family: 'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;
            color: black;
            border: 1px solid #eee;
        }}
        .cert-table {{
            width: 100%;
            border-collapse: collapse;
            border: 2px solid black;
        }}
        .cert-table th, .cert-table td {{
            border: 1px solid black;
            height: 40px;
            text-align: center;
            font-size: 14px;
        }}
        .title-box {{
            background-color: #e8eefc;
            font-size: 22px !important;
            font-weight: bold;
            height: 50px !important;
        }}
        .info-header {{
            background-color: #e8eefc;
            height: 35px !important;
        }}
        .label-cell {{
            background-color: white;
            width: 80px;
            font-weight: bold;
        }}
        .content-cell {{
            text-align: left;
            padding-left: 10px;
        }}
        .footer-section {{
            margin-top: 15px;
            text-align: center;
        }}
        .school-name {{
            font-size: 24px;
            font-weight: bold;
            letter-spacing: 10px;
            margin-top: 20px;
        }}
        .seal-container {{
            position: relative;
            display: inline-block;
        }}
        .seal-img {{
            position: absolute;
            top: -20px;
            right: -40px;
            width: 50px;
            opacity: 0.8;
        }}
    </style>

    <div class="cert-wrapper">
        <table class="cert-table">
            <tr>
                <th colspan="10" class="title-box">{title}</th>
            </tr>
            <tr class="info-header">
                <td colspan="2">과</td>
                <td colspan="2">학년</td>
                <td colspan="2">반</td>
                <td colspan="2">번</td>
                <td colspan="2">성명:</td>
            </tr>
            <tr>
                <td colspan="2" style="font-size:12px;">{fixed_info.get('dept', '기계과')}</td>
                <td colspan="2">{fixed_info.get('grade', '-')}</td>
                <td colspan="2">{fixed_info.get('cls', '-')}</td>
                <td colspan="2">{row['번호']}</td>
                <td colspan="2">{row['이름']}</td>
            </tr>
            
            {"" if is_activity else ""}
            {f'''
            <tr>
                <td rowspan="2" class="label-cell">교내<br>활동<br>사유</td>
                <td colspan="9" rowspan="2" class="content-cell">{row['사유']}</td>
            </tr>
            <tr style="display:none;"></tr>
            <tr>
                <td class="label-cell">장소</td>
                <td colspan="9" class="content-cell">{row['행선지']}</td>
            </tr>
            ''' if is_activity else f'''
            <tr>
                <td rowspan="3" class="label-cell">사 유</td>
                <td colspan="9" rowspan="3" class="content-cell">{row['사유']}</td>
            </tr>
            <tr style="display:none;"></tr><tr style="display:none;"></tr>
            '''}
            
            <tr>
                <td class="label-cell">시간</td>
                <td colspan="9" class="content-cell">
                    {row['시간']} ( 시 분 ~ 시 분 )
                </td>
            </tr>
        </table>

        <div class="footer-section">
            <p style="font-size: 16px; margin-bottom: 25px;">{confirm_text}</p>
            <p style="font-size: 16px; letter-spacing: 5px;">20{year} 년 &nbsp;&nbsp;&nbsp;&nbsp; {month} 월 &nbsp;&nbsp;&nbsp;&nbsp; {day} 일</p>
            
            <div style="margin-top: 25px; font-size: 16px; text-align: right; padding-right: 50px;">
                <span class="seal-container">
                    {teacher_label} **오정은** (인)
                    {f'<img src="data:image/png;base64,{seal_base64}" class="seal-img">' if seal_base64 else ''}
                </span>
            </div>
            
            <div class="school-name">경 기 기 계 공 업 고 등 학 교</div>
        </div>
    </div>
    """
    
    st.markdown(html_layout, unsafe_allow_html=True)
    # 인쇄 스크립트 실행
    components.html("<script>window.parent.print();</script>", height=0)
