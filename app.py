import streamlit as st
import google.generativeai as genai
import pypdf
import os
import time

# 1. 페이지 설정
st.set_page_config(page_title="GIB 정관규정집 AI 상담사", page_icon="🏢", layout="centered")

# 디자인 개선
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #FF4B4B; color: white; border: none; }
    .answer-box { background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #FF4B4B; line-height: 1.7; }
    </style>
""", unsafe_allow_html=True)

# 2. 사용 가능한 최적의 모델 자동 찾기
def get_working_model():
    try:
        # 사용 가능한 모델 리스트 조회
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                # flash 1.5 모델을 최우선으로 찾음
                if 'gemini-1.5-flash' in m.name:
                    return m.name
        # flash가 없으면 아무나 응답 가능한 첫 번째 모델 반환
        return 'gemini-1.5-flash' 
    except:
        return 'models/gemini-1.5-flash' # 기본값

@st.cache_data(show_spinner=False)
def extract_pdf_text(file_path):
    """메모리 효율적인 텍스트 추출"""
    if not os.path.exists(file_path): return None
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            text_list = [f"[Page {i+1}]\n{p.extract_text()}" for i, p in enumerate(pdf_reader.pages) if p.extract_text()]
            return "\n\n".join(text_list)
    except: return None

def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")

    # API 설정
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 API Key를 찾을 수 없습니다. Secrets 설정을 확인하세요.")
        return
    genai.configure(api_key=api_key)

    # 3. 규정집 로드 (세션 저장으로 속도 향상)
    file_path = "regulations.pdf"
    if "reg_text" not in st.session_state:
        with st.status("📄 규정집 분석 중...", expanded=True) as status:
            text = extract_pdf_text(file_path)
            if text:
                st.session_state.reg_text = text
                status.update(label="✅ 분석 완료", state="complete", expanded=False)
            else:
                st.error("❌ 파일을 읽을 수 없습니다. GitHub에 'regulations.pdf'가 있는지 확인하세요.")
                return

    # 4. 상담 UI
    st.markdown("### 상담 분야를 선택하세요")
    categories = {
        "인사 (승진, 채용, 평가)": "4급 승진을 위한 최저 소요 연수는 몇 년인가요?",
        "급여 (호봉, 수당, 퇴직금)": "가족 4명의 경우 수당 지급 기준을 알려주세요.",
        "복무 (휴가, 출장, 근무시간)": "연차 휴가 이월 규정에 대해 알려주세요.",
        "복지 (학자금, 의료비 지원)": "자녀 학자금 보조 수당 신청 절차는 어떻게 되나요?",
        "기타 (징계, 감사 등)": "징계 위원회 구성 요건이 어떻게 되나요?"
    }
    
    selected_cat = st.selectbox("분야", options=list(categories.keys()), label_visibility="collapsed")
    query = st.text_area("질문 내용", placeholder=f"예시: {categories[selected_cat]}", height=120)

    if st.button("상담 시작하기 🚀"):
        if not query:
            st.warning("질문을 입력해 주세요.")
        else:
            with st.spinner("AI가 규정집을 검토하고 있습니다..."):
                try:
                    # 작동 가능한 모델명을 동적으로 가져옴 (404 방지 핵심)
                    target_model = get_working_model()
                    model = genai.GenerativeModel(target_model)
                    
                    prompt = f"""
                    당신은 GIB 기관의 규정 전문 상담사입니다. 
                    아래 [규정집] 내용을 기반으로만 답변하세요.

                    [규정집]
                    {st.session_state.reg_text}

                    [질문 분야]: {selected_cat}
                    [사용자 질문]: {query}

                    [답변 가이드]
                    1. 친절하게 답변하되 반드시 관련 '규정 명칭'과 '페이지 번호'를 적으세요.
                    2. 규정에 없는 내용은 "첨부된 자료에는 관련 정보가 없습니다."라고 답하세요.
                    3. 답변 마지막 문구: "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    """
                    
                    response = model.generate_content(prompt)
                    
                    st.markdown("### 💡 답변 결과")
                    st.markdown(f'<div class="answer-box">{response.text}</div>', unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"⚠️ 시스템 응답 지연이 발생했습니다. (오류: {str(e)[:50]}...)")
                    st.info("Tip: 잠시 후 다시 버튼을 눌러보시거나 앱을 새로고침 해주세요.")

if __name__ == "__main__":
    main()
