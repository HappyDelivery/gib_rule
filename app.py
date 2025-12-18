import streamlit as st
import google.generativeai as genai
import os
import time

# 1. 페이지 설정 및 디자인
st.set_page_config(page_title="GIB 정관규정집 AI 상담사", page_icon="🏢", layout="centered")

st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 8px; height: 3.5em; font-weight: bold; background-color: #FF4B4B; color: white; border: none; }
    div[data-baseweb="textarea"] { border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# 2. Gemini 파일 API를 이용한 업로드 및 캐싱 (속도 핵심)
@st.cache_resource
def upload_to_gemini(file_path):
    """파일을 구글 서버에 업로드하고 식별자를 반환 (딱 한 번만 실행됨)"""
    try:
        # 파일 업로드
        uploaded_file = genai.upload_file(path=file_path, display_name="GIB_Regulations")
        
        # 업로드된 파일이 처리될 때까지 대기 (보통 수 초 소요)
        while uploaded_file.state.name == "PROCESSING":
            time.sleep(1)
            uploaded_file = genai.get_file(uploaded_file.name)
            
        if uploaded_file.state.name == "FAILED":
            raise Exception("구글 서버 내 파일 처리 실패")
            
        return uploaded_file
    except Exception as e:
        st.error(f"파일 업로드 중 오류: {e}")
        return None

def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")

    # API 설정
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 API Key 설정이 필요합니다.")
        return
    genai.configure(api_key=api_key)

    # 3. 파일 존재 확인 및 구글 서버 업로드
    file_path = "regulations.pdf"
    if not os.path.exists(file_path):
        st.error(f"❌ '{file_path}' 파일을 찾을 수 없습니다.")
        return

    # 구글 서버에 업로드 (캐싱 처리되어 앱 실행 시 한 번만 수행됨)
    with st.spinner("🚀 시스템을 초기화 중입니다 (최초 1회)..."):
        gemini_file = upload_to_gemini(file_path)

    if not gemini_file:
        return

    # 4. 상담 화면 UI
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
            with st.spinner("규정집을 분석하여 답변을 생성 중입니다..."):
                try:
                    # 에러 해결 포인트: 모델명을 가장 안정적인 'gemini-1.5-flash'로 설정
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    prompt = f"""
                    당신은 GIB 기관의 정관 및 규정 전문 상담사입니다.
                    제공된 규정집 파일 내용을 바탕으로 사용자의 질문에 답변하세요.

                    [질문 분야]: {selected_cat}
                    [사용자 질문]: {query}

                    [필수 답변 규칙]
                    1. 정확하고 사실에 근거하여 친절하게 답변하세요.
                    2. 반드시 해당 내용의 근거가 되는 규정 명칭과 '페이지 번호'를 명시하세요.
                    3. 파일 내에 관련 정보가 없는 경우 "첨부된 자료에는 관련 정보가 없습니다."라고 명확히 답변하세요.
                    4. 복잡한 절차는 번호가 매겨진 리스트 형식으로 정리하세요.
                    5. 답변 마지막 문구는 반드시 아래 문장으로 끝내세요:
                       "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    """
                    
                    # 파일 URI를 참조하여 답변 생성 (파일 데이터를 직접 보내지 않아 매우 빠름)
                    response = model.generate_content([gemini_file, prompt])
                    
                    st.markdown("### 💡 답변 결과")
                    st.info(response.text)
                    
                except Exception as e:
                    # 모델 명칭 에러 대응을 위한 대체 시도
                    st.error(f"답변 생성 중 오류가 발생했습니다. (관리자 문의)")
                    st.caption(f"상세 에러: {str(e)}")

if __name__ == "__main__":
    main()
