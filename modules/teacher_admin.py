# ... (상단 생략)
                        try:
                            # 10개 조각 리스트로 모으기
                            ev_chunks = [row.get(f'증빙_{k}', "") for k in range(1, 11)]
                            
                            # 서명은 단일 복구, 증빙은 다중 복구 함수 사용
                            admin_pdf = SchoolPDF(paths['font'], paths['bold_font'], paths['bg']).generate_report(
                                r_d, 
                                decode_image_safe(row.get('보호자서명', "")), 
                                decode_image_safe(row.get('학생서명', "")), 
                                decode_multiple_images_safe(ev_chunks),
                                fixed_info
                            )
                            # ... (다운로드 버튼)
