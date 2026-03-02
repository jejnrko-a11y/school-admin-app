import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_multiple_images, process_sig, decode_image_safe, decode_multiple_images_safe, send_discord_notification, SchoolPDF
import io
import base64

def show_page(conn, student_options, fixed_info, paths):
    if st.session_state.get('submitted'):
        st.title("✅ 결석계 제출 완료")
        st.success(f"{st.session_state.student_name} 학생의 서류가 제출되었습니다.")
        st.download_button("📄 통합 결석계 PDF 다운로드", data=st.session_state.pdf_data, file_name=f"결석계_{st.session_state.student_name}.pdf", use_container_width=True)
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
        sel_student = st.selectbox("학생 선택", student_options)
        reason_detail = st.text_area("상세 사유")
        proof_files = st.file_uploader("증빙 사진 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)
        g_name = st.text_input("보호자 성함")
        sc1, sc2 = st.columns(2)
        with sc1: g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sc2: s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0:
                st.error("입력 정보를 확인하세요.")
            else:
                try:
                    # 1. 데이터 처리
                    name_only = sel_student.split("(")[0]
                    num_only = int(sel_student.split("(")[1].replace("번)", ""))
                    g_b64 = process_sig(g_canvas.image_data)
                    s_b64 = process_sig(s_canvas.image_data)
                    proof_chunks = process_multiple_images(proof_files)
                    
                    # 2. PDF 생성
                    rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                    pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                    st.session_state.pdf_data = pdf_gen.generate_report(rep_data, decode_image_safe(g_b64), decode_image_safe(s_b64), decode_multiple_images_safe(proof_chunks), fixed_info)
                    st.session_state.student_name = name_only

                    # 3. [핵심] 구글 시트 전송용 딕셔너리 수동 매칭
                    existing = conn.read(ttl=0)
                    row_dict = {
                        "결석기간": f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}",
                        "일수": calc_days,
                        "이름": name_only,
                        "번호": num_only,
                        "보호자": g_name,
                        "상세사유": reason_detail,
                        "제출일시": get_kst().strftime("%m-%d %H:%M"),
                        "학생서명": f"'{s_b64}",
                        "보호자서명": f"'{g_b64}"
                    }
                    # 증빙_1 ~ 증빙_10 컬럼명 강제 지정
                    for idx in range(1, 11):
                        val = proof_chunks[idx-1] if idx <= len(proof_chunks) else ""
                        row_dict[f"증빙_{idx}"] = f"'{val}" if val else ""

                    # 컬럼 순서 강제 정렬 (시트 순서와 일치)
                    new_row = pd.DataFrame([row_dict])
                    conn.update(data=pd.concat([existing, new_row], ignore_index=True))
                    
                    # 전송 성공 디버그 알림
                    st.toast(f"데이터 {len(proof_chunks[0])}자 전송 시도 성공")
                    
                    send_discord_notification(f"🔔 [제출] {name_only}({num_only}번) / {calc_days}일")
                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e:
                    st.error(f"제출 중 오류가 발생했습니다. 구글 시트의 컬럼명을 다시 확인하세요: {e}")
