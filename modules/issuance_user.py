# --- 탭 1: 신청서 작성 ---
    with tab1:
        # [1. 날짜 선택 로직]
        if 'issuance_date' not in st.session_state:
            st.session_state.issuance_date = get_kst().date()
            
        target_date = st.date_input("발생 날짜 선택", value=st.session_state.issuance_date)

        # [2. 요일별 교시 리스트 생성]
        weekday = target_date.weekday()
        period_options = ["조회", "1교시", "2교시", "3교시", "4교시", "5교시", "6교시"]
        if weekday == 1: # 화요일일 때 7교시 추가
            period_options.append("7교시")
        period_options.append("종례")

        # [3. 날짜 변경 시 슬라이더 초기화 (조회~종례)]
        if target_date != st.session_state.issuance_date:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])
            st.session_state.issuance_date = target_date

        # 처음 접속 시 기본값 설정
        if 'issuance_slider' not in st.session_state:
            st.session_state.issuance_slider = (period_options[0], period_options[-1])

        with st.form("request_form", clear_on_submit=True):
            c1, c2 = st.columns(2)
            with c1:
                cert_type = st.selectbox("증명서 종류", ["조퇴증", "외출증", "교내활동증"])
            with c2:
                destination = st.text_input("장소 (행선지)", placeholder="예: 병원, 가정, 과학관")
            
            reason = st.text_input("상세 사유", placeholder="사유를 입력하세요.")

            # [4. 이미지와 동일한 UI 적용]
            st.write(f"⏰ **{target_date.strftime('%m/%d')} ({['월','화','수','목','금','토','일'][weekday]}) 교시 선택**")
            
            selected_range = st.select_slider(
                "드래그하여 시작/종료 교시를 선택하세요", # 요청하신 문구
                options=period_options,
                value=st.session_state.issuance_slider, # 디폴트: 조회 ~ 종례
                key="issuance_range_slider"
            )
            
            if st.form_submit_button("🚀 승인 신청하기", use_container_width=True):
                if not destination or not reason:
                    st.error("장소와 사유를 모두 입력해 주세요.")
                else:
                    # 선택된 범위를 문자열로 변환 (예: 조회~종례)
                    period_str = f"{selected_range[0]}~{selected_range[1]}" if selected_range[0] != selected_range[1] else selected_range[0]
                    
                    new_data = pd.DataFrame([{
                        "일련번호": "-", 
                        "신청일시": get_kst().strftime("%m-%d %H:%M"),
                        "이름": user['name'], 
                        "번호": user['num'], 
                        "종류": cert_type,
                        "시간": f"{target_date.strftime('%m/%d')} ({period_str})",
                        "행선지": destination, 
                        "사유": reason, 
                        "상태": "신청", 
                        "승인일시": "-"
                    }])
                    
                    updated_df = pd.concat([df_log, new_data], ignore_index=True)
                    conn.update(worksheet="발급명부", data=updated_df)
                    
                    # 신청 완료 후 슬라이더 상태 리셋
                    st.session_state.issuance_slider = (period_options[0], period_options[-1])
                    st.success("신청 완료! 담임 선생님의 승인을 기다려 주세요.")
                    st.cache_data.clear()
                    st.rerun()
