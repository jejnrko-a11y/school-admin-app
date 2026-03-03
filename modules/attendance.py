import streamlit as st
import pandas as pd
from datetime import datetime
from utils import get_kst

def show_page(conn):
    st.title("✅ 일일 출결 체크")
    
    # 1. 날짜 선택 및 데이터 로드
    selected_date = st.date_input("출결 확인 날짜", value=get_kst().date())
    date_str = selected_date.strftime("%Y-%m-%d")

    # 학생 명부 로드
    try:
        df_students = conn.read(worksheet="학생명부", ttl=0)
        # '교사' 제외 및 번호순 정렬
        df_students = df_students[df_students['이름'] != '교사'].copy()
        df_students['번호'] = df_students['번호'].apply(lambda x: int(float(x)))
        df_students = df_students.sort_values(by='번호')
    except Exception as e:
        st.error(f"학생 명부를 불러올 수 없습니다: {e}")
        return

    # 2. 세션 상태 초기화 (날짜별 출결 데이터 관리)
    state_key = f"attn_{date_str}"
    if state_key not in st.session_state:
        # 기존 저장된 데이터가 있는지 확인
        try:
            df_history = conn.read(worksheet="출결관리", ttl=0)
            existing_today = df_history[df_history['날짜'] == date_str]
            
            if not existing_today.empty:
                # 저장된 기록이 있으면 불러오기
                initial_data = {}
                for _, row in existing_today.iterrows():
                    initial_data[int(row['번호'])] = {
                        "상태": row['출결상태'],
                        "비고": row['비고'] if pd.notna(row['비고']) else ""
                    }
                st.session_state[state_key] = initial_data
            else:
                # 기록이 없으면 모두 '출석'으로 초기화
                st.session_state[state_key] = {int(row['번호']): {"상태": "출석", "비고": ""} for _, row in df_students.iterrows()}
        except:
            st.session_state[state_key] = {int(row['번호']): {"상태": "출석", "비고": ""} for _, row in df_students.iterrows()}

    # 3. 상단 대시보드 및 일괄 작업
    c1, c2 = st.columns([2, 1])
    with c1:
        # 실시간 통계 계산
        current_data = st.session_state[state_key]
        total_cnt = len(df_students)
        absent_cnt = sum(1 for v in current_data.values() if "결석" in v['상태'])
        tardy_cnt = sum(1 for v in current_data.values() if v['상태'] in ["지각", "조퇴"])
        
        cols = st.columns(3)
        cols[0].metric("총원", f"{total_cnt}명")
        cols[1].metric("결석", f"{absent_cnt}명", delta=-absent_cnt, delta_color="inverse")
        cols[2].metric("지각/조퇴", f"{tardy_cnt}명")

    with c2:
        if st.button("🔄 전체 출석 초기화", use_container_width=True):
            for n in st.session_state[state_key]:
                st.session_state[state_key][n]["상태"] = "출석"
            st.rerun()

    st.divider()

    # 4. 학생별 출결 체크 리스트 (카드 형태)
    status_options = ["출석", "질병결석", "미인정결석", "지각", "조퇴"]
    
    for _, row in df_students.iterrows():
        num = int(row['번호'])
        name = row['이름']
        
        with st.container(border=True):
            sc1, sc2 = st.columns([1, 3])
            with sc1:
                st.markdown(f"**{num}번 {name}**")
            
            with sc2:
                # 상태 선택 (라디오 버튼 가로 배치)
                current_status = st.session_state[state_key][num]["상태"]
                new_status = st.radio(
                    f"상태_{num}",
                    status_options,
                    index=status_options.index(current_status),
                    horizontal=True,
                    label_visibility="collapsed",
                    key=f"radio_{date_str}_{num}"
                )
                st.session_state[state_key][num]["상태"] = new_status
                
                # 비고 입력
                current_remark = st.session_state[state_key][num]["비고"]
                new_remark = st.text_input(
                    f"비고_{num}",
                    value=current_remark,
                    placeholder="특이사항 입력",
                    label_visibility="collapsed",
                    key=f"note_{date_str}_{num}"
                )
                st.session_state[state_key][num]["비고"] = new_remark

    # 5. 저장 로직
    st.markdown("---")
    if st.button("🚀 출결 데이터 구글 시트에 저장하기", type="primary", use_container_width=True):
        try:
            with st.spinner("데이터 저장 중..."):
                # 저장용 데이터프레임 생성
                save_rows = []
                for _, row in df_students.iterrows():
                    n = int(row['번호'])
                    save_rows.append({
                        "날짜": date_str,
                        "번호": n,
                        "이름": row['이름'],
                        "출결상태": st.session_state[state_key][n]["상태"],
                        "비고": st.session_state[state_key][n]["비고"]
                    })
                df_new = pd.DataFrame(save_rows)
                
                # 기존 시트 데이터 읽기
                try:
                    df_existing = conn.read(worksheet="출결관리", ttl=0)
                except:
                    df_existing = pd.DataFrame(columns=["날짜", "번호", "이름", "출결상태", "비고"])
                
                # 같은 날짜 데이터 삭제 후 병합 (Upsert 효과)
                if not df_existing.empty:
                    df_existing = df_existing[df_existing['날짜'] != date_str]
                
                df_final = pd.concat([df_existing, df_new], ignore_index=True)
                
                # 시트 업데이트
                conn.update(worksheet="출결관리", data=df_final)
                st.success(f"✅ {date_str} 출결 저장이 완료되었습니다!")
                st.balloons()
        except Exception as e:
            st.error(f"저장 실패: {e}")
