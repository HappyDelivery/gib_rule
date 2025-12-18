import time  # <--- 상단 import 모음에 이 줄을 꼭 추가하세요!

# ... (기존 코드 생략) ...

# --------------------------------------------------------------------------------
# 3. Helper Functions 수정 (Progress Bar & Time Estimation 추가)
# --------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)  # 기본 스피너 끄기 (우리가 직접 만들 것이므로)
def extract_text_with_pages(file_content):
    """PDF 파일에서 페이지 번호와 함께 텍스트 추출 (진행률 표시 기능 포함)"""
    try:
        # 파일을 읽기 위한 Reader 객체 생성
        pdf_reader = pypdf.PdfReader(file_content)
        total_pages = len(pdf_reader.pages)
        text_data = []

        # 1. 진행률 표시줄 생성
        progress_bar = st.progress(0, text="분석 시작...")
        start_time = time.time()  # 시작 시간 기록

        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                text_data.append(f"--- [Page {i+1}] ---\n{text}")
            
            # 2. 남은 시간 계산 로직
            elapsed_time = time.time() - start_time
            avg_time_per_page = elapsed_time / (i + 1)
            remaining_pages = total_pages - (i + 1)
            estimated_time_left = avg_time_per_page * remaining_pages
            
            # 3. 진행률 및 텍스트 업데이트
            percent_complete = (i + 1) / total_pages
            status_text = f"⏳ 규정집 분석 중... {i+1}/{total_pages} 페이지 (약 {int(estimated_time_left)}초 남음)"
            progress_bar.progress(percent_complete, text=status_text)

        # 완료 후 정리
        progress_bar.empty()  # 진행바 제거
        return "\n\n".join(text_data)

    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
        return ""

# ... (나머지 코드는 그대로 유지) ...
