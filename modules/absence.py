import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_multiple_images, process_sig, decode_image_safe, decode_multiple_images_safe, send_discord_notification, SchoolPDF
import io
import base64

def show_page(conn, user, fixed_info, paths):
    # 제출 완료 상태일 때
    if st.session_state.get('submitted'):
        st.title("✅ 제출 완료")
        st.success(f"{user['name']} 학생의 결석계가 성공적으로 접수되었습니다.")
        st.download_button(
            label="📄 완성된 결석계 PDF 다운로드",
            data=st.session_state.pdf_data,
            file_name=f"결석계_{user['name']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("추가로 작성하기"):
            st.session_state.submitted = False
            st.rerun()
        return

    st.title("📝 결석신고서 작성")
    st.caption(f"인증 정보: {user['name']} ({user['num']}번)")

    # 1. 날짜 설정
    st.subheader("📅 1. 결석 날짜 설정")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("시작일")
    end_d = c2.date_input("종료일")
    calc_days = len(pd.bdate_range(start_d, end_d)) if start_d <= end_d else 0
    st.info(f"선택 기간 내 평일 수업일수는 **{calc_days}일**입니다.")

    # 2. 상세 정보 입력 Form
    with st.form("absence_form"):
        st.subheader("📍 2. 결석 사유 및 증빙")
        reason_detail = st.text_area("상세 사유 (병원명, 사유 등)")
        proof_files = st.file_uploader("증빙서류 첨부 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

        st.subheader("✍️ 3. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        
        sc1, sc2 = st.columns(2)
        with sc1:
            st.write("보호자 서명")
            g_canvas = st_canvas(height=100, width=200, stroke_width=3, key="g_sig", background_color="rgba(0,0,0,0)")
        with sc2:
            st.write("학생 서명")
            s_canvas = st_canvas(height=100, width=200, stroke_width=3, key="s_sig", background_color="rgba(0,0,0,0)")

        if st.form_submit_button("✅ 결석신고서 제출"):
            if not g_name or calc_days == 0 or not reason_detail:
                st.error("모든 정보를 입력해 주세요.")
            else:
                try:
                    # 데이터 처리
                    g_b64 = process_sig(g_canvas.image_data)
                    s_b64 = process_sig(s_canvas.image_data)
                    proof_chunks = process_multiple_images(proof_files)
                    
                    # PDF 생성
                    rep_data = {"num": user['num'], "name": user['name'], "s_m": start_d.month, "s_d": start_d.day,
                                "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                    
                    pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                    st.session_state.pdf_data = pdf_gen.generate_report(
                        rep_data, decode_image_safe(g_b64), decode_image_safe(s_b64), 
                        decode_multiple_images_safe(proof_chunks), fixed_info
                    )

                    # 구글 시트 저장
                    sub_time = get_kst().strftime("%m-%d %H:%M")
                    per_str = f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}"
                    existing = conn.read(ttl=0)
                    
                    row_dict = {
                        "결석기간": per_str, "일수": calc_days, "이름": user['name'], "번호": user['num'],
                        "보호자": g_name, "상세사유": reason_detail, "제출일시": sub_time,
                        "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}"
                    }
                    for i, chunk in enumerate(proof_chunks):
                        row_dict[f"증빙_{i+1}"] = f"'{chunk}" if chunk else ""

                    conn.update(data=pd.concat([existing, pd.DataFrame([row_dict])], ignore_index=True))
                    send_discord_notification(f"🔔 [결석계 제출] {user['name']}({user['num']}번) / {per_str}")
                    st.session_state.submitted = True
                    st.rerun()
                except Exception as e: st.error(f"저장 오류: {e}")
