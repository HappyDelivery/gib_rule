import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime

# --------------------------------------------------------------------------------
# 1. Page & Luxury UI Style
# --------------------------------------------------------------------------------
st.set_page_config(
    page_title="GIB 정관규정집 AI 상담사",
    page_icon="🏢",
    layout="centered"
)

# 고급스러운 다크 테마 커스텀 CSS
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;700&display=swap');
    
    html, body, [class*="css"] { font-family: 'Noto Sans KR', sans-serif; }
    
    /* 메인 배경 및 카드 스타일 */
    .main { background-color: #0E1117; }
    div[data-testid="stExpander"] {
        border: 1px solid #2d2d2d;
        border-radius: 15px;
        background-color: #161b22;
    }
    
    /* 고급스러운 타이틀 스타일 */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        background: linear-gradient(90deg, #FFFFFF, #888888);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    
    /* 버튼 애니메이션 */
    .stButton > button {
        border-radius: 10px;
        background: linear-gradient(45deg, #2b5876, #4e4376);
        color: white;
        border: none;
        transition: all 0.3s ease;
        height: 3.5rem;
        font-size: 1.1rem;
    }
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.3);
    }
    
    /* 탭 스타일 */
    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        background-color: #1f2937;
        border-radius: 8px 8px 0 0;
        padding: 10px 20px;
        color: #9ca3af;
    }
    .stTabs [aria-selected="true"] {
        background-color: #3b82f6 !important;
        color: white !important;
    }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. API & Model Setup (Error Handling)
# --------------------------------------------------------------------------------
def setup_genai():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
        return True
    return False

# --------------------------------------------------------------------------------
# 3. Core Logic (PDF & AI)
# --------------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_and_process_pdf(file_source):
    """PDF를 읽어 페이지별로 텍스트를 구조화합니다."""
    try:
        reader = pypdf.PdfReader(file_source)
        full_text = []
        progress_text = "📖 규정 전문 분석 중..."
        bar = st.progress(0, text=progress_text)
        
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                full_text.append(f"[문서 페이지: {i+1}]\n{text}")
            
            # 진행률 표시
            pct = (i + 1) / len(reader.pages)
            bar.progress(pct, text=f"{progress_text} ({i+1}/{len(reader.pages)}p)")
        
        time.sleep(0.5)
        bar.empty()
        return "\n\n".join(full_text)
    except Exception as e:
        st.error(f"파일을 읽는 중 오류가 발생했습니다: {e}")
        return None

def ask_gemini(model_name, prompt):
    """429 에러 방지를 위한 재시도 로직이 포함된 질의 함수"""
    model = genai.GenerativeModel(model_name)
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            if "429" in str(e) and attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1)) # 지수 백오프 (점점 더 오래 대기)
                continue
            return f"❌ 오류 발생: {str(e)}"

# --------------------------------------------------------------------------------
# 4. App Body
# --------------------------------------------------------------------------------
def main():
    # 헤더 섹션
    st.markdown('<p class="main-title">🏢 GIB 정관규정집 AI 상담사</p>', unsafe_allow_html=True)
    st.markdown(f"<p style='color:#888;'>최종 업데이트: {datetime.now().strftime('%Y-%m-%d')}</p>", unsafe_allow_html=True)

    # 1단계: API 체크
    if not setup_genai():
        st.error("API Key가 설정되지 않았습니다. Secrets를 확인해 주세요.")
        st.stop()

    # 2단계: 파일 로드 (서버 내 파일 우선)
    pdf_context = ""
    default_path = "regulations.pdf"
    
    with st.expander("🛠️ 시스템 설정 및 데이터 관리", expanded=False):
        uploaded_file = st.file_uploader("새 규정집 업로드 (선택사항)", type="pdf")
        selected_model = st.selectbox("엔진 선택", ["gemini-1.5-flash", "gemini-1.5-pro"])
        temp_val = st.slider("답변 정확도 조정", 0.0, 1.0, 0.0)

    # 데이터 로딩 로직
    if uploaded_file:
        pdf_context = load_and_process_pdf(uploaded_file)
    elif os.path.exists(default_path):
        with open(default_path, "rb") as f:
            pdf_context = load_and_process_pdf(f)
    
    if not pdf_context:
        st.info("💡 규정집 파일(regulations.pdf)을 업로드하거나 루트 폴더에 넣어주세요.")
        st.stop()

    # 3단계: 질문 섹션
    st.markdown("---")
    query = st.text_input("📝 규정집 내용 중 궁금하신 사항을 입력하세요", placeholder="예: 연가 일수 산정 방식은 어떻게 되나요?")

    if st.button("전문가에게 문의하기", use_container_width=True):
        if not query:
            st.warning("질문을 입력해 주세요.")
        else:
            with st.status("🔍 관련 규정을 검색하고 답변을 생성 중입니다...", expanded=True) as status:
                full_prompt = f"""
                당신은 GIB(기관명)의 규정 관리 전문 상담사입니다. 
                제공된 [규정 전문]만을 근거로 사용자의 질문에 답변하세요.

                [규정 전문]
                {pdf_context}

                [필수 지침]
                1. 답변 어조: 공공기관 상담원처럼 매우 정중하고 친절하게 답변하세요.
                2. 근거 제시: 답변의 각 단락 끝에 반드시 관련 규정 명칭과 [문서 페이지: n]을 명시하세요.
                3. 형식: 가독성을 위해 불렛 포인트나 번호 매기기를 활용하세요.
                4. 부재 정보: 만약 [규정 전문]에 내용이 없다면 반드시 "첨부된 자료에는 관련 정보가 없습니다."라고 답하세요.
                5. 유사 사례: 공무원 규정 등 유사 사례 인용 시 [출처: 공무원 인사규정 등]을 명확히 하세요.
                6. 마무리 문구: 반드시 "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"로 끝내세요.

                사용자 질문: {query}
                """
                
                answer = ask_gemini(selected_model, full_prompt)
                status.update(label="✅ 분석 완료", state="complete", expanded=False)

            # 결과 대시보드
            tab1, tab2 = st.tabs(["💬 규정 답변", "📄 참고 데이터"])
            with tab1:
                st.markdown(f"""
                <div style="background-color: #1e293b; padding: 20px; border-radius: 10px; border-left: 5px solid #3b82f6;">
                    {answer}
                </div>
                """, unsafe_allow_html=True)
            with tab2:
                st.caption("AI가 참조한 원문 데이터의 일부입니다.")
                st.text_area("Original Text Context", pdf_context[:5000], height=300)

if __name__ == "__main__":
    main()
