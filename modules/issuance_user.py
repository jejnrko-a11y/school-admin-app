import streamlit as st
import pandas as pd
6교시"]
        if weekday == 1: period_options.append("7교시")
        from datetime import datetime
import streamlit.components.v1 as components
import base64
import os
from utils import get_kst

def show_page(conn, user, fixed_info):
    # ==========================================
period_options.append("종례")

        # 날짜 변경 시 슬라이더 초기화
        if target_date != st.session_state.issuance_date:
            st.session_state.iss    # 1. UI 및 인쇄 설정 CSS
    # ==========================================
    st.markdown("""
        <style>
        [data-testid="stDataFrame"] { font-size: 12px !important;uance_slider = (period_options[0], period_options[-1])
            st.session_state.issuance_date = target_date

        if 'issuance_slider' not in st.session_ }
        @media print {
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer { display: none !important; }
            .stButton, .no-print, [state:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])

        with st.form("request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cert_typedata-testid="stForm"], .stTabs [role="tablist"], .stInfo, .stTitle, hr { 
                display: none !important; 
            }
            .main .block-container { padding:  = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동0 !important; margin: 0 !important; }
            /* 인쇄 시 배경색과 이미지가 보이증"])
            with c2:
                destination = st.text_input("행선지(또는 장소)",도록 설정 */
            * { -webkit-print-color-adjust: exact !important; print-color- placeholder="예: 병원, 가정, 과학실 등")
            
            reason = st.text_input("상세adjust: exact !important; }
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📜 조퇴/외출/교내활동증 신청")
    st.info 사유", placeholder="상세한 사유를 적어주세요.")

            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토("신청 후 담임 선생님의 승인이 완료되면 증명서를 출력할 수 있습니다.")
    
    #','일'][weekday]}) 교시 선택**")
            time_range = st.select_slider(
                "드래그하여 시작/종료 범위를 선택하세요", 
                options=period_options, 
                 데이터 로드
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except Exception:
        st.error("⚠️ 구글 시트에 '발급명value=st.session_state.issuance_slider
            )
            
            if st.form_submit_button("🚀 신청서 제출", use_container_width=True):
                if not destination or not reason:
                    st.error("행선지(장소)와 사유를 모두 입력해 주세요.")부' 탭이 없습니다. 시트에 '발급명부' 이름의 탭을 먼저 생성해 주세요.")
                else:
                    period_str = f"{time_range[0]}~{time_range[1]}" if time_range[0] != time_range[1] else time_range[0]

        return

    tab1, tab2 = st.tabs(["✍️ 신규 신청", "📂 내 신청 내역"])

    # --- 탭 1: 신청서 작성 ---
    with tab1:
                    new_data = pd.DataFrame([{
                        "일련번호": "-", 
                        "신청일        # 날짜 선택 (폼 외부 배치하여 슬라이더 즉시 갱신)
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user[' = get_kst().date()
            
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date)

        # 요일별 교시 로직 (화요일 7교시 감지)
        weekday = target_date.weekday()
        periodname'], 
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
                        conn_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.update(worksheet="발급명부", data=updated_df)
                        st.success("신.append("7교시")
        period_options.append("종례")

        # 날짜 변경 시 슬라이더 초기화
        if target_date != st.session_state.issuance_date:
청 완료! 교사 승인 후 '내 신청 내역'에서 인쇄가 가능합니다.")
                        st.cache_data.clear()
                        st.rerun()
                    except Exception as e:
                        st.error(f            st.session_state.issuance_slider = (period_options[0], period_options[-1"저장 실패: {e}")

    # --- 탭 2: 내 내역 확인 및 인쇄 ---
    ])
            st.session_state.issuance_date = target_date

        if 'issuance_with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시", ascending=False)
        if my_log.empty:
            st.info("신청 내역이 없습니다.")
        else:
            for idx,slider' not in st.session_state:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])

        with st.form("request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with row in my_log.iterrows():
                status_icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청 c1:
                cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            with c2:
                destination = st.text_input("행선지(또는 장소)", placeholder="예: 병원, 가정, 과학관 2층")
일시']} - {row['종류']}"):
                    st.write(f"**시간:** {row['시간']} | **장소/행선지:** {row['행선지']}")
                    st.write(f"**사유:** {row['사유']}")
                    
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인완료 (번호: {row['일련번호']})")
                        if st.button("🖨️ 증명서 보기 및 인쇄", key=f"btn            
            reason = st.text_input("상세 사유", placeholder="예: 독감 증상으로 인한 진료, 귀가 등")

            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][weekday]}) 교시 선택**")
            time_range = st.select_slider(
                "드래그하여 시간을 선택하세요", 
                options=period_options, 
                value=st.session_state.issuance__{idx}"):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 반려된 신청입니다.")

def render_certificate(row,slider
            )
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("행선지와 사유를 모두 입력해 주세요.")
                else:
                    period_str = f"{time_range[0]} fixed_info):
    # 1. 교사 직인 이미지 처리
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f~{time_range[1]}" if time_range[0] != time_range[1] else time_range[0]
                    new_data = pd.DataFrame([{
                        "일련번호": "-", .read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:48px; margin-left:-
                        "신청일시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user['name'], 
                        "번호": user['num'], 
                        "종류38px; margin-top:-12px; opacity:0.8;">'

    # 2. 고정 정보 및 날짜 추출
    dept = str(fixed_info.get('dept', '미정')).replace('.0": cert_type,
                        "시간": f"{target_date.strftime('%m/%d')} ({period_str})",
                        "행선지": destination, 
                        "사유": reason, 
                        "상태": "신청", 
                        "승인일시": "-"
                    }])
                    ', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
                    updated_df = pd.concat([df_log, new_data], ignore_index=True)
                    updated
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    _df = updated_df.sort_values(by=['신청일시'], ascending=True) # 최신이 아래로
                    conn.update(worksheet="발급명부", data=updated_df)
                    st.success("신청 완료! [내 신청 내역] 탭에서 승인 여부를 확인하세요.")
    try:
        date_part = row['시간'].split(' ')[0] # "MM/DD"
        m, d = date_part.split('/')
        y = str(datetime.now().year)[2:] # "26"
    except:
        y, m, d = "20  ", "  ",
                    st.cache_data.clear()
                    st.rerun()

    # --- 탭 2: 내 내역 확인 및 인쇄 ---
    with tab2:
        my_log = df_log[df_log['이름'] == user['name']].sort_values(by="신청일시 "  "

    # 3. 종류별 양식 분기
    if row['종류'] ==", ascending=False)
        if my_log.empty:
            st.info("신청 내역 "교내활동증":
        title = "학 생 교 내 활 동 확 인 증"
        table이 없습니다.")
        else:
            for idx, row in my_log.iterrows():
                status__html = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:38px; border-bottom:1.5px solid black;">
                <td colspan="icon = {"신청": "🔵", "승인": "🟢", "반려": "🔴"}.get(row['상태'], "⚪")
                with st.expander(f"{status_icon} [{row['상태']}] {row['신청일시']} - {row['종류']}"):
2" style="text-align:center; font-size:16px; font-weight:bold; letter-spacing:1px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &                    st.write(f"**시간:** {row['시간']} | **행선지:** {row['행선지']}")
                    st.write(f"**사유:** {row['사유']}")
                    
                    if row['상태'] == "승인":
                        st.success(f"✅ 승인완료 (번호nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:90px;">
                <td style: {row['일련번호']})")
                        if st.button("🖨️ 증명="width:18%; border:1px solid black; background:#F2F2F2; text-align:center; font-weight:bold;">교내<br>활동<br>사유</td>
                <td style="width:82%; border:1px solid black; padding:10px; text-align서 보기 및 인쇄", key=f"print_{idx}"):
                            render_certificate(row, fixed_info)
                    elif row['상태'] == "반려":
                        st.error("❌ 이 신청은 반려되었습니다.")

def render_certificate(row, fixed_info):
    # 1. 교사 직인 이미지 처리:left; vertical-align:top;">{row['사유']}</td>
            </tr>
            <tr style="height:45px;">
                <td style="border:1px solid black; background:#F2 (Base64 인코딩)
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
F2F2; text-align:center; font-weight:bold;">장소</td>
                <td style="border:1px solid black; padding-left:10px; text-align:left;">{row['행선지']}</td>
            </tr>
            <tr style="height:45px;">
                            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64<td style="border:1px solid black; background:#F2F2F2; text-align:center; font-weight:bold;">시간</td>
                <td style="border:1px solid black; text}" style="position:absolute; width:48px; margin-left:-35px; margin-top:-12px; opacity:0.8; z-index:10;">'

    # 2. 고정 데이터-align:center; font-size:17px;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
 정리
    dept = str(fixed_info.get('dept', '미상')).replace('.0', '')
    grade = str(fixed_info.get('grade', '0')).replace('.0', '')
    cls = str(fixed_info.get('cls', '0')).replace('.0', '')
    num =        </table>
        <div style="text-align:center; margin-top:30px; font-size:18px; font-weight:bold;">상기 학생의 교내활동을 확인함.</div>
        """
        teacher_label = "담당교사 :"
    else:
        title = "조 퇴 str(row['번호']).replace('.0', '')
    name = row['이름']
    
    # 날짜 추출 (row['시간']에서 'MM/DD' 부분 활용)
    try:
        date_str = row['시간'].split(' ')[0] # "03/10"
        m, ,  외 출 증"
        table_html = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background d = date_str.split('/')
        y = str(datetime.now().year)
    except:
        y-color:#E7E6E6; height:38px; border-bottom:1.5px solid black;">
                <td colspan="2" style="text-align:center; font-size:16px; font-weight:bold; letter-spacing:1px;">
                    {dept} 과 &nbsp, m, d = "2026", "  ", "  "

    # 3. 종류별 양식 분기
    if row['종류'] == "교내활동증":
        title = "학 생 교 내 활 동 확 인 증"
        teacher_label = "담당교사 :"
        # 교;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:120px;">
                <td style="width:18%; border:1px solid내활동 전용 테이블 구조
        content_table = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:40px; border-bottom:1.5px solid black;">
                 black; background:#F2F2F2; text-align:center; font-weight:bold; font-size:18px; letter-spacing:5px;">사유</td>
                <td style="width:82%; border:1px solid black; padding:10px; text-align:left; vertical-align:top;">{row['사유']} (행선지: {row['행선지']})<td colspan="2" style="text-align:center; font-size:17px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&</td>
            </tr>
            <tr style="height:45px;">
                <td style="border:1px solid black; background:#F2F2F2; text-align:center; font-weight:bold; font-size:18px; letter-spacing:5px;">시간</td>
                <td stylenbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:90px;">
                <td style="width:18%; border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; line-height:1.3="border:1px solid black; text-align:center; font-size:17px;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row;">교내<br>활동<br>사유</td>
                <td style="width:82%; border:1px solid black; padding:10px; text-align:left; vertical-align:top; font-['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:30px; font-size:18px; font-weight:bold;">상기 학생의 조퇴, 외출을 허가함.</div>
        """
        teacher_label = "담size:16px;">{row['사유']}</td>
            </tr>
            <tr style="height:50px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold;">장소</td>
                <td style="border 임 :"

    # 4. 전체 레이아웃 결합
    full_html = f"""
    <div style="width:480px; margin:20px auto; border:2px solid black;:1px solid black; padding-left:10px; text-align:left; font-size:16px;">{row['행선지']}</td>
            </tr>
            <tr style="height:5 padding:0; background:white; color:black; font-family:'Malgun Gothic', 'Apple SD Gothic Neo', sans-serif;">
        <!-- 상단 헤더 -->
        <div style="border-bottom:10px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold;">시간</td>
                <td style="border:1px solid black; text-align:center; font-size:18px; letter-spacing:1px.5px solid black; background-color:#D9E1F2; padding:12px; text-align:center;">
            <h2 style="margin:0; font-size:22px; letter-spacing:5px;">{title}</h2>
        </div>
        
        <!-- 중앙 테이블 -->
        ;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:35px; font-size:19px; font-weight:bold<div style="padding:0px;">
            {table_html}
        </div>

        <!-- 하단 서명 섹션 -->
        <div style="text-align:center; padding:25px 0 15;">상기 학생의 교내활동을 확인함.</div>
        """
    else:
        title = "조 퇴px 0;">
            <div style="font-size:19px; margin-bottom:20px; letter-spacing:3px;">
                20{y} 년 &nbsp;&nbsp;&nbsp; {m} 월 &nbsp;&nbsp;&nbsp; {d} 일
            </div>
            <div style="font-size:19px; font-weight:bold; margin-bottom:25px; position:relative;">
                {teacher_label} &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인 ,  외 출 증"
        teacher_label = "담 임 :"
        # 조퇴/외출 전용 테이블 구조
        content_table = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:40px; border-bottom:1.5px solid black)
                {seal_html}
            </div>
            <div style="border-top:1.5;">
                <td colspan="2" style="text-align:center; font-size:17px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsppx solid black; padding:15px 0; font-size:24px; font-weight:bold; letter-spacing:8px;">
                경 기 기 계 공 업 고 등 학 교
            </div>
        </div>; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:120px;">
                <td style="width:18%; border:1px solid black;
    </div>
    """
    
    # 미리보기 렌더링
    st.markdown("### 🖨️ 증명서 미리보기")
    st.markdown(full_html, unsafe_allow_html=True)
    
    # 인쇄 스크립트 실행
    components.html(f"<script> background:#f0f0f0; text-align:center; font-weight:bold; font-size:19px; letter-spacing:5px;">사유</td>
                <td style="width:82%; border:1px solid black; padding:15px; text-align:left; vertical-alignwindow.parent.print();</script>", height=0)
