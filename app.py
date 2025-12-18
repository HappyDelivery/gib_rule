import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

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
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def load_data_and_model():
    # ... (이전 코드와 동일)
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.session_state.model = next((m for m in model_list if 'flash' in m), model_list[0])
    except Exception as e:
        st.error(f"API 키 설정 중 오류가 발생했습니다: {e}", icon="🚨")
        st.stop()
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"'{file_path}' 파일을 찾을 수 없습니다. GitHub 저장소에 파일이 있는지 확인하세요.", icon="📂")
        st.stop()
    try:
        with open(file_path, "rb") as f, st.spinner():
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            text_data = []
            progress_bar = st.progress(0, text="규정집 분석 시작...")
            start_time = time.time()
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    text_data.append(f"--- [Page {i+1}] ---\n{text}")
                elapsed = time.time() - start_time
                avg_time_per_page = elapsed / (i + 1)
                remaining_pages = total_pages - (i + 1)
                eta = max(0, avg_time_per_page * remaining_pages)
                percent_complete = (i + 1) / total_pages
                status_text = f"규정집 분석 중... {i+1}/{total_pages} 페이지 (예상 남은 시간: {int(eta)}초)"
                progress_bar.progress(percent_complete, text=status_text)
            st.session_state.pdf_text = "\n\n".join(text_data)
            progress_bar.empty()
    except Exception as e:
        st.error(f"PDF 처리 중 오류가 발생했습니다: {e}", icon="📄")
        st.stop()
    st.session_state.data_loaded = True


def generate_response(model, query, pdf_text):
    """AI 답변 생성 및 사용자 친화적 오류 처리"""
    
    # ====[수정된 부분 시작]====
    system_prompt = f"""
    # **당신의 역할 및 정체성**
    당신은 오직 주어진 [규정집 원문]의 내용만을 분석하고 답변하는, 고도로 정밀한 '문서 분석 AI'입니다. 당신의 목표는 사용자의 질문에 대해 100% 규정집에 근거한 정확한 정보를 제공하는 것입니다.

    # **규칙 (반드시 지켜야 할 철칙)**
    1. **정보 출처 제한**: 당신은 오직 아래 제공된 [규정집 원문] 정보만을 사용해야 합니다. 당신이 학습한 다른 어떤 외부 지식, 웹 정보, 개인적인 추론도 절대 사용해서는 안 됩니다. 이것이 가장 중요한 제1원칙입니다.
    2. **근거 명시 의무**: 모든 답변에는 반드시 정보의 출처인 '페이지 번호(Page X)'를 명시해야 합니다. 예를 들어, "해당 내용은 규정집 15페이지에서 확인할 수 있습니다." 와 같이 구체적으로 제시해야 합니다.
    3. **없는 정보 처리**: 만약 사용자의 질문에 대한 내용이 [규정집 원문]에 없다면, 절대 답변을 지어내지 마세요. 대신, 반드시 아래와 같이 정해진 문구로만 답변해야 합니다.
       > "규정집 원문에서 해당 정보를 찾을 수 없습니다. 질문을 조금 더 구체적으로 해주시거나 다른 키워드를 사용해 보시는 것을 권장합니다."
    4. **답변 형식**: 복잡한 절차나 여러 항목은 번호 매기기나 글머리 기호를 사용해 가독성을 높여주세요.
    5. **마무리 문구**: 모든 답변의 맨 마지막에는 반드시 다음 문구를 추가해야 합니다.
       > "세부 내용은 정관규정집 원문을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"

    # **[규정집 원문]**
    {pdf_text}
    """
    # ====[수정된 부분 끝]====

    try:
        ai_model = genai.GenerativeModel(model)
        response = ai_model.generate_content(
            [system_prompt, f"사용자 질문: {query}"], 
            generation_config={"temperature": 0.0} # 창의성을 0으로 설정하여 사실 기반 답변 유도
        )
        return response.text
    except ResourceExhausted:
        return "⚠️ **API 사용량 한도 초과**\n\n무료 API 키의 분당 요청 횟수(RPM)를 초과했습니다. **약 1분 후에 다시 질문해주세요.**"
    except Exception as e:
        return f"⚠️ 답변 생성 중 오류가 발생했습니다: {e}"

# --------------------------------------------------------------------------------
# 3. Main UI Rendering (이하 내용은 모두 동일)
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
st.divider()

if not st.session_state.data_loaded:
    load_data_and_model()
    st.rerun()

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

st.markdown("---")
st.markdown("#### ✍️ 직접 질문하기")
user_query = st.text_area("규정집 내용 중 궁금하신 사항을 입력하세요.", key="user_query", height=120)

if st.button("AI에게 질문하기 🚀", type="primary", use_container_width=True):
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.spinner("AI가 규정집을 검토하고 답변을 생성 중입니다..."):
            response_text = generate_response(st.session_state.model, user_query, st.session_state.pdf_text)
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.rerun()
    else:
        st.warning("질문을 입력해주세요.", icon="⚠️")

st.markdown("---")
st.markdown("#### 📋 답변 결과")
if not st.session_state.chat_history:
    st.info("질문을 입력하거나 예시 질문을 선택한 후 'AI에게 질문하기' 버튼을 누르세요.")
else:
    for message in reversed(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
