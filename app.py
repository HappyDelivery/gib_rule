import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page Configuration & Essential Setup
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏛️",
    layout="centered"
)

# Custom CSS for refined UI
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton>button { border-radius: 8px; }
    .st-emotion-cache-1ftv3r1 {
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. Secure API & Data Loading (Backend Logic)
# --------------------------------------------------------------------------------
# --- Session State Initialization ---
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --- Functions ---
@st.cache_resource(show_spinner="AI 엔진을 준비하는 중입니다...")
def configure_api():
    """Secrets에서 API 키를 가져와 GenAI를 설정합니다."""
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        # 사용 가능한 모델 중 flash 모델을 우선적으로 찾음
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        flash_model = next((m for m in model_list if 'flash' in m), None)
        return flash_model if flash_model else model_list[0]
    except KeyError:
        st.error("오류: `secrets.toml`에 GOOGLE_API_KEY가 설정되지 않았습니다.")
        st.info("Streamlit Cloud의 'Settings > Secrets'에서 API 키를 추가해주세요.")
        st.stop()
    except Exception as e:
        st.error(f"API 설정 중 오류 발생: {e}")
        st.stop()

@st.cache_data(show_spinner="규정집 원문을 로드하고 있습니다...")
def load_and_process_pdf(file_path):
    """지정된 경로의 PDF 파일을 로드하고 텍스트를 추출합니다."""
    if not os.path.exists(file_path):
        st.error(f"오류: '{file_path}' 파일을 찾을 수 없습니다. GitHub 저장소에 파일이 올바르게 위치해 있는지 확인하세요.")
        st.stop()
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            text_data = [f"--- [Page {i+1}] ---\n{page.extract_text()}" for i, page in enumerate(pdf_reader.pages) if page.extract_text()]
        return "\n\n".join(text_data)
    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}")
        st.stop()

def generate_response(model, query, pdf_text):
    """AI 답변 생성"""
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
        response = model.generate_content([system_prompt, f"사용자 질문: {query}"], generation_config={"temperature": 0.1})
        return response.text
    except Exception as e:
        return f"⚠️ 답변 생성 중 오류가 발생했습니다: {e}. 잠시 후 다시 시도해주세요."

# --- Initial Loading ---
SELECTED_MODEL = configure_api()
st.session_state.pdf_text = load_and_process_pdf("regulations.pdf")

# --------------------------------------------------------------------------------
# 3. Main UI & Interaction
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"최종 업데이트: {datetime.now().strftime('%Y-%m-%d')}")
st.divider()

# --- 예시 질문 UI ---
st.markdown("#### 💬 카테고리별 질문 예시")
st.markdown("궁금한 분야를 선택하시면, 자주 묻는 질문을 확인할 수 있습니다.")

example_questions = {
    "인사/복무": [
        "연차휴가 사용 규정",
        "병가 신청 절차와 필요 서류",
        "육아휴직 신청 자격과 기간",
    ],
    "보수/경비": [
        "출장비 정산 방법",
        "시간외근무수당 지급 기준",
        "경조사비 지급 규정",
    ],
    "기타": [
        "법인카드 사용 시 주의사항",
        "정보보안 관련 규정",
        "차량 운행 및 관리 규정",
    ]
}

selected_category = st.selectbox("궁금한 분야를 선택하세요.", options=list(example_questions.keys()))

st.write("") # 여백
cols = st.columns(len(example_questions[selected_category]))
for i, question in enumerate(example_questions[selected_category]):
    if cols[i].button(question, use_container_width=True):
        st.session_state.user_input = question

# --- 직접 질문 UI ---
st.markdown("---")
st.markdown("#### ✍️ 직접 질문하기")
st.markdown("규정집 내용 중 궁금하신 사항을 자유롭게 입력하세요.")
user_query = st.text_area("질문 입력", key="user_input", height=120, placeholder="예시: 국내 출장 시 숙박비 상한액은 얼마인가요?")

# --- 액션 버튼 ---
col1, col2 = st.columns([3, 2])
ai_button = col1.button("AI에게 질문하기 🚀", type="primary", use_container_width=True)
# 담당자 이메일 주소는 실제 주소로 변경하세요.
col2.link_button("👩‍💼 전문가에게 문의하기", "mailto:hr@example.com?subject=규정집 관련 문의", use_container_width=True)


# --- 채팅 기록 및 답변 생성 ---
st.markdown("---")
st.markdown("#### 📋 답변 결과")

if ai_button and user_query:
    st.session_state.chat_history.append({"role": "user", "content": user_query})
    with st.spinner("AI가 규정집을 검토하고 답변을 생성 중입니다..."):
        response_text = generate_response(SELECTED_MODEL, user_query, st.session_state.pdf_text)
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
    st.session_state.user_input = "" # 질문 후 입력창 초기화
    st.rerun() # 채팅 기록을 즉시 화면에 반영

# 채팅 기록 표시
if not st.session_state.chat_history:
    st.info("좌측 하단의 'AI에게 질문하기' 버튼을 눌러 답변을 받아보세요.")
else:
    for message in reversed(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
