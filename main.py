# ... (앞부분 동일)

elif menu == "교사용 관리":
    st.title("👨‍🏫 교사용 관리")
    pw = st.text_input("비밀번호", type="password")
    
    if pw == ADMIN_PASSWORD:
        try:
            data = conn.read(ttl=0)
            if not data.empty:
                # 최신 제출순으로 정렬 (제출일시 기준)
                data = data.sort_values(by='제출일시', ascending=False)
                
                for i, row in data.iterrows():
                    with st.expander(f"📌 {row['제출일시']} - {row['이름']} 학생"):
                        st.write(f"**보호자:** {row['보호자']} | **결석:** {row['결석기간']}")
                        st.write(f"**상세사유:** {row['상세사유']}")
                        
                        col_view, col_pdf = st.columns(2)
                        with col_view:
                            if row.get('증빙서류데이터'):
                                st.image(decode_base64_to_bytes(row['증빙서류데이터']), caption="증빙서류", width=300)
                        
                        with col_pdf:
                            st.write("📂 **행정 서류 관리**")
                            # PDF 재생성 버튼
                            if st.button(f"📄 {row['이름']} PDF 생성", key=f"btn_{i}"):
                                try:
                                    # 1. 날짜 데이터 안전하게 추출
                                    # "2026-03-01~2026-03-02 (1.0일간)" 형태에서 앞의 날짜만 추출
                                    date_part = str(row['결석기간']).split('(')[0].strip()
                                    s_date_str = date_part.split('~')[0].strip()
                                    e_date_str = date_part.split('~')[1].strip()
                                    
                                    s_date_obj = datetime.strptime(s_date_str, "%Y-%m-%d")
                                    e_date_obj = datetime.strptime(e_date_str, "%Y-%m-%d")
                                    
                                    # 2. 숫자 데이터 정수화 (1.0 -> 1)
                                    days_val = int(float(row['일수']))
                                    num_val = int(float(row['번호']))
                                    
                                    admin_report_data = {
                                        "num": num_val, 
                                        "name": str(row['이름']), 
                                        "s_m": s_date_obj.month, 
                                        "s_d": s_date_obj.day,
                                        "e_m": e_date_obj.month, 
                                        "e_d": e_date_obj.day,
                                        "days": days_val, 
                                        "g_name": str(row['보호자'])
                                    }
                                    
                                    # 3. PDF 생성
                                    pdf_gen_admin = SchoolPDF()
                                    # 서명 데이터가 없는 예전 데이터일 경우를 대비해 None 처리
                                    g_sig = decode_base64_to_bytes(row.get('보호자서명'))
                                    s_sig = decode_base64_to_bytes(row.get('학생서명'))
                                    
                                    admin_pdf = pdf_gen_admin.generate_report(admin_report_data, g_sig, s_sig)
                                    
                                    st.session_state[f"pdf_{i}"] = admin_pdf
                                    st.success(f"✅ {row['이름']} 학생 PDF 준비됨")
                                    
                                except Exception as e:
                                    st.error(f"데이터 변환 오류: {e}")
                            
                            # 생성된 PDF가 세션에 있으면 다운로드 버튼 표시
                            if f"pdf_{i}" in st.session_state:
                                st.download_button(
                                    label=f"📥 {row['이름']} PDF 다운로드",
                                    data=st.session_state[f"pdf_{i}"],
                                    file_name=f"결석신고서_{row['이름']}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_{i}"
                                )
            else:
                st.info("제출된 데이터가 없습니다.")
        except Exception as e:
            st.error(f"시트 로드 실패: {e}")
