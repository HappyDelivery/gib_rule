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
    .stAlert { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --------------------------------------------------------------------------------
# 2. 백엔드 로직 (Full Context & Robust Retry)
# --------------------------------------------------------------------------------

# 세션 상태 초기화
if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "full_text" not in st.session_state:
    st.session_state.full_text = ""

def load_data():
    """앱 초기화: 규정집 전체 로드"""
    # 1. API 설정
    try:
        api_key = st.secrets["GOOGLE_API_KEY"]
        genai.configure(api_key=api_key)
    except Exception as e:
        st.error(f"API 설정 오류: {e}")
        st.stop()

    # 2. PDF 전체 텍스트 추출
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"파일 없음: {file_path}")
        st.stop()
    
    try:
        with open(file_path, "rb") as f, st.spinner("규정집 정밀 분석 중... (최초 1회만 실행)"):
            pdf_reader = pypdf.PdfReader(f)
            text_data = []
            
            progress = st.progress(0, "페이지 로딩 중...")
            total = len(pdf_reader.pages)
            
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    # 페이지 번호 명확히 마킹
                    text_data.append(f"--- [Page {i+1}] ---\n{text}")
                progress.progress((i+1)/total)
            
            progress.empty()
            # 검색 없이 전체 텍스트를 통째로 저장
            st.session_state.full_text = "\n\n".join(text_data)
            
    except Exception as e:
        st.error(f"PDF 오류: {e}")
        st.stop()

    st.session_state.data_loaded = True

def generate_response_full_scan(query):
    """
    [핵심 기능] 전체 텍스트 스캔 + 강력한 재시도 로직
    - 일부만 검색하지 않고 전체를 보내 정확도 100% 확보
    - 429 오류 발생 시 점진적으로 대기하며 재시도
    """
    
    # 시스템 프롬프트: 규정집 전체를 보고 판단하라고 지시
    system_prompt = f"""
    당신은 '문서 분석 AI'입니다. 아래 제공된 [규정집 전문]을 바탕으로 사용자의 질문에 답하세요.

    [규정집 전문]
    {st.session_state.full_text}

    [작성 원칙]
    1. 질문과 관련된 내용이 규정집의 여러 곳에 흩어져 있을 수 있습니다. **전체 내용을 꼼꼼히 확인**하여 종합적인 답변을 작성하세요.
    2. '제X조' 같은 조항이 언급되면 해당 조항의 실제 내용도 찾아서 함께 설명하세요.
    3. 반드시 '페이지 번호(Page X)'를 근거로 제시하세요.
    4. 정보가 명확하지 않으면 추측하지 말고 "규정집에서 정확한 내용을 찾을 수 없습니다."라고 답하세요.
    5. 마지막 문구: "세부 내용은 정관규정집 원문을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
    """

    # 재시도 설정
    max_retries = 3
    
    # 사용할 모델: 긴 문맥 처리에 강하고 무료 할당량이 높은 flash 모델 고정
    model_name = "gemini-1.5-flash" 

    for attempt in range(max_retries):
        try:
            ai_model = genai.GenerativeModel(model_name)
            
            # 답변 생성 요청
            response = ai_model.generate_content(
                [system_prompt, f"사용자 질문: {query}"],
                generation_config={"temperature": 0.0}
            )
            return response.text
            
        except ResourceExhausted:
            # 한도 초과 시 대기 후 재시도
            wait_time = (attempt + 1) * 10  # 10초, 20초, 30초 대기
            time.sleep(wait_time)
            continue # 루프 다시 실행
            
        except Exception as e:
            return f"⚠️ 오류 발생: {str(e)}"
            
    # 3번 다 실패했을 경우
    return "⚠️ 현재 사용자가 많아 AI 연결이 지연되고 있습니다. 잠시 후(약 1분 뒤) 다시 질문해 주시기 바랍니다."

# --------------------------------------------------------------------------------
# 3. UI 렌더링
# --------------------------------------------------------------------------------
st.title("🏛️ GIB 정관규정집 AI 상담사")
st.caption(f"기준일: {datetime.now().strftime('%Y-%m-%d')}")
st.divider()

# 데이터 로드
if not st.session_state.data_loaded:
    load_data()
    st.rerun()

# 카테고리 예시
st.markdown("#### 💬 자주 묻는 질문")
example_questions = {
    "인사/복무": ["연차휴가 사용 규정", "병가 신청 절차", "육아휴직 자격"],
    "보수/경비": ["출장비 정산 방법", "시간외수당 지급 기준", "경조사비 지급 규정"],
    "기타": ["법인카드 사용 규정", "보안 및 정보 관리 규정", "차량 관리 규정"]
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
        
        # 스피너 메시지에 재시도 가능성을 언급
        with st.spinner("규정집 전체를 검토 중입니다... (내용이 많을 경우 시간이 조금 걸릴 수 있습니다)"):
            response_text = generate_response_full_scan(user_query)
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
    st.info("질문을 입력하면 AI가 규정집 전체를 정밀 분석하여 답변합니다.")
