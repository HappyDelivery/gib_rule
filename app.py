import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time
from datetime import datetime
from google.api_core.exceptions import ResourceExhausted

# --------------------------------------------------------------------------------
# 1. 환경 설정 및 스타일
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
    /* 답변 영역 스타일 */
    .st-emotion-cache-1v0mbdj { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. 백엔드 로직 (모델 다중화 & 스마트 검색)
# --------------------------------------------------------------------------------

# 세션 상태 초기화
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "pdf_pages" not in st.session_state:
    st.session_state.pdf_pages = [] # 페이지별 분할 저장

def get_relevant_context(query, pages, top_k=5):
    """
    [핵심 기능] PDF 전체를 다 보내지 않고, 질문과 관련된 페이지만 찾아서 보냄 (토큰 절약)
    - 단순 키워드 매칭 방식 사용 (속도 빠름, 토큰 절약 최적화)
    """
    query_keywords = query.split()
    scored_pages = []
    
    for i, page_text in enumerate(pages):
        score = 0
        for keyword in query_keywords:
            if keyword in page_text:
                score += 1
        if score > 0:
            scored_pages.append((score, page_text))
    
    # 관련도 순 정렬 후 상위 k개 페이지 추출
    scored_pages.sort(key=lambda x: x[0], reverse=True)
    selected_pages = [p[1] for p in scored_pages[:top_k]]
    
    # 만약 검색 결과가 없으면(키워드 불일치), 앞부분 3페이지만 보냄 (서론/목차 등)
    if not selected_pages:
        return "\n\n".join(pages[:3])
    
    return "\n\n".join(selected_pages)

def load_data_and_models():
    """앱 초기화: API 설정 및 PDF 로드"""
    # 1. API 설정 및 사용 가능한 모델 리스트 확보
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
        
        # 사용 가능한 모델을 모두 가져와서 Flash -> Pro 순서로 정렬 (Flash가 싸고 빠름)
        all_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        # 우선순위: Flash > Pro > 나머지
        sorted_models = sorted(all_models, key=lambda x: (0 if 'flash' in x else 1 if 'pro' in x else 2))
        st.session_state.available_models = sorted_models
        
    except Exception as e:
        st.error(f"API 설정 오류: {e}")
        st.stop()

    # 2. PDF 로드 (페이지별로 리스트에 저장)
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"파일 없음: {file_path}")
        st.stop()
    
    try:
        with open(file_path, "rb") as f, st.spinner("규정집 분석 중..."):
            pdf_reader = pypdf.PdfReader(f)
            st.session_state.pdf_pages = []
            
            # 진행바
            progress = st.progress(0, "페이지 분석 중...")
            total = len(pdf_reader.pages)
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    # 페이지 번호 마킹하여 저장
                    st.session_state.pdf_pages.append(f"--- [Page {i+1}] ---\n{text}")
                progress.progress((i+1)/total)
            
            progress.empty()
            
    except Exception as e:
        st.error(f"PDF 오류: {e}")
        st.stop()

    st.session_state.data_loaded = True

def generate_response_with_fallback(query):
    """
    [핵심 기능] 모델 자동 우회 (Fallback) 시스템
    - 1순위 모델이 실패하면 자동으로 2순위, 3순위 모델로 교체하여 재시도
    """
    
    # 1. 질문과 관련된 페이지 추출 (토큰 절약)
    relevant_context = get_relevant_context(query, st.session_state.pdf_pages)
    
    system_prompt = f"""
    당신은 '문서 분석 AI'입니다. 아래 제공된 [관련 규정 내용]을 기반으로 질문에 답하세요.

    [관련 규정 내용 (발췌)]
    {relevant_context}

    [작성 원칙]
    1. 반드시 제공된 내용에 근거해서만 답하세요. 외부 정보 사용 금지.
    2. 답변에는 '페이지 번호'를 꼭 명시하세요. (예: Page 12)
    3. 정보가 없으면 "제공된 규정 내용에서 관련 정보를 찾을 수 없습니다."라고 답하세요.
    4. 마지막 문구: "세부 내용은 정관규정집 원문을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
    """

    # 2. 모델 리스트를 순회하며 시도 (Fallback)
    models = st.session_state.get("available_models", [])
    if not models:
        return "사용 가능한 AI 모델을 찾을 수 없습니다."

    last_error = ""
    
    for model_name in models:
        try:
            # 모델 변경 시도 알림 (로그 성격, 화면엔 표시 X)
            # print(f"Trying model: {model_name}") 
            
            ai_model = genai.GenerativeModel(model_name)
            response = ai_model.generate_content(
                [system_prompt, f"사용자 질문: {query}"],
                generation_config={"temperature": 0.0}
            )
            return response.text # 성공 시 바로 반환
            
        except ResourceExhausted:
            # 한도 초과 시 다음 모델로 넘어감
            continue 
        except Exception as e:
            last_error = str(e)
            continue
            
    # 모든 모델이 실패했을 경우
    return f"⚠️ 죄송합니다. 모든 AI 모델이 현재 사용량이 많아 응답할 수 없습니다.\n(마지막 오류: {last_error})\n잠시 후 다시 시도해주세요."

# --------------------------------------------------------------------------------
# 3. UI 렌더링
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
st.divider()

# 데이터 로드
if not st.session_state.data_loaded:
    load_data_and_models()
    st.rerun()

# 카테고리 예시
st.markdown("#### 💬 자주 묻는 질문")
example_questions = {
    "인사/복무": ["연차휴가 사용 규정", "병가 신청 절차", "육아휴직 자격"],
    "보수/경비": ["출장비 정산 방법", "시간외수당 기준", "경조사비 지급"],
    "기타": ["법인카드 사용 규정", "보안 규정", "차량 관리"]
}
selected_category = st.selectbox("분야 선택", list(example_questions.keys()))

cols = st.columns(len(example_questions[selected_category]))
for i, q in enumerate(example_questions[selected_category]):
    if cols[i].button(q, use_container_width=True):
        st.session_state.user_query = q
        st.rerun()

# 직접 질문
st.markdown("---")
st.markdown("#### ✍️ 직접 질문하기")
user_query = st.text_area("질문을 입력하세요.", key="user_query", height=100)

if st.button("답변 받기 🚀", type="primary", use_container_width=True):
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        
        with st.spinner("AI 모델을 최적화하여 답변을 생성 중입니다..."):
            # 개선된 Fallback 함수 호출
            response_text = generate_response_with_fallback(user_query)
            st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        st.rerun()
    else:
        st.warning("질문을 입력해주세요.")

# 결과 표시
st.markdown("---")
if st.session_state.chat_history:
    for message in reversed(st.session_state.chat_history):
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
else:
    st.info("질문을 입력하면 AI가 규정집을 분석하여 답변합니다.")
