import streamlit as st
import google.generativeai as genai
import os
import time

# 1. 페이지 설정
st.set_page_config(page_title="GIB 정관규정집 AI 상담사", page_icon="🏢", layout="centered")

# 디자인 최적화 (모바일 우선)
st.markdown("""
    <style>
    .stApp { font-family: 'Pretendard', sans-serif; }
    .stButton > button { width: 100%; border-radius: 12px; height: 3.5em; font-weight: bold; background-color: #FF4B4B; color: white; border: none; }
    .status-box { padding: 15px; border-radius: 10px; background-color: #262730; border: 1px solid #464646; margin-bottom: 20px; }
    </style>
""", unsafe_allow_html=True)

def main():
    st.title("🏢 GIB 정관규정집 AI 상담사")

    # API 설정
    api_key = st.secrets.get("GOOGLE_API_KEY")
    if not api_key:
        st.error("🔑 API Key를 찾을 수 없습니다. Secrets 설정을 확인하세요.")
        return
    genai.configure(api_key=api_key)

    file_path = "regulations.pdf"
    
    # 2. Gemini File API를 활용한 파일 분석 (메모리 절약형)
    if "gemini_file_uri" not in st.session_state:
        if not os.path.exists(file_path):
            st.error(f"❌ '{file_path}' 파일이 GitHub에 없습니다.")
            return

        with st.status("🚀 규정집을 AI 서버에 연결하는 중...", expanded=True) as status:
            try:
                # 파일을 구글 서버로 직접 업로드 (로컬 메모리 사용 최소화)
                st.write("1. 파일 전송 중...")
                uploaded_file = genai.upload_file(path=file_path)
                
                st.write("2. AI가 문서를 분석 중입니다 (수 초 소요)...")
                # 파일 처리 대기
                while uploaded_file.state.name == "PROCESSING":
                    time.sleep(2)
                    uploaded_file = genai.get_file(uploaded_file.name)
                
                if uploaded_file.state.name == "FAILED":
                    st.error("AI 서버 내 파일 분석에 실패했습니다.")
                    return
                
                # 업로드된 파일 정보 저장
                st.session_state.gemini_file_uri = uploaded_file.uri
                st.session_state.gemini_file_name = uploaded_file.name
                status.update(label="✅ 분석 준비 완료!", state="complete", expanded=False)
                
            except Exception as e:
                st.error(f"❌ 분석 중 오류 발생: {e}")
                st.info("Tip: 파일명이 정확한지, API 키가 유효한지 확인하세요.")
                return

    # 3. 상담 UI (본 화면)
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
            with st.spinner("AI 상담사가 답변을 작성하고 있습니다..."):
                try:
                    # 404 에러 방지용: 모델 식별자 최적화
                    model = genai.GenerativeModel('gemini-1.5-flash')
                    
                    # 파일 참조 정보 가져오기
                    doc_ref = genai.get_file(st.session_state.gemini_file_name)
                    
                    prompt = f"""
                    당신은 GIB 기관의 정관 및 규정 전문 상담사입니다. 
                    첨부된 규정집 파일을 정독하고, 오직 그 내용에만 근거하여 답변하세요.

                    [상담 분야]: {selected_cat}
                    [사용자 질문]: {query}

                    [작성 규칙]
                    1. 사실에 기반하여 친절하게 답변하세요.
                    2. 관련 규정의 명칭과 해당 '페이지 번호'를 반드시 명시하세요.
                    3. 내용이 없는 경우 "첨부된 자료에는 관련 정보가 없습니다."라고 답변하세요.
                    4. 마지막 끝인사: "세부내용은 정관규정집을 다시 한번 확인하시기 바랍니다. 더 궁금하신 사항은 없으신가요?"
                    """
                    
                    # 파일과 프롬프트를 함께 전송 (매우 빠름)
                    response = model.generate_content([doc_ref, prompt])
                    
                    st.markdown("### 💡 답변 결과")
                    st.info(response.text)
                    
                except Exception as e:
                    # 404 모델명 에러에 대한 최후의 방어 코드
                    if "404" in str(e):
                        st.error("AI 모델 연결에 문제가 있습니다. 잠시 후 다시 시도해 주세요.")
                    else:
                        st.error(f"답변 생성 중 오류가 발생했습니다: {e}")

if __name__ == "__main__":
    main()
