import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page & UI Configuration
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# Custom CSS for a refined look
st.markdown("""
    <style>
    /* General Styling */
    .stApp {
        background-color: #1E1E1E;
        color: #FFFFFF;
        font-family: 'Pretendard', sans-serif;
    }
    /* Expander styling */
    .stExpander {
        border: 1px solid #4A4A4A;
        border-radius: 10px;
    }
    /* Button styling */
    .stButton>button {
        background-color: #007AFF;
        color: white;
        border-radius: 8px;
        height: 3em;
        font-weight: bold;
        border: none;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    /* Link Button for expert */
    .stLinkButton>a {
        background-color: #4A4A4A;
        color: #FFFFFF !important; /* Important to override default link color */
        border-radius: 8px;
        height: 3em;
        display: flex;
        justify-content: center;
        align-items: center;
        text-decoration: none;
    }
    /* Tabs styling */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] { background-color: #333333; border-radius: 5px; }
    .stTabs [aria-selected="true"] { background-color: #007AFF; }
    /* Success/Error boxes */
    .stAlert { border-radius: 8px; }
    </style>
""", unsafe_allow_html=True)


# --------------------------------------------------------------------------------
# 2. State Management & Helper Functions
# --------------------------------------------------------------------------------
# Initialize session state variables
if 'pdf_text' not in st.session_state:
    st.session_state.pdf_text = ""
if 'query' not in st.session_state:
    st.session_state.query = ""

@st.cache_data(show_spinner=False)
def extract_text_with_pages(file_content):
    """PDF에서 텍스트 추출 (진행률 표시 기능 포함)"""
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
            avg_time = elapsed_time / (i + 1)
            eta = avg_time * (total_pages - (i + 1))
            progress_bar.progress((i + 1) / total_pages, text=f"⏳ 분석 중... {i+1}/{total_pages} 페이지 (남은 시간: {int(eta)}초)")
        
        progress_bar.empty()
        return "\n\n".join(text_data)
    except Exception as e:
        st.error(f"PDF 처리 오류: {e}")
        return ""

def get_available_models(api_key):
    """사용 가능한 모델 목록을 동적으로 가져와서 오류 방지"""
    try:
        genai.configure(api_key=api_key)
        models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        return sorted([m for m in models if 'flash' in m]) + sorted([m for m in models if 'flash' not in m])
    except Exception:
        return []

def generate_gemini_response(api_key, model_name, system_prompt, user_query, temperature):
    """Gemini API 호출 및 정교한 예외 처리"""
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(
            system_prompt + "\n\n사용자 질문: " + user_query,
            generation_config=genai.types.GenerationConfig(temperature=temperature)
        )
        return response.text
    except Exception as e:
        error_msg = str(e)
        if "API key not valid" in error_msg:
            return "❌ 오류: Google API Key가 유효하지 않습니다. 확인 후 다시 입력해 주세요."
        elif "429" in error_msg:
            return "⏳ 오류: 요청이 너무 많습니다 (Rate Limit). 잠시 후 다시 시도해 주세요."
        elif "404" in error_msg or "not found" in error_msg:
             return f"❌ 오류: 선택하신 모델('{model_name}')을 현재 API Key로 사용할 수 없습니다. 사용 가능한 다른 모델을 선택해 주세요."
        else:
            return f"오류가 발생했습니다: {error_msg}"

# --------------------------------------------------------------------------------
# 3. Main Application UI & Logic
# --------------------------------------------------------------------------------

# --- HEADER ---
st.title("🏦 GIB 정관규정집 AI 상담사")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d')}")

# --- SETTINGS & UPLOAD EXPANDER ---
with st.expander("⚙️ 설정 및 규정집 관리", expanded=True):
    # API Key Handling
    api_key = st.text_input("Google Gemini API Key", type="password", help="API Key는 secrets에 저장하는 것이 가장 안전합니다.")
    if not api_key:
        if "GOOGLE_API_KEY" in st.secrets:
            api_key = st.secrets["GOOGLE_API_KEY"]
            st.success("✅ Secrets에서 API Key를 성공적으로 로드했습니다.")
        else:
            st.warning("API Key를 입력해주세요. Streamlit Cloud 배포 시에는 Secrets에 등록하세요.")
            st.stop()
    
    # Model Selection
    available_models = get_available_models(api_key)
    if not available_models:
        st.error("API Key가 유효하지 않거나, 사용 가능한 모델이 없습니다.")
        st.stop()
    selected_model = st.selectbox("🤖 AI 엔진 선택", available_models, help="Flash 모델은 빠르고 경제적입니다.")
    
    # PDF File Upload
    uploaded_file = st.file_uploader("새 규정집 업로드 (선택사항)", type=["pdf"])
    if uploaded_file:
        st.session_state.pdf_text = extract_text_with_pages(uploaded_file)
        if st.session_state.pdf_text:
            st.success(f"✅ '{uploaded_file.name}' 분석 완료!")
    elif not st.session_state.pdf_text: # 앱 첫 실행 시 기본 파일 로드 시도
        default_file_path = "regulations.pdf"
        if os.path.exists(default_file_path):
            with open(default_file_path, "rb") as f:
                st.session_state.pdf_text = extract_text_with_pages(f)
            if st.session_state.pdf_text:
                 st.info(f"ℹ️ 기본 규정집('{default_file_path}')을 로드했습니다.")
        else:
            st.error("규정집 PDF 파일이 필요합니다. 파일을 업로드해 주세요.")
            st.stop()

