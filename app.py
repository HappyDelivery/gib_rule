import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time  # 시간 계산을 위해 필수

# --------------------------------------------------------------------------------
# 1. Page & UI Configuration (Mobile First)
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="규정집 AI 어시스턴트",
    page_icon="⚖️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 8px; height: 3em; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; background-color: #262730; border-radius: 5px; color: white; }
    .stTabs [aria-selected="true"] { background-color: #FF4B4B; color: white; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. Security & API Setup
# --------------------------------------------------------------------------------
def get_api_key():
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    else:
        return None

api_key = get_api_key()

# --------------------------------------------------------------------------------
# 3. Helper Functions (PDF Processing with Progress Bar)
# --------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def extract_text_with_pages(file_content):
    """PDF 파일에서 페이지 번호와 함께 텍스트 추출 (남은 시간 예측 기능 포함)"""
    try:
        pdf_reader = pypdf.PdfReader(file_content)
        total_pages = len(pdf_reader.pages)
        text_data = []

        # 진행바 컨테이너 생성
        progress_bar = st.progress(0, text="분석 시작...")
        start_time = time.time()

        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                text_data.append(f"--- [Page {i+1}] ---\n{text}")
            
            # 남은 시간 계산
            elapsed_time = time.time() - start_time
            if i > 0: # 0으로 나누기 방지
                avg_time_per_page = elapsed_time / (i + 1)
                remaining_pages = total_pages - (i + 1)
                estimated_time_left = avg_time_per_page * remaining_pages
            else:
                estimated_time_left = 0
            
            # UI 업데이트 (진행률 및 남은 시간)
            percent_complete = (i + 1) / total_pages
            status_text = f"⏳ 규정집 분석 중... {i+1}/{total_pages} 페이지 (약 {int(estimated_time_left)}초 남음)"
            progress_bar.progress(percent_complete, text=status_text)

        # 완료 후 진행바 제거
        progress_bar.empty()
        return "\n\n".join(text_data)

    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
        return ""

def get_available_models(api_key):
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        models.sort(key=lambda x: 'flash' not in x)
        return models
    except Exception:
        return []

def generate_gemini_response(model_name, system_prompt, user_query, temperature):
    try:
        model = genai.GenerativeModel(model_name)
        config = genai.types.GenerationConfig(temperature=temperature, max_output_tokens=2048)
        chat = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])
        response = chat.send_message(user_query, generation_config=config)
        return response.text
    except Exception as e:
        if "404" in str(e): return "Error 404: 모델을 찾을 수 없습니다."
        elif "429" in str(e): return "Error 429: 사용량이 많아 잠시 지연되었습니다."
        else: return f"오류 발생: {str(e)}"

# --------------------------------------------------------------------------------
# 4. Main Application Logic
# --------------------------------------------------------------------------------
def main():
    st.title("🏛️ 사내 규정 전문 AI 상담사")
    st.markdown("규정집에 기반하여 정확하고 친절하게 답변해 드립니다.")

    with st.expander("⚙️ 설정 및 자료 업로드", expanded=True):
        # API Key 설정
        if not api_key:
            st.warning("⚠️ Secrets 설정이 필요합니다. 임시 키를 입력하세요.")
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
            selected_model = st.selectbox("사용 모델", available_models, index=0)
        else:
            st.error("사용 가능한 모델이 없습니다.")
            st.stop()

        # 파일 업로드 로직
        uploaded_file = st.file_uploader("규정집 PDF 업로드", type=["pdf"])
        default_file_path = "regulations.pdf"
        pdf_text = ""
        
        # 파일 처리 (진행바 자동 실행됨)
        if uploaded_file:
            pdf_text = extract_text_with_pages(uploaded_file)
            if pdf_text: st.success(f"✅ 분석 완료! ({uploaded_file.name})")
        elif os.path.exists(default_file_path):
            with open(default_file_path, "rb") as f:
                pdf_text = extract_text_with_pages(f)
            if pdf_text: st.success(f"✅ 기본 규정집 로드 완료")
        else:
            st.warning("규정집 PDF 파일이 필요합니다.")

        temperature = st.slider("창의성 (0.0 권장)", 0.0, 1.0, 0.0)

    # 질의응답 로직
    if pdf_text:
        query = st.text_area("궁금한 점을 질문하세요.", height=100)
        
        if st.button("답변 받기 🚀", use_container_width=True):
            if not query:
                st.warning("질문을 입력해 주세요.")
            else:
                with st.spinner("답변을 작성 중입니다..."):
                    system_prompt = f"""
                    당신은 규정 전문 AI입니다. 아래 [규정집 내용]을 바탕으로 답변하세요.
                    
                    [규정집 내용]
                    {pdf_text}
                    
                    [답변 원칙]
                    1. 사실에 근거하여 친절하게 답변. 복잡한 내용은 리스트 형식 사용.
                    2. 관련 근거와 '페이지 번호(Page X)' 반드시 표기.
                    3. 정보가 없으면 '첨부된 자료에는 관련 정보가 없습니다.'라고 답변.
                    4. 마지막 문구: "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    
                    사용자 질문: {query}
                    """
                    response_text = generate_gemini_response(selected_model, system_prompt, query, temperature)

                st.markdown("---")
                tab1, tab2 = st.tabs(["📋 AI 답변", "🔍 원문 컨텍스트"])
                with tab1: st.markdown(response_text)
                with tab2: st.text(pdf_text[:2000] + "\n...")

if __name__ == "__main__":
    main()
