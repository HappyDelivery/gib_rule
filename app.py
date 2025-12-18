import streamlit as st
import google.generativeai as genai
import pypdf
import os
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page Configuration (must be the first Streamlit command)
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏦",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --------------------------------------------------------------------------------
# 2. Custom CSS for a Polished Look
# --------------------------------------------------------------------------------
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;700&display=swap');
    
    html, body, [class*="st-"] {
        font-family: 'Noto Sans KR', sans-serif;
    }
    .stApp {
        background-color: #1c1c1e; /* Slightly softer dark background */
        color: #E0E0E0;
    }
    h1, h3 {
        color: #FFFFFF;
    }
    h1 {
        border-bottom: 2px solid #0A84FF;
        padding-bottom: 10px;
    }
    /* Tab styling for a modern look */
    .stTabs [data-baseweb="tab-list"] {
        gap: 24px;
        border-bottom: 2px solid #3A3A3C;
    }
    .stTabs [data-baseweb="tab"] {
        padding: 10px 15px;
        background-color: transparent;
        border: none;
        color: #8E8E93;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        border-bottom: 3px solid #0A84FF;
        color: #FFFFFF;
    }
    /* Primary button (Red color as requested) */
    .stButton>button[kind="primary"] {
        background-color: #FF3B30;
        color: white;
        border: none;
        border-radius: 10px;
        height: 3.2em;
        font-weight: bold;
        font-size: 16px;
    }
    /* Secondary button (example questions) */
    .stButton>button:not([kind="primary"]) {
        background-color: #2C2C2E;
        color: #E0E0E0;
        border: 1px solid #3A3A3C;
        border-radius: 8px;
    }
    .st-emotion-cache-1r6slb0 { /* Target specific info box */
        background-color: #2C2C2E;
        border: 1px solid #3A3A3C;
        border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 3. Backend Functions & Initialization
# --------------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def extract_text_from_pdf(file_path):
    """PDF 파일에서 텍스트를 추출하고 캐시에 저장합니다. (효율성 극대화)"""
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            text_data = [f"--- [Page {i+1}] ---\n{page.extract_text()}" 
                         for i, page in enumerate(pdf_reader.pages) if page.extract_text()]
        return "\n\n".join(text_data)
    except FileNotFoundError:
        return "error_not_found"
    except Exception as e:
        return f"error_processing: {e}"

def initialize_app():
    """앱 첫 실행 시 API Key 설정 및 PDF 데이터 로드"""
    # API Key 로드
    if 'api_key' not in st.session_state:
        try:
            st.session_state.api_key = st.secrets["GOOGLE_API_KEY"]
            genai.configure(api_key=st.session_state.api_key)
        except (KeyError, FileNotFoundError):
            st.error("관리자 오류: GOOGLE_API_KEY가 앱 Secrets에 설정되지 않았습니다.")
            st.stop()

    # PDF 데이터 로드
    if 'pdf_text' not in st.session_state:
        with st.spinner("AI 상담사를 준비하고 있습니다..."):
            pdf_text = extract_text_from_pdf("regulations.pdf")
            if "error_not_found" in pdf_text:
                st.error("관리자 오류: 'regulations.pdf' 파일을 찾을 수 없습니다.")
                st.stop()
            elif "error_processing" in pdf_text:
                st.error(f"관리자 오류: PDF 파일을 처리하는 중 문제가 발생했습니다. ({pdf_text})")
                st.stop()
            st.session_state.pdf_text = pdf_text

def get_gemini_response(query, pdf_context):
    """Gemini API를 호출하여 답변을 생성합니다."""
    system_prompt = f"""
    당신은 GIB 기관의 정관 및 규정 전문 AI 상담사입니다. 아래 [규정집 내용]을 바탕으로 사용자의 질문에 답변해야 합니다.

    [규정집 내용]
    {pdf_context}

    [답변 작성 5대 원칙]
    1. **정확성:** 반드시 규정집 내용에 근거하여, 페이지 번호(예: [Page 5])를 명시하며 답변합니다.
    2. **명료성:** 복잡한 절차는 번호 매기기(1., 2., 3.)를 사용해 단계별로 설명합니다.
    3. **정직성:** 규정집에 내용이 없으면 "첨부된 규정집에는 관련 정보를 찾을 수 없습니다."라고 명확히 답변합니다. 추측은 절대 금물입니다.
    4. **친절함:** 항상 친절하고 전문적인 안내자의 어조를 유지합니다.
    5. **마무리:** 모든 답변의 끝에는 다음 문구를 반드시 포함합니다: "세부 내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
    """
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        response = model.generate_content(
            system_prompt + "\n\n사용자 질문: " + query,
            generation_config=genai.types.GenerationConfig(temperature=0.0)
        )
        return response.text
    except Exception as e:
        if "429" in str(e):
            return "⏳ 오류: 현재 요청이 많아 잠시 지연되고 있습니다. 잠시 후 다시 시도해 주세요."
        return f"API 호출 중 오류가 발생했습니다: {e}"

# --------------------------------------------------------------------------------
# 4. Main Application UI
# --------------------------------------------------------------------------------

# 앱의 기본 UI를 먼저 그리고, 필요한 초기화를 진행합니다.
st.title("🏦 GIB 정관규정집 AI 상담사")
st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")

# 초기화 실행
initialize_app()

# --- CATEGORY TABS & EXAMPLE QUESTIONS ---
st.header("💬 카테리별 질문 예시")
st.write("궁금한 분야를 선택하고, 예시 질문을 눌러 바로 질문해 보세요.")

CATEGORIES = {
    "🧑‍💼 인사/복무": ["연차휴가 사용 규정", "병가 신청 절차", "출장비 정산 방법"],
    "💰 보수/급여": ["시간외근무수당 지급 기준", "명절 상여금 지급일", "자격증 수당 종류"],
    "📋 경조사/기타": ["경조사 지원 기준", "법인카드 사용 지침", "보안 규정 위반 시 조치"]
}

tabs = st.tabs(list(CATEGORIES.keys()))
for i, (category, questions) in enumerate(CATEGORIES.items()):
    with tabs[i]:
        cols = st.columns(len(questions))
        for j, question in enumerate(questions):
            if cols[j].button(question, key=f"{category}_{j}", use_container_width=True):
                st.session_state.query = question
                st.rerun()

# --- USER INPUT & SUBMISSION ---
st.header("✍️ 직접 질문하기")
query = st.text_area(
    "label",
    value=st.session_state.get('query', ''),
    height=150,
    placeholder="예) 육아휴직은 최대 몇 년까지 가능한가요?",
    label_visibility="collapsed"
)

if st.button("AI에게 질문하기 🚀", use_container_width=True, type="primary"):
    if not query:
        st.warning("질문을 입력해 주세요.")
    else:
        with st.spinner("규정집을 검토하고 답변을 생성하는 중..."):
            response = get_gemini_response(query, st.session_state.pdf_text)
            st.session_state.last_response = response
            st.session_state.query = query # 마지막 질문 기억

# --- RESPONSE OUTPUT ---
st.header("📋 답변 결과")
if 'last_response' in st.session_state:
    st.info(st.session_state.last_response)
else:
    st.info("질문을 입력하거나 예시 질문을 선택한 후 'AI에게 질문하기' 버튼을 누르세요.")
