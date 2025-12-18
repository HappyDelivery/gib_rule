import streamlit as st
import google.generativeai as genai
import pypdf
import os

# 1. 페이지 설정
st.set_page_config(page_title="GIB 정관규정집 AI 상담사", page_icon="🏢", layout="centered")

# 디자인 개선 (CSS)
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #FF4B4B; color: white; border: none; }
    div[data-baseweb="textarea"] { border-radius: 10px; }
    .answer-box { background-color: #1E1E1E; padding: 20px; border-radius: 10px; border-left: 5px solid #FF4B4B; }
    </style>
""", unsafe_allow_html=True)

# 2. PDF 텍스트 추출 및 캐싱 (속도 최적화의 핵심)
@st.cache_data(show_spinner=False)
def get_pdf_text(file_path):
    if not os.path.exists(file_path):
        return None
    try:
        with open(file_path, "rb") as f:
            pdf_reader = pypdf.PdfReader(f)
            extracted_pages = []
            for i, page in enumerate(pdf_reader.pages):
                text = page.extract_text()
                if text:
                    extracted_pages.append(f"[페이지 {i+1}]\n{text}")
            return "\n\n".join(extracted_pages)
    except:
        return None

def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")

    # API 설정
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 API Key를 찾을 수 없습니다. Streamlit Cloud의 Secrets 설정을 확인하세요.")
        return
    genai.configure(api_key=api_key)

    # 3. 데이터 로딩 (캐싱을 사용하여 접속 시 한 번만 실행)
    file_path = "regulations.pdf"
    if "full_text" not in st.session_state:
        with st.spinner("📄 규정집 데이터를 최적화 중입니다..."):
            text = get_pdf_text(file_path)
            if text:
                st.session_state.full_text = text
            else:
                st.error("❌ 'regulations.pdf' 파일을 읽을 수 없습니다. GitHub에 파일이 있는지 확인해 주세요.")
                return

    # 4. 상담 UI 구성
    st.markdown("### 상담 분야를 선택하세요")
    categories = {
        "인사 (승진, 채용, 평가)": "4급 승진을 위한 최저 소요 연수는 몇 년인가요?",
        "급여 (호봉, 수당, 퇴직금)": "가족 4명의 경우 수당 지급 기준을 알려주세요.",
        "복무 (휴가, 출장, 근무시간)": "연차 휴가 이월 규정에 대해 알려주세요.",
        "복지 (학자금, 의료비 지원)": "자녀 학자금 보조 수당 신청 절차는 어떻게 되나요?",
        "기타 (징계, 감사 등)": "징계 위원회 구성 요건이 어떻게 되나요?"
    }
    
    selected_cat = st.selectbox("분야", options=list(categories.keys()), label_visibility="collapsed")
    
    st.markdown("---")
    query = st.text_area("질문 내용을 입력하세요", 
                        placeholder=f"예시: {categories[selected_cat]}", 
                        height=120)

    if st.button("상담 시작하기 🚀"):
        if not query:
            st.warning("질문을 입력해 주세요.")
        else:
            with st.spinner("규정집을 분석하여 답변을 작성 중입니다..."):
                try:
                    # [에러 해결] 가장 안정적인 모델 호출 방식
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    당신은 GIB 기관의 정관 및 규정 전문 상담사입니다. 
                    아래 [규정집 내용]을 바탕으로만 답변하세요.

                    [규정집 내용]
                    {st.session_state.full_text}

                    [상담 분야]: {selected_cat}
                    [사용자 질문]: {query}

                    [작성 규칙]
                    1. 정확하고 사실에 근거하여 친절한 말투로 답변하세요.
                    2. 답변 내용에 해당하는 관련 규정 명칭과 해당 [페이지 번호]를 반드시 명시하세요.
                    3. 만약 규정집 내용에 질문과 관련된 정보가 없다면 반드시 "첨부된 자료에는 관련 정보가 없습니다."라고 답변하세요.
                    4. 복잡한 절차나 조건은 번호가 매겨진 리스트 형태로 정리하세요.
                    5. 답변 마지막 문구는 반드시 다음 내용을 포함하세요:
                       "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    """
                    
                    response = model.generate_content(prompt)
                    
                    st.markdown("### 💡 답변 결과")
                    st.markdown(f'<div class="answer-box">{response.text}</div>', unsafe_allow_html=True)
                    
                except Exception as e:
                    # 만약의 경우를 대비한 모델명 우회 로직
                    try:
                        model = genai.GenerativeModel('gemini-1.5-flash-latest')
                        response = model.generate_content(prompt)
                        st.markdown("### 💡 답변 결과")
                        st.markdown(f'<div class="answer-box">{response.text}</div>', unsafe_allow_html=True)
                    except:
                        st.error("⚠️ AI 서비스와 연결이 원활하지 않습니다. 잠시 후 다시 시도해 주세요.")
                        st.caption(f"Error Detail: {e}")

if __name__ == "__main__":
    main()
