import streamlit as st
import google.generativeai as genai
import pypdf
import os
from io import BytesIO

# --------------------------------------------------------------------------------
# 1. Page & UI Configuration (Mobile First)
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="규정집 AI 어시스턴트",
    page_icon="⚖️",
    layout="centered",  # 모바일 친화적 레이아웃
    initial_sidebar_state="collapsed"
)

# Custom CSS for Dark Mode & Mobile Optimization
st.markdown("""
    <style>
    /* 전체 폰트 및 가독성 개선 */
    .stApp {
        font-family: 'Pretendard', sans-serif;
    }
    /* 버튼 모바일 터치 최적화 */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
    }
    /* 탭 스타일링 */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #262730;
        border-radius: 5px;
        color: white;
    }
    .stTabs [aria-selected="true"] {
        background-color: #FF4B4B;
        color: white;
    }
    /* 경고 메시지 스타일 */
    .warning-box {
        padding: 1rem;
        background-color: #ffbd45;
        color: black;
        border-radius: 0.5rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. Security & API Setup
# --------------------------------------------------------------------------------
def get_api_key():
    """Secrets에서 API 키를 가져오거나 사용자 입력을 받음"""
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    else:
        return None

api_key = get_api_key()

# --------------------------------------------------------------------------------
# 3. Helper Functions (PDF Processing & Model Handling)
# --------------------------------------------------------------------------------
@st.cache_data
def extract_text_with_pages(file_content):
    """PDF 파일에서 페이지 번호와 함께 텍스트 추출"""
    try:
        pdf_reader = pypdf.PdfReader(file_content)
        text_data = []
        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                # 페이지 구분을 명확히 하기 위해 마커 삽입
                text_data.append(f"--- [Page {i+1}] ---\n{text}")
        return "\n\n".join(text_data)
    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
        return ""

def get_available_models(api_key):
    """사용 가능한 Gemini 모델 리스트 조회 (Flash 우선)"""
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # gemini-1.5-flash를 최상단으로 정렬
        models.sort(key=lambda x: 'flash' not in x)
        return models
    except Exception as e:
        return []

def generate_gemini_response(model_name, system_prompt, user_query, temperature):
    """Gemini API 호출 및 예외 처리"""
    try:
        model = genai.GenerativeModel(model_name)
        
        # Generation Config 설정
        config = genai.types.GenerationConfig(
            temperature=temperature,
            max_output_tokens=2048,
        )
        
        # Chat Session 생성
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])
        
        response = chat.send_message(user_query, generation_config=config)
        return response.text

    except Exception as e:
        error_msg = str(e)
        if "404" in error_msg:
            return "Error 404: 모델을 찾을 수 없습니다. 모델명을 확인해주세요."
        elif "429" in error_msg:
            return "Error 429: 요청이 너무 많습니다 (Rate Limit). 잠시 후 다시 시도해주세요."
        else:
            return f"오류가 발생했습니다: {error_msg}"

# --------------------------------------------------------------------------------
# 4. Main Application Logic
# --------------------------------------------------------------------------------
def main():
    st.title("🏛️ 사내 규정 전문 AI 상담사")
    st.markdown("규정집에 기반하여 정확하고 친절하게 답변해 드립니다.")

    # 4-1. 설정 (Expander로 숨김)
    with st.expander("⚙️ 설정 및 자료 업로드", expanded=True):
        # API Key 처리
        if not api_key:
            st.warning("⚠️ Secrets에 GOOGLE_API_KEY가 설정되지 않았습니다. 아래에 입력해주세요.")
            user_api_key = st.text_input("Google API Key", type="password")
            if user_api_key:
                os.environ["GOOGLE_API_KEY"] = user_api_key
                genai.configure(api_key=user_api_key)
                current_api_key = user_api_key
            else:
                st.stop()
        else:
            genai.configure(api_key=api_key)
            current_api_key = api_key
            st.success("✅ API Key가 로드되었습니다.")

        # 모델 선택
        available_models = get_available_models(current_api_key)
        if available_models:
            selected_model = st.selectbox("사용 모델 (Flash 권장)", available_models, index=0)
        else:
            st.error("사용 가능한 모델을 불러올 수 없습니다.")
            st.stop()

        # 파일 업로드 (기본 파일 로드 로직 포함)
        # GitHub 배포 시 저장소에 'regulations.pdf'가 있다면 자동으로 읽을 수 있도록 구현 가능
        uploaded_file = st.file_uploader("규정집 PDF 업로드", type=["pdf"])
        
        # (옵션) 저장소에 기본 파일이 있을 경우를 대비한 로직
        default_file_path = "regulations.pdf" 
        pdf_text = ""
        
        if uploaded_file:
            pdf_text = extract_text_with_pages(uploaded_file)
            st.info(f"📂 업로드된 파일({uploaded_file.name})을 분석합니다.")
        elif os.path.exists(default_file_path):
            with open(default_file_path, "rb") as f:
                pdf_text = extract_text_with_pages(f)
            st.info(f"📂 기본 규정집({default_file_path})을 사용합니다.")
        else:
            st.warning("규정집 PDF 파일이 필요합니다. 파일을 업로드해 주세요.")

        # 파라미터 미세 조정
        temperature = st.slider("창의성 (낮을수록 사실 기반)", 0.0, 1.0, 0.0)

    # 4-2. 입력 및 실행
    if pdf_text:
        query = st.text_area("궁금한 점을 질문하세요.", placeholder="예: 출장비 지급 규정이 어떻게 되나요?", height=100)
        
        if st.button("답변 받기 🚀", use_container_width=True):
            if not query:
                st.warning("질문을 입력해 주세요.")
            else:
                with st.spinner("규정집을 분석하고 답변을 작성 중입니다..."):
                    # 프롬프트 엔지니어링 (핵심 로직)
                    system_prompt = f"""
                    당신은 기관의 정관 및 규정 전문 AI 어시스턴트입니다. 
                    아래 제공된 [규정집 내용]을 바탕으로 사용자의 질문에 답변해야 합니다.

                    [규정집 내용]
                    {pdf_text}

                    [답변 작성 원칙]
                    1. 답변은 정확하고 사실에 근거해야 하며, 친절하고 명확한 '안내자'의 어조를 유지하세요.
                    2. 복잡한 절차나 내용은 번호가 매겨진 List 형식으로 정리하여 가독성을 높이세요.
                    3. 답변 시, 반드시 관련 근거와 해당 정보가 위치한 '페이지 번호(Page X)'를 함께 제시하세요.
                    4. 공무원, 기타 공공기관 등의 유사 사례가 있다면 참고용으로 안내하되, 반드시 출처를 표기하세요.
                    5. 만약 [규정집 내용]에 질문과 관련된 정보가 없다면, 다른 말을 지어내지 말고 정확히 "첨부된 자료에는 관련 정보가 없습니다."라고 답변하세요.
                    6. 답변의 맨 마지막에는 반드시 다음 문구를 포함하세요: 
                       "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"

                    사용자 질문: {query}
                    """

                    response_text = generate_gemini_response(selected_model, system_prompt, query, temperature)

                # 4-3. 결과 출력 (Tabs 활용)
                st.markdown("---")
                tab1, tab2 = st.tabs(["📋 AI 답변", "🔍 원문 컨텍스트"])
                
                with tab1:
                    st.markdown("### 💡 답변 결과")
                    st.markdown(response_text)
                
                with tab2:
                    st.markdown("### 📄 참조된 규정집 내용 (일부)")
                    st.caption("AI가 답변 생성을 위해 참고한 전체 텍스트 중 앞부분입니다.")
                    st.text(pdf_text[:2000] + "\n...(후략)")

    else:
        st.info("👆 먼저 설정 탭에서 규정집(PDF)을 업로드해 주세요.")

if __name__ == "__main__":
    main()
