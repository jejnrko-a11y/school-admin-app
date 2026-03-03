def process_multiple_images(uploaded_files):
    if not uploaded_files: return [""] * 10
    all_encoded = []
    try:
        for file in uploaded_files:
            file.seek(0)
            img = Image.open(file)
            img = ImageOps.exif_transpose(img) 
            img = img.convert('L') # 흑백 변환
            
            # --- 그림자 제거 및 스캔 보정 (호환성 높은 버전) ---
            # 1. 대비를 극대화하여 배경을 하얗게 밀어냄
            img = ImageOps.autocontrast(img, cutoff=2) 
            
            # 2. 밝은 회색(그림자)을 강제로 흰색으로 변경
            img = img.point(lambda p: p if p < 170 else 255)
            
            # 3. 글자 선명도 강화
            img = ImageEnhance.Contrast(img).enhance(2.0)
            img = ImageEnhance.Sharpness(img).enhance(1.5)
            
            # 해상도 조절
            img.thumbnail((1000, 1000), Image.Resampling.LANCZOS)
            
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=45, optimize=True)
            all_encoded.append(base64.b64encode(buf.getvalue()).decode())
        
        full_string = "NEXT".join(all_encoded)
        chunk_size = 44000
        chunks = [full_string[i:i + chunk_size] for i in range(0, len(full_string), chunk_size)]
        
        while len(chunks) < 10: chunks.append("")
        return chunks[:10]
    except Exception as e:
        st.error(f"이미지 변환 실패: {e}")
        return [""] * 10
