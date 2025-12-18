import streamlit as st
import google.generativeai as genai
import pypdf
import os
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page Configuration & Style
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏛️",
    layout="centered"
)

st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton>button { border-radius: 8px; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. State Management & Backend Functions
# --------------------------------------------------------------------------------
# --- Session State: 앱의 상태(채팅 기록 등)를 기억하는 저장소 ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Core Functions ---
@st.cache_resource(show_spinner="AI 엔진 초기화 및 규정집 로딩 중...")
def load_ai_and_data():
    """
    앱의 핵심 리소스(AI 모델, PDF 데이터)를 로드하고 캐싱합니다.
    이 함수는 앱 실행 시 단 한 번만 실행됩니다.
    """
    # 1. API 설정
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        model = next((m for m in model_list if 'flash' in m), model_list[0])
    except Exception as e:
        st.error(f"API 키 설정 중 오류 발생: {e}", icon="🚨")
        st.stop()

    # 2. PDF 로드 및 텍스트 추출
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"'{file_path}' 파일을 찾을 수 없습니다. GitHub 저장소에 파일이 올바르게 위치해 있는지 확인하세요.", icon="📂")
        st.stop()
    
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            pdf_text = "\n\n".join(
                f"--- [Page {i+1}] ---\n{page.extract_text()}" 
                for i, page in enumerate(pdf_reader.pages) if page.extract_text()
            )
    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}", icon="📄")
        st.stop()

    return model, pdf_text

def generate_response(model, query, pdf_text):
    """AI 답변 생성 함수"""
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
        return f"⚠️ 답변 생성 중 오류가 발생했습니다: {e}. (Rate Limit일 수 있으니 잠시 후 다시 시도해주세요.)"

# --------------------------------------------------------------------------------
# 3. Main UI Rendering
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
st.divider()

# --- AI 엔진 및 데이터 로드 (캐싱되어 2번째부터는 즉시 반환) ---
# 이 부분에서 처음 접속 시 로딩 스피너가 표시됩니다.
MODEL, PDF_TEXT = load_ai_and_data()

# --- 카테고리별 질문 예시 ---
st.markdown("#### 💬 카테고리별 질문 예시")
example_questions = {
    "인사/복무": ["연차휴가 사용 규정", "병가 신청 절차와 필요 서류", "육아휴직 신청 자격"],
    "보수/경비": ["출장비 정산 방법", "시간외근무수당 지급 기준", "경조사비 지급 규정"],
    "기타": ["법인카드 사용 시 주의사항", "정보보안 관련 규정", "차량 운행 및 관리 규정"],
}
selected_category = st.selectbox("궁금한 분야를 선택하세요.", list(example_questions.keys()))

cols = st.columns(len(example_questions[selected_category]))
for i, question in enumerate(example_questions[selected_category]):
    if cols[i].button(question, use_container_width=True):
        st.session_state.user_query = question
        st.rerun()

# --- 직접 질문 입력 ---
st.markdown("---")
st.markdown("#### ✍️ 직접 질문하기")
user_query = st.text_area(
    "규정집 내용 중 궁금하신 사항을 입력하세요.", 
    key="user_query", 
    height=120,
    placeholder="예시: 국내 출장 시 숙박비 상한액은 얼마인가요?"
)

if st.button("AI에게 질문하기 🚀", type="primary", use_container_width=True):
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.spinner("AI가 규정집을 검토하고 답변을 생성 중입니다..."):
            response_text = generate_response(MODEL, user_query, PDF_TEXT)
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        # 입력창 초기화 로직 제거 (오류 방지)
        st.rerun() # 채팅 기록을 즉시 화면에 반영하기 위해 재실행
    else:
        st.warning("질문을 입력해주세요.", icon="⚠️")

# --- 답변 결과 표시 ---
st.markdown("---")
st.markdown("#### 📋 답변 결과")
if not st.session_state.chat_history:
    st.info("질문을 입력하거나 예시 질문을 선택한 후 'AI에게 질문하기' 버튼을 누르세요.")
else:
    for message in reversed(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
