import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page Configuration & Title
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏛️",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a more professional look
st.markdown("""
    <style>
    /* General Styling */
    .stApp {
        font-family: 'Pretendard', sans-serif;
    }
    /* Main container styling */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Expander styling */
    .st-expander {
        border: 1px solid #333;
        border-radius: 10px;
    }
    /* Chat message styling */
    .st-chat-message {
        background-color: #2b2b2b;
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 2. Session State Initialization (핵심: 상태 유지)
# --------------------------------------------------------------------------------
# 앱이 재실행되어도 유지될 변수들을 session_state에 초기화합니다.
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "api_key_configured" not in st.session_state:
    st.session_state.api_key_configured = False


# --------------------------------------------------------------------------------
# 3. Helper Functions
# --------------------------------------------------------------------------------
def configure_genai(api_key):
    """API 키 설정 및 모델 목록 로드"""
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        models.sort(key=lambda x: ('flash' not in x, 'pro' not in x)) # flash, pro 우선 정렬
        st.session_state.api_key_configured = True
        return models
    except Exception as e:
        st.error(f"API 키 설정에 실패했습니다: {e}")
        st.session_state.api_key_configured = False
        return []

@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_content):
    """PDF 파일에서 텍스트 추출 (진행률 표시 포함)"""
    try:
        pdf_reader = pypdf.PdfReader(file_content)
        total_pages = len(pdf_reader.pages)
        text_data = []
        progress_bar = st.progress(0, text="규정집 분석 시작...")
        start_time = time.time()

        for i, page in enumerate(pdf_reader.pages):
            text = page.extract_text()
            if text:
                text_data.append(f"--- [Page {i+1}] ---\n{text}")
            
            elapsed_time = time.time() - start_time
            avg_time_per_page = elapsed_time / (i + 1)
            remaining_pages = total_pages - (i + 1)
            estimated_time_left = max(0, avg_time_per_page * remaining_pages)
            
            percent_complete = (i + 1) / total_pages
            status_text = f"⏳ 규정집 분석 중... {i+1}/{total_pages} 페이지 (약 {int(estimated_time_left)}초 남음)"
            progress_bar.progress(percent_complete, text=status_text)
        
        progress_bar.empty()
        return "\n\n".join(text_data)
    except Exception as e:
        st.error(f"PDF 처리 중 오류가 발생했습니다: {e}")
        return ""

def generate_response(model, query, pdf_text, temperature):
    """Gemini 모델을 통해 답변 생성"""
    system_prompt = f"""
    당신은 'GIB' 기관의 정관 및 규정 전문 AI 상담사입니다. 아래 [규정집 내용]을 바탕으로 사용자의 질문에 답변해야 합니다.

    [규정집 내용]
    {pdf_text}

    [답변 작성 5대 원칙]
    1. **근거 제시**: 답변의 핵심 내용마다 반드시 관련 근거가 되는 조항과 '페이지 번호(Page X)'를 명확히 인용하세요.
    2. **정확성**: [규정집 내용]에 없는 정보는 절대 지어내지 마세요. 정보가 없다면 "규정집 원문에서 해당 정보를 찾을 수 없습니다."라고 명확히 답변하세요.
    3. **가독성**: 복잡한 절차나 여러 항목은 번호 매기기(1., 2., 3.)나 글머리 기호(•)를 사용하여 명료하게 정리하세요.
    4. **친절한 안내자 톤**: 항상 전문가적이면서도 친절한 어조를 유지하세요.
    5. **마무리 문구**: 답변의 맨 마지막에는 반드시 다음 문구를 추가하세요: "세부 내용은 정관규정집 원문을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
    """
    try:
        model = genai.GenerativeModel(model)
        response = model.generate_content(
            [system_prompt, f"사용자 질문: {query}"],
            generation_config={"temperature": temperature}
        )
        return response.text
    except Exception as e:
        return f"⚠️ 답변 생성 중 오류가 발생했습니다: {str(e)}"

# --------------------------------------------------------------------------------
# 4. Main UI Rendering
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

# --- 설정 Expander ---
with st.expander("⚙️ 초기 설정 (API Key & 규정집)", expanded=not st.session_state.api_key_configured or not st.session_state.pdf_text):
    # API Key 입력
    api_key_input = st.text_input("Google Gemini API Key", type="password", value=st.secrets.get("GOOGLE_API_KEY", ""))
    
    if api_key_input:
        available_models = configure_genai(api_key_input)
    else:
        st.warning("Google Gemini API 키를 입력해주세요.")
        available_models = []

    if st.session_state.api_key_configured:
        st.success("API Key가 성공적으로 설정되었습니다.")
        
        # 모델 선택
        selected_model = st.selectbox("🤖 답변 생성 모델 선택", available_models)
        
        # 파일 업로드
        uploaded_file = st.file_uploader("규정집 PDF 파일 업로드", type="pdf")
        if uploaded_file:
            st.session_state.pdf_text = extract_text_from_pdf(uploaded_file)
            if st.session_state.pdf_text:
                st.success(f"✅ '{uploaded_file.name}' 분석 완료! 이제 질문을 시작할 수 있습니다.")


# --- 메인 로직: 설정이 완료되었을 때만 표시 ---
if st.session_state.api_key_configured and st.session_state.pdf_text:
    
    # 카테고리별 예시 질문 (UX 개선)
    st.markdown("---")
    st.subheader("💡 자주 묻는 질문 카테고리")
    cols = st.columns(3)
    example_questions = {
        "휴가/휴직": "연차 사용 규정과 병가 신청 절차를 알려줘.",
        "출장/경비": "국내 출장 시 교통비와 숙박비 정산 기준이 어떻게 돼?",
        "인사/평가": "승진 심사 기준과 평가 절차에 대해 설명해줘."
    }
    
    # 각 버튼에 고유한 key를 부여
    if cols[0].button("🌴 휴가/휴직", use_container_width=True, key="cat_vacation"):
        st.session_state.preset_query = example_questions["휴가/휴직"]
    if cols[1].button("✈️ 출장/경비", use_container_width=True, key="cat_biztrip"):
        st.session_state.preset_query = example_questions["출장/경비"]
    if cols[2].button("📈 인사/평가", use_container_width=True, key="cat_hr"):
        st.session_state.preset_query = example_questions["인사/평가"]
    
    # 채팅 기록 표시
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # 사용자 질문 입력
    if prompt := st.chat_input("규정집에 대해 무엇이든 물어보세요.", key="chat_input"):
        # 사용자가 선택한 예시 질문이 있다면, 그것을 사용
        if "preset_query" in st.session_state and st.session_state.preset_query:
            prompt = st.session_state.preset_query
            del st.session_state.preset_query # 사용 후 삭제

        # 사용자 질문을 채팅 기록에 추가하고 화면에 표시
        st.session_state.chat_history.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # AI 답변 생성 및 표시
        with st.chat_message("assistant"):
            with st.spinner("답변을 생성하고 있습니다..."):
                response = generate_response(
                    model=selected_model,
                    query=prompt,
                    pdf_text=st.session_state.pdf_text,
                    temperature=0.1  # 사실 기반 답변을 위해 낮은 온도로 설정
                )
                st.markdown(response)
        
        # AI 답변을 채팅 기록에 추가
        st.session_state.chat_history.append({"role": "assistant", "content": response})

else:
    st.info("👆 상단의 '초기 설정'을 열어 API Key를 입력하고 규정집 PDF 파일을 업로드해주세요.")
