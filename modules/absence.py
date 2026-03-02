import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_multiple_images, process_sig, decode_image_safe, decode_multiple_images_safe, send_discord_notification, SchoolPDF
import io
import base64
from datetime import datetime

def show_page(conn, student_options, fixed_info, paths):
    # 제출 완료 상태일 때 보여줄 화면
    if st.session_state.get('submitted'):
        st.title("✅ 결석계 제출 완료")
        st.balloons()
        st.success(f"{st.session_state.student_name} 학생의 서류가 성공적으로 접수되었습니다.")
        st.write("아래 버튼을 눌러 생성된 통합 PDF를 다운로드하여 보관하세요.")
        
        st.download_button(
            label="📄 완성된 통합 결석계 PDF 다운로드",
            data=st.session_state.pdf_data,
            file_name=f"결석계_{st.session_state.student_name}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        if st.button("새로운 결석계 작성하기"):
            st.session_state.submitted = False
            st.session_state.pdf_data = None
            st.rerun()
        return

    # 작성 화면
    st.title("📝 결석신고서 작성")

    # 1. 날짜 설정 (Form 밖에서 실시간 계산)
    st.subheader("📅 1. 결석 날짜 설정")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("결석 시작일", get_kst())
    end_d = c2.date_input("결석 종료일", get_kst())

    calc_days = 0
    if start_d <= end_d:
        # 주말 제외 평일 계산
        business_days = pd.bdate_range(start_d, end_d)
        calc_days = len(business_days)
        st.info(f"선택하신 기간 중 평일(수업일)은 **총 {calc_days}일**입니다.")
    else:
        st.error("종료일이 시작일보다 빠를 수 없습니다.")

    # 2. 상세 정보 입력 Form
    with st.form("absence_form"):
        st.subheader("📍 2. 학생 정보 및 사유")
        sel_student = st.selectbox("학생 이름을 선택하세요", student_options)
        
        reason_detail = st.text_area("상세 사유 (병원명, 질병명, 구체적인 사유 등)")

        st.subheader("📎 3. 증빙서류 첨부")
        proof_files = st.file_uploader("사진을 첨부하세요 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

        st.subheader("✍️ 4. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        
        sig_col1, sig_col2 = st.columns(2)
        with sig_col1:
            st.write("보호자 서명")
            g_canvas = st_canvas(
                height=100, width=200, stroke_width=3, 
                key="g_sig", background_color="rgba(0,0,0,0)", 
                update_streamlit=True
            )
        with sig_col2:
            st.write("학생 서명")
            s_canvas = st_canvas(
                height=100, width=200, stroke_width=3, 
                key="s_sig", background_color="rgba(0,0,0,0)", 
                update_streamlit=True
            )

        submit_btn = st.form_submit_button("✅ 결석신고서 제출하기")

        if submit_btn:
            if not g_name or calc_days == 0 or not reason_detail:
                st.error("모든 정보를 입력하고 날짜를 다시 확인해 주세요.")
            else:
                try:
                    # 학생 정보 분리
                    name_only = sel_student.split("(")[0]
                    num_only = int(sel_student.split("(")[1].replace("번)", ""))
                    st.session_state.student_name = name_only

                    # [처리 1] 서명 및 증빙 이미지 인코딩 (Base64)
                    g_b64 = process_sig(g_canvas.image_data)
                    s_b64 = process_sig(s_canvas.image_data)
                    proof_chunks = process_multiple_images(proof_files)

                    # [처리 2] PDF 생성을 위해 이미지 복구 (BytesIO)
                    g_io = decode_image_safe(g_b64)
                    s_io = decode_image_safe(s_b64)
                    ev_ios = decode_multiple_images_safe(proof_chunks)

                    # [처리 3] PDF 생성 데이터 구성 및 실행
                    rep_data = {
                        "num": num_only, "name": name_only,
                        "s_m": start_d.month, "s_d": start_d.day,
                        "e_m": end_d.month, "e_d": end_d.day,
                        "days": calc_days, "g_name": g_name
                    }
                    
                    pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                    st.session_state.pdf_data = pdf_gen.generate_report(rep_data, g_io, s_io, ev_ios, fixed_info)

                    # [처리 4] 구글 시트 저장 (순서: 기간, 일수, 이름, 번호, 보호자, 사유, 제출일, 서명, 증빙1~10)
                    sub_time = get_kst().strftime("%m-%d %H:%M")
                    per_str = f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}"
                    existing = conn.read(ttl=0)
                    
                    row_dict = {
                        "결석기간": per_str,
                        "일수": calc_days,
                        "이름": name_only,
                        "번호": num_only,
                        "보호자": g_name,
                        "상세사유": reason_detail,
                        "제출일시": sub_time,
                        "학생서명": f"'{s_b64}" if s_b64 else "",
                        "보호자서명": f"'{g_b64}" if g_b64 else ""
                    }
                    # 증빙_1 ~ 증빙_10 채우기
                    for idx, chunk in enumerate(proof_chunks):
                        row_dict[f"증빙_{idx+1}"] = f"'{chunk}" if chunk else ""

                    # 최종 업데이트
                    conn.update(data=pd.concat([existing, pd.DataFrame([row_dict])], ignore_index=True))

                    # [처리 5] 알림 발송 및 화면 전환
                    send_discord_notification(f"🔔 **[결석계 제출]** {name_only}({num_only}번) / {per_str} ({calc_days}일)")
                    st.session_state.submitted = True
                    st.rerun()

                except Exception as e:
                    st.error(f"제출 과정에서 오류가 발생했습니다: {e}")
