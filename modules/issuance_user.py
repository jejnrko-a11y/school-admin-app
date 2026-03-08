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

def render_certificate(row, fixed_info):
    # 인쇄용 증명서 양식
    html_layout = f"""
    <div style="border:5px double black; padding:40px; background:white; color:black; font-family:'Malgun Gothic', sans-serif; position:relative; min-height:450px;">
        <div style="text-align:right; font-size:14px;">제 {row['일련번호']} 호</div>
        <h1 style="text-align:center; text-decoration:underline; letter-spacing:15px; font-size:40px; margin-top:10px;">{row['종류']}</h1>
        <table style="width:100%; border-collapse:collapse; margin-top:30px; border:2px solid black;">
            <tr>
                <td style="padding:15px; border:1px solid black; background:#f0f0f0; width:20%; font-weight:bold; text-align:center;">성 명</td>
                <td style="padding:15px; border:1px solid black; width:30%; text-align:center;">{row['이름']}</td>
                <td style="padding:15px; border:1px solid black; background:#f0f0f0; width:20%; font-weight:bold; text-align:center;">학 번</td>
                <td style="padding:15px; border:1px solid black; width:30%; text-align:center;">{fixed_info['grade']}학년 {fixed_info['cls']}반 {row['번호']}번</td>
            </tr>
            <tr>
                <td style="padding:15px; border:1px solid black; background:#f0f0f0; font-weight:bold; text-align:center;">일 시</td>
                <td colspan="3" style="padding:15px; border:1px solid black;">{row['시간']}</td>
            </tr>
            <tr>
                <td style="padding:15px; border:1px solid black; background:#f0f0f0; font-weight:bold; text-align:center;">행선지</td>
                <td colspan="3" style="padding:15px; border:1px solid black;">{row['행선지']}</td>
            </tr>
            <tr>
                <td style="padding:15px; border:1px solid black; background:#f0f0f0; font-weight:bold; text-align:center;">사 유</td>
                <td colspan="3" style="padding:15px; border:1px solid black;">{row['사유']}</td>
            </tr>
        </table>
        <p style="text-align:center; margin-top:40px; font-size:18px;">위 학생은 위와 같은 사유로 {row['종류'].replace('증','')}함을 증명합니다.</p>
        <div style="text-align:center; margin-top:60px; font-size:24px; font-weight:bold;">경기기계공업고등학교장 (직인)</div>
        <div style="position:absolute; bottom:50px; right:120px; width:70px; height:70px; border:2px solid rgba(255,0,0,0.4); border-radius:50%; display:flex; align-items:center; justify-content:center; color:rgba(255,0,0,0.4); font-size:12px; transform:rotate(-15deg);">학교장인</div>
    </div>
    """
    st.markdown(html_layout, unsafe_allow_html=True)
    components.html("<script>window.parent.print();</script>", height=0)
