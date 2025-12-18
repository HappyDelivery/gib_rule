import streamlit as st
import google.generativeai as genai
import pypdf
import os

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="GIB 정관규정집 AI 상담사", page_icon="🏢", layout="centered")

st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #FF4B4B; color: white; }
    /* 질문 입력창 스타일 */
    div[data-baseweb="textarea"] { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. PDF 텍스트 추출 함수 (최적화)
def extract_text_from_pdf(file_path):
    if not os.path.exists(file_path):
        return None, "파일을 찾을 수 없습니다."
    
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            text_data = []
            
            # 진행 상태 표시를 위해 텍스트 추출 시각화
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i in range(total_pages):
                page = pdf_reader.pages[i]
                content = page.extract_text()
                if content:
                    text_data.append(f"--- [Page {i+1}] ---\n{content}")
                
                # 진행률 업데이트 (매 10페이지마다)
                if i % 10 == 0 or i == total_pages - 1:
                    progress = (i + 1) / total_pages
                    progress_bar.progress(progress)
                    status_text.text(f"📄 규정집 분석 중... ({i+1}/{total_pages} 페이지)")
            
            progress_bar.empty()
            status_text.empty()
            
            full_text = "\n\n".join(text_data)
            if len(full_text.strip()) < 100:
                return None, "글자를 읽을 수 없는 PDF입니다. (이미지 스캔본 여부 확인 필요)"
            
            return full_text, "OK"
    except Exception as e:
        return None, f"오류 발생: {str(e)}"

# 3. 메인 로직
def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")

    # API 설정
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 API Key가 설정되지 않았습니다.")
        return
    genai.configure(api_key=api_key)

    # 4. 파일 로딩 (세션 상태 활용하여 1회만 실행)
    if "pdf_content" not in st.session_state:
        file_path = "regulations.pdf"
        with st.spinner("🚀 규정집 데이터를 초기화하고 있습니다. 잠시만 기다려 주세요..."):
            content, msg = extract_text_from_pdf(file_path)
            if content:
                st.session_state.pdf_content = content
                st.success("✅ 규정집 분석이 완료되었습니다!")
            else:
                st.error(f"❌ {msg}")
                st.info("Tip: GitHub에 'regulations.pdf' 파일이 있고 글자가 드래그 가능한 파일인지 확인해 주세요.")
                return
    
    # 5. 상담 카테고리 및 질문 화면
    st.markdown("### 상담 분야를 선택하세요")
    
    categories = {
        "인사 (승진, 채용, 평가)": "4급 승진을 위한 최저 소요 연수는 몇 년인가요?",
        "급여 (호봉, 수당, 퇴직금)": "가족수당 지급 기준과 금액이 궁금합니다.",
        "복무 (휴가, 출장, 근무시간)": "연차 휴가 이월 규정에 대해 알려주세요.",
        "복지 (학자금, 의료비 지원)": "자녀 학자금 보조 수당 신청 절차는 어떻게 되나요?",
        "기타 (징계, 감사 등)": "징계 위원회 구성 요건이 어떻게 되나요?"
    }
    
    selected_cat = st.selectbox("분야", options=list(categories.keys()), label_visibility="collapsed")
    
    st.markdown("---")
    query = st.text_area("질문 내용을 입력하세요", 
                        placeholder=f"예시: {categories[selected_cat]}", 
                        height=120)

    if st.button("상담 시작하기 🚀"):
        if not query:
            st.warning("질문을 입력해 주세요.")
        else:
            with st.spinner("규정집에서 답변을 찾고 있습니다..."):
                try:
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    system_prompt = f"""
                    당신은 GIB 기관의 정관 및 규정 전문 상담사입니다.
                    아래 제공된 [규정집 내용]만을 바탕으로 답변하세요.

                    [규정집 내용]
                    {st.session_state.pdf_content}

                    [작성 규칙]
                    1. 답변은 친절하고 명확하게 작성하세요.
                    2. 반드시 관련 근거 규정명과 페이지 번호를 명시하세요.
                    3. 규정집에 없는 내용은 "첨부된 자료에는 관련 정보가 없습니다."라고 답하세요.
                    4. 마지막 인사말: "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    """
                    
                    response = model.generate_content([system_prompt, f"질문: {query}"])
                    
                    st.markdown("### 💡 답변 결과")
                    st.info(response.text)
                    
                except Exception as e:
                    st.error(f"답변 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
