import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io
import re

# --- 1. 페이지 설정 ---
st.set_page_config(
    page_title="도겸이의 학습 도우미",
    page_icon="🐣",
    layout="centered"
)

# --- 2. 네이버 사전 스타일 CSS ---
st.markdown("""
<style>
    .stApp { background-color: #121212; color: #fff; }
    
    /* 제목 */
    h1 { color: #FFD700 !important; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    
    /* 버튼 */
    .stButton > button {
        width: 100%; border-radius: 12px; font-weight: bold;
        background: #03C75A; /* 네이버 그린 컬러 */
        color: white; height: 3.5em; font-size: 1.2rem !important; border: none;
    }
    
    /* 설명 텍스트 (채팅) */
    .chat-text {
        font-size: 1.3rem; line-height: 1.8; color: #E0E0E0;
        margin-bottom: 20px;
    }
    
    /* [핵심] 사전 카드 스타일 */
    .dic-card {
        background-color: #242424;
        border: 1px solid #444;
        border-radius: 15px;
        padding: 25px;
        margin-top: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.5);
    }
    .dic-english {
        font-size: 2.2rem;
        font-weight: bold;
        color: #66dbff; /* 밝은 하늘색 강조 */
        margin-bottom: 10px;
    }
    .dic-pronoun {
        font-size: 1.1rem;
        color: #aaa;
        margin-bottom: 15px;
    }
    .dic-meaning {
        font-size: 1.4rem;
        font-weight: bold;
        color: #fff;
        border-top: 1px solid #555;
        padding-top: 15px;
        margin-top: 10px;
    }
    
    /* 오디오 플레이어 숨김 처리 후 커스텀 버튼화는 복잡하므로 기본 플레이어 스타일 개선 */
    .stAudio { margin-top: 10px; margin-bottom: 10px; width: 100%; }
</style>
""", unsafe_allow_html=True)

# --- 3. 모델 연결 함수 (안전 모드) ---
def get_model():
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("API 키가 없습니다.")
        st.stop()
    genai.configure(api_key=api_key)
    
    # 모델 자동 탐색
    candidates = ["gemini-1.5-flash", "models/gemini-1.5-flash", "gemini-pro"]
    for name in candidates:
        try:
            model = genai.GenerativeModel(name)
            model.generate_content("Hi", generation_config={'max_output_tokens': 1})
            return name
        except: continue
    return "gemini-1.5-flash" # Fallback

# --- 4. 영어 음성 생성 ---
def generate_audio(text):
    if not text: return None
    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        return fp
    except: return None

# --- 5. UI 메인 ---
st.title("🐣 도겸이의 학습 도우미 ✏️")

with st.container():
    col1, col2 = st.columns([3, 1])
    with col1:
        user_question = st.text_input("궁금한 영어 단어나 문장을 적어봐!", placeholder="예: have a nice day")
    with col2:
        uploaded_file = st.file_uploader("📷", type=["jpg", "png"], label_visibility="collapsed")

    # 도겸이 맞춤형 프롬프트 (구조화된 출력 요구)
    system_instruction = f"""
    당신은 초등학교 2학년 '도겸'이의 영어 선생님입니다.
    
    [답변 작성 순서]
    1. 먼저 질문에 대해 도겸이가 이해하기 쉽게 한국어로 친절하게 설명해주세요. (이때 영어 단어에 태그를 붙이지 마세요.)
    2. 설명이 다 끝나면, 가장 핵심이 되는 영어 문장(또는 단어)을 아래 포맷으로 딱 하나만 만들어주세요.
    
    [필수 출력 포맷 - 이것을 꼭 지키세요]
    ///DIC_START///
    영어문장
    한국어발음
    한국어뜻
    ///DIC_END///
    
    예시:
    ///DIC_START///
    Have a nice day!
    해브 어 나이스 데이
    좋은 하루 보내!
    ///DIC_END///
    """

if st.button("도겸이 궁금증 해결! 🔍", use_container_width=True):
    if user_question or uploaded_file:
        try:
            with st.spinner("사전을 찾아보고 있어요... 📖"):
                model_name = get_model()
                model = genai.GenerativeModel(model_name=model_name, system_instruction=system_instruction)
                
                inputs = []
                if user_question: inputs.append(user_question)
                if uploaded_file: inputs.append(Image.open(uploaded_file))
                
                response = model.generate_content(inputs)
                full_text = response.text
                
                # --- 결과 파싱 (설명 vs 사전 카드) ---
                # 1. 사전 카드 부분 추출
                pattern = r"///DIC_START///(.*?)///DIC_END///"
                match = re.search(pattern, full_text, re.DOTALL)
                
                explanation = full_text # 기본값: 전체 텍스트
                card_data = None
                
                if match:
                    # 사전 데이터가 있으면 분리
                    card_content = match.group(1).strip().split('\n')
                    # 설명 부분에서 사전 태그 제거
                    explanation = full_text.replace(match.group(0), "").strip()
                    
                    # 데이터 정리 (3줄 예상: 영어/발음/뜻)
                    card_data = [line.strip() for line in card_content if line.strip()]

            # --- 화면 출력 ---
            
            # 1. 짝꿍의 설명 (채팅 스타일)
            if explanation:
                st.markdown(f'<div class="chat-text">{explanation}</div>', unsafe_allow_html=True)
            
            # 2. 네이버 사전 스타일 카드 (데이터가 있을 때만)
            if card_data and len(card_data) >= 3:
                eng_text = card_data[0]
                pronoun = card_data[1]
                meaning = card_data[2]
                
                # 카드 UI 렌더링
                st.markdown(f"""
                <div class="dic-card">
                    <div class="dic-english">{eng_text}</div>
                    <div class="dic-pronoun">[{pronoun}]</div>
                """, unsafe_allow_html=True)
                
                # 오디오 플레이어 (영어 텍스트로 생성)
                audio_fp = generate_audio(eng_text)
                if audio_fp:
                    st.audio(audio_fp, format='audio/mp3')
                
                st.markdown(f"""
                    <div class="dic-meaning">{meaning}</div>
                </div>
                """, unsafe_allow_html=True)
            
            # 혹시 형식이 안 맞으면 그냥 텍스트로 보여주기 (에러 방지)
            elif match: 
                 st.info("카드를 만들 정보를 찾지 못했어요.")
                 st.code(match.group(1))

        except Exception as e:
            st.error("앗! 잠깐 오류가 났어요. 다시 눌러주세요! 💦")
            st.caption(f"Error: {e}")
    else:
        st.warning("질문을 입력해주세요!")

st.markdown("---")
st.markdown("<div style='text-align: center; color: #555;'>도겸이를 위한 AI 영어 사전 📖</div>", unsafe_allow_html=True)
