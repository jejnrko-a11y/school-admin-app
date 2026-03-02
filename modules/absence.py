import streamlit as st
import pandas as pd
from datetime import datetime
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_image_advanced, decode_image_safe, send_discord_notification, SchoolPDF
import io
import base64

def show_page(conn, student_options, fixed_info, paths):
    st.title("📝 결석신고서 작성")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("시작일")
    end_d = c2.date_input("종료일")
    calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
    st.info(f"평일 결석 일수: **{calc_days}일**")

    with st.form("absence_form"):
        sel_student = st.selectbox("학생 이름 선택", student_options)
        reason_detail = st.text_area("상세 사유")
        proof_files = st.file_uploader("증빙서류 사진 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
        g_name = st.text_input("보호자 성함")
        
        sc1, sc2 = st.columns(2)
        with sc1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sc2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0:
                st.error("입력 정보를 확인하세요.")
            else:
                try:
                    name_only = sel_student.split("(")[0]
                    num_only = int(sel_student.split("(")[1].replace("번)", ""))
                    
                    g_b64 = process_image_advanced(g_canvas.image_data, mode="signature")
                    s_b64 = process_image_advanced(s_canvas.image_data, mode="signature")
                    proof_chunks = process_image_advanced(proof_files, mode="evidence")
                    
                    rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                    
                    pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                    st.session_state.pdf_data = pdf_gen.generate_report(rep_data, decode_image_safe(g_b64), decode_image_safe(s_b64), decode_image_safe(proof_chunks), fixed_info)
                    st.session_state.student_name = name_only

                    # 시트 저장
                    existing = conn.read(ttl=0)
                    row_dict = {"결석기간": f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}", "일수": calc_days, 
                                "이름": name_only, "번호": num_only, "보호자": g_name, "상세사유": reason_detail, 
                                "제출일시": get_kst().strftime("%m-%d %H:%M"), "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}"}
                    for i, chunk in enumerate(proof_chunks): row_dict[f"증빙_{i+1}"] = f"'{chunk}"
                    
                    conn.update(data=pd.concat([existing, pd.DataFrame([row_dict])], ignore_index=True))
                    send_discord_notification(f"🔔 [결석계 제출] {name_only}({num_only}번) / {calc_days}일")
                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e: st.error(f"실패: {e}")
