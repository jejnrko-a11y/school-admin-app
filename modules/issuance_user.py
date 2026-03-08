import base64
import os

def render_certificate(row, fixed_info):
    # 1. 교사 직인 이미지 처리 (Base64 인코딩)
    seal_html = ""
    if os.path.exists("teacher_seal.png"):
        with open("teacher_seal.png", "rb") as f:
            seal_b64 = base64.b64encode(f.read()).decode()
            seal_html = f'<img src="data:image/png;base64,{seal_b64}" style="position:absolute; width:45px; margin-left:-35px; margin-top:-10px; opacity:0.8;">'

    # 2. 데이터 정리
    dept = str(fixed_info.get('dept', '')).replace('.0', '')
    grade = str(fixed_info.get('grade', '')).replace('.0', '')
    cls = str(fixed_info.get('cls', '')).replace('.0', '')
    num = str(row['번호']).replace('.0', '')
    name = row['이름']
    
    # 날짜 파싱 (신청일시 또는 행정날짜)
    try:
        # row['시간']에 포함된 MM/DD 추출 시도 (예: "03/10 (1교시~3교시)")
        date_part = row['시간'].split(' ')[0] # "03/10"
        m, d = date_part.split('/')
        year_str = str(datetime.now().year)
    except:
        m, d = "  ", "  "
        year_str = "20  "

    # 3. 양식 분기 처리
    if row['종류'] == "교내활동증":
        # --- [양식 2: 학생 교내 활동 확인증] ---
        title = "학 생 교 내 활 동 확 인 증"
        content_html = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:35px; border-bottom:1.5px solid black;">
                <td colspan="2" style="text-align:center; font-size:16px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:80px;">
                <td style="width:15%; border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; line-height:1.2;">교내<br>활동<br>사유</td>
                <td style="width:85%; border:1px solid black; padding:10px; text-align:left; vertical-align:top;">{row['사유']}</td>
            </tr>
            <tr style="height:45px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold;">장소</td>
                <td style="border:1px solid black; padding-left:10px; text-align:left;">{row['행선지']}</td>
            </tr>
            <tr style="height:45px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold;">시간</td>
                <td style="border:1px solid black; text-align:center; font-size:17px; letter-spacing:1px;">
                    {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:30px; font-size:18px; font-weight:bold;">상기 학생의 교내활동을 확인함.</div>
        """
        teacher_label = "담당교사 :"
    else:
        # --- [양식 1: 조퇴, 외출증] ---
        title = "조 퇴 ,  외 출 증"
        content_html = f"""
        <table style="width:100%; border-collapse:collapse; border:1.5px solid black;">
            <tr style="background-color:#E7E6E6; height:35px; border-bottom:1.5px solid black;">
                <td colspan="2" style="text-align:center; font-size:16px; font-weight:bold; letter-spacing:2px;">
                    {dept} 과 &nbsp;&nbsp; {grade} 학년 &nbsp;&nbsp; {cls} 반 &nbsp;&nbsp; {num} 번 &nbsp;&nbsp; 성명: {name}
                </td>
            </tr>
            <tr style="height:110px;">
                <td style="width:15%; border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:18px; letter-spacing:5px;">사유</td>
                <td style="width:85%; border:1px solid black; padding:10px; text-align:left; vertical-align:top; font-size:17px;">{row['사유']} (행선지: {row['행선지']})</td>
            </tr>
            <tr style="height:45px;">
                <td style="border:1px solid black; background:#f0f0f0; text-align:center; font-weight:bold; font-size:18px; letter-spacing:5px;">시간</td>
                <td style="border:1px solid black; text-align:center; font-size:17px;">
                     {row['시간'].split('(')[1].replace(')', '') if '(' in row['시간'] else row['시간']}
                </td>
            </tr>
        </table>
        <div style="text-align:center; margin-top:30px; font-size:18px; font-weight:bold;">상기 학생의 조퇴, 외출을 허가함.</div>
        """
        teacher_label = "담 임 :"

    # 공통 하단부 (날짜, 교사, 학교명)
    html_layout = f"""
    <div style="width:480px; margin:0 auto; border:2px solid black; padding:0; background:white; color:black; font-family:'Malgun Gothic', 'Dotum', sans-serif;">
        <!-- 헤더 제목 -->
        <div style="border-bottom:1.5px solid black; background-color:#D9E1F2; padding:10px; text-align:center;">
            <h2 style="margin:0; font-size:22px; letter-spacing:3px;">{title}</h2>
        </div>
        
        <!-- 본문 내용 -->
        <div style="padding:0px;">
            {content_html}
        </div>

        <!-- 하단 서명 섹션 -->
        <div style="text-align:center; padding:20px 0;">
            <div style="font-size:18px; margin-bottom:15px; letter-spacing:2px;">
                {year_str} 년 &nbsp;&nbsp;&nbsp; {m} 월 &nbsp;&nbsp;&nbsp; {d} 일
            </div>
            <div style="font-size:18px; font-weight:bold; margin-bottom:20px; position:relative;">
                {teacher_label} &nbsp;&nbsp; 오 정 은 &nbsp;&nbsp;&nbsp;&nbsp;&nbsp; (인)
                {seal_html}
            </div>
            <div style="border-top:1.5px solid black; padding:12px 0; font-size:22px; font-weight:bold; letter-spacing:5px;">
                경 기 기 계 공 업 고 등 학 교
            </div>
        </div>
    </div>
    
    <style>
        @media print {{
            header, footer, .stButton, [data-testid="stHeader"] {{ display:none !important; }}
            .main .block-container {{ padding: 0 !important; }}
        }}
    </style>
    """
    
    st.markdown(html_layout, unsafe_allow_html=True)
    components.html("<script>window.parent.print();</script>", height=0)
