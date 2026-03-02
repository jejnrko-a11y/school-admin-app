import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_multiple_images, process_sig, decode_image_safe, decode_multiple_images_safe, send_discord_notification, SchoolPDF
import io
import base64
from datetime import datetime

def show_page(conn, user, fixed_info, paths):
    if st.session_state.get('submitted'):
        st.title("✅ 결석계 제출 완료")
        st.success(f"{st.session_state.student_name} 학생의 서류가 제출되었습니다.")
        st.download_button("📄 통합 PDF 다운로드", data=st.session_state.pdf_data, 
                           file_name=f"결석계_{st.session_state.student_name}.pdf", use_container_width=True)
        if st.button("새로 작성하기"):
            st.session_state.submitted = False
            st.rerun()
        return

    st.title("📝 결석신고서 작성")
    c1, c2 = st.columns(2)
    start_d, end_d = c1.date_input("시작일"), c2.date_input("종료일")
    calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
    st.info(f"평일 결석 일수: **{calc_days}일**")

    with st.form("absence_form"):
        reason_detail = st.text_area("상세 사유")
        proof_files = st.file_uploader("증빙 사진 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
        g_name = st.text_input("보호자 성함")
        sc1, sc2 = st.columns(2)
        with sc1: g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sc2: s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0:
                st.error("보호자 성함과 날짜를 확인하세요.")
            else:
                try:
                    # 1. 인코딩
                    g_b64 = process_sig(g_canvas.image_data)
                    s_b64 = process_sig(s_canvas.image_data)
                    proof_chunks = process_multiple_images(proof_files)
                    
                    # 2. PDF 생성
                    rep_data = {"num": user['num'], "name": user['name'], "s_m": start_d.month, "s_d": start_d.day,
                                "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                    pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                    st.session_state.pdf_data = pdf_gen.generate_report(rep_data, decode_image_safe(g_b64), decode_image_safe(s_b64), decode_multiple_images_safe(proof_chunks), fixed_info)
                    st.session_state.student_name = user['name']

                    # 3. [핵심] 결석명부 시트에 저장
                    # worksheet="결석명부"를 명시해야 합니다.
                    existing = conn.read(worksheet="결석명부", ttl=0)
                    row_dict = {
                        "결석기간": f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}",
                        "일수": calc_days, "이름": user['name'], "번호": user['num'],
                        "보호자": g_name, "상세사유": reason_detail, "제출일시": get_kst().strftime("%m-%d %H:%M"),
                        "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}"
                    }
                    for i, chunk in enumerate(proof_chunks):
                        row_dict[f"증빙_{i+1}"] = f"'{chunk}" if chunk else ""

                    conn.update(worksheet="결석명부", data=pd.concat([existing, pd.DataFrame([row_dict])], ignore_index=True))
                    
                    send_discord_notification(f"🔔 [결석계] {user['name']}({user['num']}번) / {calc_days}일")
                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e: st.error(f"저장 실패: {e}")
