import streamlit as st
import google.generativeai as genai
import pypdf
import os

# --------------------------------------------------------------------------------
# 1. 기본 설정 및 디자인
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏢",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# 다크모드 및 모바일 최적화 CSS
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button {
        width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold;
        background-color: #FF4B4B; color: white; border: none;
    }
    .stButton > button:hover { background-color: #FF2B2B; color: white; }
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 10px; }
    .stTabs [data-baseweb="tab"] {
        height: 50px; background-color: #262730; border-radius: 5px; color: white;
    }
    .stTabs [aria-selected="true"] { background-color: #4B90FF; color: white; }
    /* 숨김 처리할 요소들 (혹시 모를 잔여물) */
    [data-testid="stFileUploader"] { display: none; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. 내부 로직 (API 및 PDF 처리 - 사용자에게 안 보임)
# --------------------------------------------------------------------------------
def get_api_key():
    """Secrets에서 조용히 키 로드"""
    if "GOOGLE_API_KEY" in st.secrets:
        return st.secrets["GOOGLE_API_KEY"]
    return None

def configure_genai(api_key):
    """모델 설정 (Flash 강제 사용)"""
    try:
        genai.configure(api_key=api_key)
        return True
    except:
        return False

@st.cache_data(show_spinner=False)
def load_local_pdf(file_path):
    """서버(GitHub)에 있는 PDF 파일 로드"""
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            text_data = []
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    text_data.append(f"--- [Page {i+1}] ---\n{text}")
            return "\n\n".join(text_data)
    except Exception:
        return None

def generate_response(system_prompt, user_query):
    """Gemini 응답 생성 (Temperature 0.0 고정)"""
    try:
        # Flash 모델 우선 사용
        model = genai.GenerativeModel('gemini-1.5-flash')
        config = genai.types.GenerationConfig(temperature=0.0) # 사실 기반 답변 강화
        
        chat = model.start_chat(history=[
            {"role": "user", "parts": [system_prompt]}
        ])
        response = chat.send_message(user_query, generation_config=config)
        return response.text
    except Exception as e:
        return "죄송합니다. 일시적인 시스템 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."

# --------------------------------------------------------------------------------
# 3. 메인 화면 구성
# --------------------------------------------------------------------------------
def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")
    
    # API 키 로드 (실패 시에만 경고)
    api_key = get_api_key()
    if not api_key:
        st.error("시스템 설정 오류: API Key를 찾을 수 없습니다. 관리자에게 문의하세요.")
        st.stop()
    
    configure_genai(api_key)

    # PDF 파일 로드 (regulations.pdf 고정)
    file_path = "regulations.pdf"
    
    if os.path.exists(file_path):
        pdf_text = load_local_pdf(file_path)
    else:
        st.error("⚠️ 시스템 오류: 'regulations.pdf' 파일을 찾을 수 없습니다. (파일명 확인 필요)")
        st.stop()

    if not pdf_text:
        st.error("⚠️ 문서 처리 오류: 규정집 내용을 읽을 수 없습니다.")
        st.stop()

    # 3-1. 카테고리 선택 및 예시 질문 동적 생성
    st.markdown("### 상담 분야를 선택하세요")
    
    categories = {
        "인사 (승진, 채용, 평가)": "4급 승진을 위한 최저 소요 연수는 몇 년인가요?",
        "급여 (호봉, 수당, 퇴직금)": "가족수당 지급 기준과 금액이 궁금합니다.",
        "복무 (휴가, 출장, 근무시간)": "연차 휴가 이월 규정에 대해 알려주세요.",
        "복지 (학자금, 의료비 지원)": "자녀 학자금 보조 수당 신청 절차는 어떻게 되나요?",
        "기타 (징계, 감사 등)": "징계 위원회 구성 요건이 어떻게 되나요?"
    }
    
    selected_category = st.selectbox(
        "분야 선택",
        options=list(categories.keys()),
        label_visibility="collapsed"
    )

    # 선택된 카테고리에 맞는 예시 질문 가져오기
    example_question = categories[selected_category]

    # 3-2. 질문 입력창
    st.markdown("---")
    query = st.text_area(
        "질문 내용", 
        placeholder=f"예시: {example_question}",
        height=100
    )

    # 3-3. 실행 및 결과
    if st.button("상담 시작하기 🚀", use_container_width=True):
        if not query:
            st.warning("질문 내용을 입력해 주세요.")
        else:
            with st.spinner("규정집을 분석 중입니다..."):
                # 프롬프트 구성
                system_prompt = f"""
                당신은 GIB(기관명)의 정관 및 규정 전문 AI 상담사입니다.
                사용자는 현재 '{selected_category}' 분야에 대해 질문했습니다.
                아래 [규정집 내용]을 바탕으로 답변하세요.

                [규정집 내용]
                {pdf_text}

                [답변 작성 원칙]
                1. 답변은 정확하고 사실에 근거해야 하며, 친절하고 명확한 '안내자' 어조를 사용하세요.
                2. 절차나 조건은 번호(List)를 매겨 가독성 있게 정리하세요.
                3. 반드시 '근거 규정'과 '페이지 번호(Page X)'를 명시하세요.
                4. 규정집에 없는 내용은 "관련 정보가 없습니다."라고 명확히 답하세요. (지어내지 말 것)
                5. 답변 끝인사: "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"

                사용자 질문: {query}
                """
                
                response_text = generate_response(system_prompt, query)

            # 결과 출력
            st.markdown("---")
            tab1, tab2 = st.tabs(["💬 답변 결과", "📖 근거 자료"])
            
            with tab1:
                st.markdown(response_text)
            
            with tab2:
                st.info("AI가 답변을 생성하기 위해 참고한 규정집의 일부입니다.")
                st.text(pdf_text[:1500] + "\n...(중략)")

if __name__ == "__main__":
    main()
