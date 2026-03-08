import streamlit as st
import pandas as pd
from datetime import datetime
import streamlit.components.v1 as components
from utils import get_kst, load_student_list

def show_page(conn, fixed_info):
    # ==========================================
    # 1. 증명서 양식 전용 CSS (화면 미리보기 & 인쇄용)
    # ==========================================
    st.markdown("""
        <style>
        @media print {
            @page { size: A4 landscape; margin: 15mm; }
            header, [data-testid="stHeader"], [data-testid="stSidebar"], footer,
            .stButton, .no-print, [data-testid="stForm"] { display: none !important; }
            .main .block-container { padding: 0 !important; max-width: 100% !important; }
            .cert-container { border: 2px solid #000 !important; display: block !important; }
        }

        /* 증명서 박스 디자인 */
        .cert-container {
            width: 100%;
            max-width: 800px;
            margin: 20px auto;
            padding: 40px;
            border: 1px solid #ccc;
            background-color: #fff;
            color: #000;
            font-family: 'Malgun Gothic', sans-serif;
            position: relative;
        }
        .cert-title {
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            text-decoration: underline;
            margin-bottom: 40px;
            letter-spacing: 10px;
        }
        .cert-serial { position: absolute; top: 20px; right: 20px; font-size: 14px; }
        .cert-table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 30px;
        }
        .cert-table td {
            border: 1px solid #000;
            padding: 12px;
            font-size: 18px;
            text-align: center;
        }
        .cert-label { background-color: #f0f0f0; font-weight: bold; width: 20%; }
        .cert-content { text-align: left !important; padding-left: 20px !important; }
        
        .cert-footer {
            text-align: center;
            margin-top: 50px;
            font-size: 22px;
            font-weight: bold;
        }
        .seal-area {
            position: absolute;
            bottom: 40px;
            right: 60px;
            width: 80px;
            height: 80px;
            border: 2px solid rgba(255,0,0,0.5);
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            color: rgba(255,0,0,0.5);
            font-size: 12px;
            transform: rotate(-15deg);
        }
        </style>
    """, unsafe_allow_html=True)

    st.title("📂 증명서 발급 시스템")
    st.info("조퇴, 외출, 교내활동 증명서를 생성하고 관리합니다.")

    # 2. 데이터 준비
    df_students = load_student_list(conn)
    student_options = [f"{row['번호']}번 {row['이름']}" for _, row in df_students.iterrows()]
    
    # 발급 내역 로드
    try:
        df_log = conn.read(worksheet="발급명부", ttl=0)
    except:
        df_log = pd.DataFrame(columns=["일련번호", "날짜", "학생명", "종류", "시간", "행선지", "사유"])

    # ---------------------------------------------------------
    # PART 1: 발급 정보 입력 폼
    # ---------------------------------------------------------
    with st.form("issuance_form"):
        st.subheader("📝 발급 정보 입력")
        c1, c2 = st.columns(2)
        with c1:
            cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            target_date = st.date_input("발급 날짜", value=get_kst().date())
        with c2:
            selected_student = st.selectbox("학생 선택", student_options)
            destination = st.text_input("행선지(장소)", placeholder="예: 병원, 가정, 과학관 등")

        # 교시 슬라이더 (화요일 7교시 로직 적용)
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: period_options.append("7교시")
        period_options.append("종례")

        time_range = st.select_slider(
            "⏰ 적용 시간(교시) 범위",
            options=period_options,
            value=(period_options[0], period_options[-1])
        )
        
        reason = st.text_input("상세 사유", placeholder="예: 발열로 인한 귀가, 대회 참가 등")
        
        submit_btn = st.form_submit_button("🔍 증명서 생성 및 미리보기", use_container_width=True)

    # ---------------------------------------------------------
    # PART 2: 미리보기 및 저장 로직
    # ---------------------------------------------------------
    if submit_btn:
        now = get_kst()
        serial_no = f"{now.year}-{len(df_log) + 1:03d}"
        student_name = selected_student.split(' ')[1]
        student_num = selected_student.split('번')[0]
        time_str = f"{time_range[0]} ~ {time_range[1]}"

        # 데이터 저장 준비
        new_entry = {
            "일련번호": serial_no, "날짜": target_date.strftime("%Y-%m-%d"),
            "학생명": student_name, "종류": cert_type, "시간": time_str,
            "행선지": destination, "사유": reason
        }

        # 미리보기 레이아웃 렌더링
        html_cert = f"""
        <div class="cert-container">
            <div class="cert-serial">제 {serial_no} 호</div>
            <div class="cert-title">{cert_type}</div>
            <table class="cert-table">
                <tr>
                    <td class="cert-label">성 명</td><td>{student_name}</td>
                    <td class="cert-label">학 번</td><td>{fixed_info['grade']}학년 {fixed_info['cls']}반 {student_num}번</td>
                </tr>
                <tr>
                    <td class="cert-label">일 시</td>
                    <td colspan="3" class="cert-content">{target_date.strftime('%Y년 %m월 %d일')} ({time_str})</td>
                </tr>
                <tr>
                    <td class="cert-label">행선지</td><td colspan="3" class="cert-content">{destination}</td>
                </tr>
                <tr>
                    <td class="cert-label">사 유</td><td colspan="3" class="cert-content">{reason}</td>
                </tr>
            </table>
            <p style="text-align:center; font-size:16px; margin-top:30px;">
                위 학생은 위와 같은 사유로 {cert_type.replace('증','')}함을 증명합니다.
            </p>
            <div class="cert-footer">
                {target_date.strftime('%Y년 %m월 %d일')}<br><br>
                경기기계공업고등학교장 (직인)
            </div>
            <div class="seal-area">학교장인</div>
        </div>
        """
        st.markdown(html_cert, unsafe_allow_html=True)

        # 실제 DB 저장
        updated_log = pd.concat([df_log, pd.DataFrame([new_entry])], ignore_index=True)
        conn.update(worksheet="발급명부", data=updated_log)
        
        st.success(f"✅ {cert_type} 발급 기록이 저장되었습니다.")
        
        # 인쇄 버튼
        components.html("""
            <script>
            function printCert() {
                window.parent.print();
            }
            </script>
            <button onclick="printCert()" style="
                width: 100%; padding: 15px; background-color: #1E3A8A; 
                color: white; border: none; border-radius: 8px; cursor: pointer;
                font-weight: bold; font-size: 16px; margin-top: 10px;">🖨️ 증명서 즉시 인쇄하기</button>
        """, height=70)

    # ---------------------------------------------------------
    # PART 3: 발급 내역 조회
    # ---------------------------------------------------------
    with st.expander("📋 최근 발급 내역 확인"):
        if not df_log.empty:
            st.dataframe(df_log.sort_values(by="일련번호", ascending=False), use_container_width=True, hide_index=True)
        else:
            st.write("발급 기록이 없습니다.")
