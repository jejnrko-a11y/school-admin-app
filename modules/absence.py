# ... (상단 생략)
            if st.form_submit_button("✅ 결석신고서 제출"):
                if not g_name or calc_days == 0:
                    st.error("보호자 성함과 날짜를 확인하세요.")
                else:
                    try:
                        name_only = sel_student.split("(")[0]
                        num_only = int(sel_student.split("(")[1].replace("번)", ""))
                        st.session_state.student_name = name_only
                        
                        # 1. 처리
                        g_b64 = process_sig(g_canvas.image_data)
                        s_b64 = process_sig(s_canvas.image_data)
                        proof_chunks = process_multiple_images(proof_files)
                        
                        # 2. PDF 생성을 위한 즉시 복구 (리스트 전달)
                        g_io = decode_image_safe(g_b64)
                        s_io = decode_image_safe(s_b64)
                        ev_ios = decode_multiple_images_safe(proof_chunks)
                        
                        rep_data = {"num": num_only, "name": name_only, "s_m": start_d.month, "s_d": start_d.day,
                                    "e_m": end_d.month, "e_d": end_d.day, "days": calc_days, "g_name": g_name}
                        
                        pdf_gen = SchoolPDF(paths['font'], paths['bold_font'], paths['bg'])
                        st.session_state.pdf_data = pdf_gen.generate_report(rep_data, g_io, s_io, ev_ios, fixed_info)

                        # 3. 구글 시트 저장
                        sub_time = get_kst().strftime("%m-%d %H:%M")
                        per_str = f"{start_d.strftime('%m-%d')}~{end_d.strftime('%m-%d')}"
                        existing = conn.read(ttl=0)
                        
                        row_dict = {
                            "결석기간": per_str, "일수": calc_days, "이름": name_only, "번호": num_only,
                            "보호자": g_name, "상세사유": reason_detail, "제출일시": sub_time,
                            "학생서명": f"'{s_b64}" if s_b64 else "", 
                            "보호자서명": f"'{g_b64}" if g_b64 else ""
                        }
                        for idx, chunk in enumerate(proof_chunks):
                            row_dict[f"증빙_{idx+1}"] = f"'{chunk}" if chunk else ""

                        conn.update(data=pd.concat([existing, pd.DataFrame([row_dict])], ignore_index=True))
                        # ... (알림 후 리런)
