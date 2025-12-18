import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
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
    .st-emotion-cache-1ftv3r1 { /* 질문/답변 컨테이너 스타일 */
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 10px;
        padding: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. State & Backend Functions
# --------------------------------------------------------------------------------
# --- Session State: 앱의 상태를 기억하는 저장소 ---
if "initialized" not in st.session_state:
    st.session_state.initialized = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "user_input" not in st.session_state:
    st.session_state.user_input = ""

# --- Core Functions ---
def initialize_app():
    """
    앱 초기 실행 시 단 한 번만 호출되는 함수.
    API 설정 및 PDF 데이터 로드를 담당.
    """
    # 1. API 설정
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        model_list = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        st.session_state.model = next((m for m in model_list if 'flash' in m), model_list[0])
    except Exception as e:
        st.error(f"API 키 설정 중 오류 발생: {e}", icon="🚨")
        st.info("Streamlit Cloud의 'Settings > Secrets'에 GOOGLE_API_KEY가 올바르게 설정되었는지 확인하세요.")
        st.stop()

    # 2. PDF 로드 및 처리 (진행률 표시 기능 포함)
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"'{file_path}' 파일을 찾을 수 없습니다. GitHub 저장소 최상위 위치에 파일이 있는지 확인하세요.", icon="📂")
        st.stop()
    
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            total_pages = len(pdf_reader.pages)
            text_data = []
            
            # 진행률 표시를 위한 UI 요소 생성
            progress_bar = st.progress(0, text="규정집 분석 시작...")
            start_time = time.time()

            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    text_data.append(f"--- [Page {i+1}] ---\n{text}")

                # 진행률 및 남은 시간 계산 및 업데이트
                elapsed_time = time.time() - start_time
                avg_time_per_page = elapsed_time / (i + 1)
                remaining_pages = total_pages - (i + 1)
                estimated_time_left = max(0, avg_time_per_page * remaining_pages)
                percent_complete = (i + 1) / total_pages
                status_text = f"규정집 분석 중... {i+1}/{total_pages} 페이지 (약 {int(estimated_time_left)}초 남음)"
                progress_bar.progress(percent_complete, text=status_text)
            
            st.session_state.pdf_text = "\n\n".join(text_data)
            progress_bar.empty() # 진행바 제거

    except Exception as e:
        st.error(f"PDF 처리 중 오류 발생: {e}", icon="📄")
        st.stop()

    st.session_state.initialized = True
    st.rerun() # 초기화 완료 후 화면을 다시 그려 메인 UI를 표시

def generate_response(model, query, pdf_text):
    """AI 답변 생성 함수"""
    # 시스템 프롬프트 (AI의 역할 및 규칙 정의)
    system_prompt = "..." # 이전 코드와 동일 (생략)
    try:
        model = genai.GenerativeModel(model)
        response = model.generate_content([system_prompt, f"사용자 질문: {query}"], generation_config={"temperature": 0.1})
        return response.text
    except Exception as e:
        return f"⚠️ 답변 생성 중 오류가 발생했습니다: {e}. (Rate Limit일 수 있으니 잠시 후 다시 시도해주세요.)"

# --------------------------------------------------------------------------------
# 3. Main UI Rendering
# --------------------------------------------------------------------------------
# --- 초기화 로직 실행 ---
if not st.session_state.initialized:
    initialize_app()
else:
    # --- 초기화 완료 후 메인 UI ---
    st.title("🏛️ GIB 정관규정집 AI 상담사")
    st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
    st.divider()

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
            st.session_state.user_input = question
            st.rerun()

    # --- 직접 질문 입력 ---
    st.markdown("---")
    st.markdown("#### ✍️ 직접 질문하기")
    user_query = st.text_area("규정집 내용 중 궁금하신 사항을 입력하세요.", key="user_input", height=120)
    
    col1, col2 = st.columns([3, 2])
    if col1.button("AI에게 질문하기 🚀", type="primary", use_container_width=True):
        if user_query:
            st.session_state.chat_history.append({"role": "user", "content": user_query})
            with st.spinner("AI가 규정집을 검토하고 답변을 생성 중입니다..."):
                response_text = generate_response(st.session_state.model, user_query, st.session_state.pdf_text)
                st.session_state.chat_history.append({"role": "assistant", "content": response_text})
            st.session_state.user_input = "" # 입력창 초기화
            st.rerun()
        else:
            st.warning("질문을 입력해주세요.")

    col2.link_button("👩‍💼 전문가에게 문의하기", f"mailto:hr@example.com?subject=규정집 문의: {user_query}", use_container_width=True)

    # --- 답변 결과 표시 ---
    st.markdown("---")
    st.markdown("#### 📋 답변 결과")
    if not st.session_state.chat_history:
        st.info("질문을 입력하거나 예시 질문을 선택한 후 'AI에게 질문하기' 버튼을 누르세요.")
    else:
        # 최신 답변이 위로 오도록 역순으로 표시
        for message in reversed(st.session_state.chat_history):
            with st.chat_message(message["role"]):
                st.markdown(message["content"])
