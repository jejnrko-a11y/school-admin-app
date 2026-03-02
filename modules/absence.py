import streamlit as st
import pandas as pd
from streamlit_drawable_canvas import st_canvas
from utils import get_kst, process_multiple_images, process_sig, decode_image_safe, decode_multiple_images_safe, send_discord_notification, SchoolPDF
import io
import base64
from datetime import datetime
from streamlit_pdf_viewer import pdf_viewer # 전용 뷰어 추가

def show_page(conn, user, fixed_info, paths):
    # 세션 상태 초기화
    if 'preview_done' not in st.session_state: st.session_state.preview_done = False
    if 'temp_pdf_data' not in st.session_state: st.session_state.temp_pdf_data = None
    if 'temp_row_dict' not in st.session_state: st.session_state.temp_row_dict = None

    # 제출 성공 완료 화면
    if st.session_state.get('submitted'):
        st.title("✅ 결석계 제출 완료")
        st.balloons()
        st.success(f"{st.session_state.student_name} 학생의 서류가 선생님께 전송되었습니다.")
        
        st.download_button(
            label="📄 최종본 PDF 다운로드",
            data=st.session_state.pdf_data,
            file_name=f"결석계_{st.session_state.student_name}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        
        # 완료 화면에서도 미리보기 확인 가능
        pdf_viewer(st.session_state.pdf_data)

        if st.button("새로운 결석계 작성하기"):
            st.session_state.submitted = False
            st.session_state.preview_done = False
            st.session_state.temp_pdf_data = None
            st.rerun()
        return

    st.title("📝 결석신고서 작성")

    # 1. 날짜 설정
    st.subheader("📅 1. 결석 날짜 설정")
    c1, c2 = st.columns(2)
    start_d = c1.date_input("시작일", get_kst())
    end_d = c2.date_input("종료일", get_kst())

    calc_days = 0
    if start_d <= end_d:
        business_days = pd.bdate_range(start_d, end_d)
        calc_days = len(business_days)
        st.info(f"평일 수업일수: **총 {calc_days}일**")
    else:
        st.error("종료일이 시작일보다 빠를 수 없습니다.")

    # 2. 상세 정보 입력 Form
    with st.form("absence_form"):
        st.subheader("📍 2. 사유 및 증빙")
        reason_detail = st.text_area("상세 사유 (병원명, 질병명 등)")
        proof_files = st.file_uploader("증빙서류 사진 (여러 장 가능)", type=['jpg', 'png', 'jpeg'], accept_multiple_files=True)

        st.subheader("✍️ 3. 보호자 확인 및 서명")
        g_name = st.text_input("보호자 성함")
        
        st.write("---")
        sig_col1, sig_col2 = st.columns(2)
        with sig_col1:
            st.markdown("#### 🖋️ 보호자 서명란")
            g_canvas = st_canvas(
                height=150, width=280, stroke_width=3, 
                key="g_sig_canvas", background_color="rgba(0,0,0,0)", 
                update_streamlit=True
            )
        with sig_col2:
            st.markdown("#### 🖋️ 학생 서명란")
            s_canvas = st_canvas(
                height=150, width=280, stroke_width=3, 
                key="s_sig_canvas", background_color="rgba(0,0,0,0)", 
                update_streamlit=True
            )

        # 1단계 버튼
        preview_btn = st.form_submit_button("🔍 1단계: 서류 미리보기 생성")

        if preview_btn:
            if not g_name or calc_days == 0 or not reason_detail:
                st.error("모든 정보를 입력하고 날짜를 확인해 주세요.")
            else:
                try:
                    with st.spinner("미리보기를 만드는 중..."):
                        g_b64 = process_sig(g_canvas.image_data)
                        s_b64 = process_sig(s_canvas.image_data)
                        proof_chunks = process_multiple_images(proof_files)

                        rep_data = {
                            "num": user['num'], "name": user['name'],
                            "s_m": start_d.month, "s_d": start_d.day,
                            "e_m": end_d.month, "e_d": end_d.day,
                            "days": calc_days, "g_name": g_name
                        }
                        
                        pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                        pdf_bytes = pdf_gen.generate_report(
                            rep_data, 
                            decode_image_safe(g_b64), 
                            decode_image_safe(s_b64), 
                            decode_multiple_images_safe(proof_chunks), 
                            fixed_info
                        )

                        # 저장용 데이터 구성
                        sub_time = get_kst().strftime("%m-%d %H:%M")
                        per_str = f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}"
                        row_dict = {
                            "결석기간": per_str, "일수": calc_days, "이름": user['name'], "번호": user['num'],
                            "보호자": g_name, "상세사유": reason_detail, "제출일시": sub_time,
                            "학생서명": f"'{s_b64}", "보호자서명": f"'{g_b64}"
                        }
                        for i, chunk in enumerate(proof_chunks):
                            row_dict[f"증빙_{i+1}"] = f"'{chunk}"

                        st.session_state.temp_pdf_data = pdf_bytes
                        st.session_state.temp_row_dict = row_dict
                        st.session_state.preview_done = True
                        st.session_state.student_name = user['name']
                except Exception as e:
                    st.error(f"미리보기 생성 실패: {e}")

    # 3. 미리보기 출력 및 최종 제출
    if st.session_state.preview_done:
        st.markdown("---")
        st.subheader("👀 결석계 최종 확인")
        st.warning("⚠️ 아직 제출되지 않았습니다! 아래 서류를 확인하고 반드시 [최종 제출] 버튼을 눌러주세요.")

        # [수정] 전용 뷰어로 PDF 표시 (용량이 커도 잘 나옴)
        pdf_viewer(st.session_state.temp_pdf_data)

        if st.button("🚀 2단계: 위 내용으로 최종 제출하기", use_container_width=True):
            try:
                with st.spinner("선생님께 전송 중..."):
                    existing = conn.read(worksheet="결석명부", ttl=0)
                    new_row = pd.DataFrame([st.session_state.temp_row_dict])
                    conn.update(worksheet="결석명부", data=pd.concat([existing, new_row], ignore_index=True))
                    
                    msg = f"🔔 [결석계 제출] {st.session_state.student_name} / {st.session_state.temp_row_dict['결석기간']}"
                    send_discord_notification(msg)
                    
                    st.session_state.pdf_data = st.session_state.temp_pdf_data
                    st.session_state.submitted = True
                    st.rerun()
            except Exception as e:
                st.error(f"제출 실패: {e}")
