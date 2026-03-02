# ... (상단 생략)
            if st.form_submit_button("🔍 1단계: 미리보기 생성"):
                if not g_name or calc_days == 0 or not reason_detail:
                    st.error("입력 정보를 확인하세요.")
                else:
                    try:
                        with st.spinner("이미지 최적화 및 미리보기 생성 중..."):
                            # 1. 인코딩
                            g_b64 = process_sig(g_canvas.image_data)
                            s_b64 = process_sig(s_canvas.image_data)
                            proof_chunks = process_multiple_images(proof_files)
                            
                            # 2. PDF 생성 (즉시 복구 테스트)
                            g_io = decode_image_safe(g_b64)
                            s_io = decode_image_safe(s_b64)
                            ev_ios = decode_multiple_images_safe(proof_chunks)
                            
                            rep_data = {"num": user['num'], "name": user['name'], "s_m": start_d.month, "s_d": start_d.day,
                                        "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                            
                            pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                            st.session_state.temp_pdf_data = pdf_gen.generate_report(rep_data, g_io, s_io, ev_ios, fixed_info)

                            # 3. [수정] 구글 시트 저장용 딕셔너리 조립 (빈 값 처리 강화)
                            row_dict = {
                                "결석기간": f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}", 
                                "일수": calc_days, "이름": user['name'], "번호": user['num'],
                                "보호자": g_name, "상세사유": reason_detail, "제출일시": get_kst().strftime("%m-%d %H:%M"),
                                "학생서명": f"'{s_b64}" if s_b64 else "", 
                                "보호자서명": f"'{g_b64}" if g_b64 else ""
                            }
                            # 조각 데이터: 내용이 있을 때만 ' 붙임
                            for i, chunk in enumerate(proof_chunks):
                                if chunk.strip():
                                    row_dict[f"증빙_{i+1}"] = f"'{chunk}"
                                else:
                                    row_dict[f"증빙_{i+1}"] = ""

                            st.session_state.temp_row_dict = row_dict
                            st.session_state.preview_done = True
                            st.session_state.student_name = user['name']
                            st.toast("미리보기가 생성되었습니다.")
                    except Exception as e: st.error(f"처리 실패: {e}")
# ... (하단 동일)