# --- CATEGORY & EXAMPLE QUESTIONS ---
st.markdown("---")
st.markdown("### 📚 카테고리별 질문 예시")

CATEGORIES = {
    "인사/복무": ["연차휴가 사용 규정", "병가 신청 절차와 필요 서류", "출장비 정산 방법"],
    "보수/수당": ["초과근무수당 지급 기준", "명절 상여금 지급일과 금액", "자격증 수당 종류 및 조건"],
    "포상/징계": ["우수직원 포상 종류", "징계위원회의 구성 및 절차", "업무상 과실에 대한 징계 기준"]
}

selected_category = st.selectbox("궁금한 분야를 선택하세요.", options=list(CATEGORIES.keys()))
example_questions = CATEGORIES[selected_category]

# Use columns for a cleaner layout of example questions
cols = st.columns(len(example_questions))
for i, question in enumerate(example_questions):
    if cols[i].button(question, use_container_width=True):
        st.session_state.query = question

# --- USER INPUT & SUBMISSION ---
st.markdown("### ✍️ 직접 질문하기")
query = st.text_area(
    "규정집 내용 중 궁금하신 사항을 입력하세요.", 
    value=st.session_state.query,
    height=150,
    placeholder="예) 육아휴직은 최대 몇 년까지 가능한가요?"
)

col1, col2 = st.columns(2)
with col1:
    if st.button("AI에게 질문하기 🚀", use_container_width=True, type="primary"):
        if not query:
            st.warning("질문을 입력해 주세요.")
        elif not st.session_state.pdf_text:
            st.error("규정집이 로드되지 않았습니다. 설정에서 파일을 업로드해 주세요.")
        else:
            system_prompt = f"""
            당신은 GIB 기관의 정관 및 규정 전문 AI 상담사입니다. 아래 [규정집 내용]을 바탕으로 사용자의 질문에 답변해야 합니다.

            [규정집 내용]
            {st.session_state.pdf_text}

            [답변 작성 5대 원칙]
            1. **정확성:** 반드시 규정집 내용에 근거하여, 페이지 번호(예: [Page 5])를 명시하며 답변합니다.
            2. **명료성:** 복잡한 절차는 번호 매기기(1., 2., 3.)를 사용해 단계별로 설명합니다.
            3. **정직성:** 규정집에 내용이 없으면 "첨부된 규정집에는 관련 정보를 찾을 수 없습니다."라고 명확히 답변합니다. 추측은 절대 금물입니다.
            4. **친절함:** 항상 친절하고 전문적인 안내자의 어조를 유지합니다.
            5. **마무리:** 모든 답변의 끝에는 다음 문구를 반드시 포함합니다: "세부 내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
            """
            
            with st.spinner("답변을 생성 중입니다..."):
                response_text = generate_gemini_response(api_key, selected_model, system_prompt, query, 0.0)

            st.session_state.last_response = response_text
            st.session_state.last_context = st.session_state.pdf_text

with col2:
    st.link_button("👩‍💼 전문가에게 문의하기", "mailto:help@gib.example.com", use_container_width=True)


# --- RESPONSE OUTPUT ---
if 'last_response' in st.session_state:
    st.markdown("---")
    st.markdown("### 💬 답변 결과")
    
    tab1, tab2 = st.tabs(["✅ AI 답변", "📄 참고 데이터"])
    with tab1:
        st.markdown(st.session_state.last_response)
    with tab2:
        st.caption("AI가 답변 생성을 위해 참고한 전체 텍스트입니다.")
        st.text_area("규정집 원문", value=st.session_state.last_context, height=300, disabled=True)
