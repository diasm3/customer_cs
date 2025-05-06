import streamlit as st
import asyncio
import sys
import os
import uuid
from datetime import datetime

# 상위 디렉토리를 import path에 추가
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 기업 페르소나 모듈 임포트
from data.personas.company_personas import (
    list_available_personas, 
    get_persona_by_id, 
    get_scenarios_by_company, 
    get_scenario
)

# LangGraph 클라이언트 임포트
from utils.langraph_client import (
    create_langgraph_client,
    create_thread,
    add_message_to_thread,
    find_or_create_assistant,
    send_message_and_wait_response,
    get_assistants,
    generate_company_response_async
)

# CSS 파일 로드 함수
def load_css(css_file):
    with open(css_file, "r") as f:
        css = f.read()
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)

# 추가 CSS 스타일 - 숨김 버튼용
st.markdown("""
<style>
    .hidden-button {
        display: none;
    }
    button[data-testid="baseButton-secondary"] {
        display: block;
    }
    .hidden-button button[data-testid="baseButton-secondary"] {
        display: none;
    }
</style>
""", unsafe_allow_html=True)

# CSS 로드
css_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "css", "chat_style.css")
load_css(css_path)

# 페이지 제목
st.write("<div class='main-title'>CS 대화 시뮬레이션</div>", unsafe_allow_html=True)

# 세션 상태 초기화
if 'step' not in st.session_state:
    st.session_state.step = "login"
if 'nickname' not in st.session_state:
    st.session_state.nickname = None
if 'user_id' not in st.session_state:
    st.session_state.user_id = None
if 'company' not in st.session_state:
    st.session_state.company = None
if 'scenario' not in st.session_state:
    st.session_state.scenario = None
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'thread_id' not in st.session_state:
    st.session_state.thread_id = None
if 'assistant_id' not in st.session_state:
    st.session_state.assistant_id = None
if 'evaluation_result' not in st.session_state:
    st.session_state.evaluation_result = None

# 기업 선택 함수 정의
def select_company(company):
    st.session_state.company = company
    st.session_state.step = "scenario_select"
    st.rerun()

# 시나리오 선택 함수 정의
def select_scenario(scenario):
    st.session_state.scenario = scenario
    st.session_state.chat_messages = []  # 채팅 메시지 초기화
    st.session_state.thread_id = None    # 스레드 ID 초기화
    st.session_state.assistant_id = None # 어시스턴트 ID 초기화
    st.session_state.step = "chat"
    st.rerun()

# 단계에 따라 다른 화면 표시
if st.session_state.step == "login":
    # 로그인 화면
    st.write("<div class='subtitle'>로그인</div>", unsafe_allow_html=True)

    # 로그인 폼
    with st.form("login_form"):
        nickname = st.text_input("닉네임", placeholder="사용할 닉네임을 입력하세요")
        submit = st.form_submit_button("시작하기")
        
        if submit and nickname:
            st.session_state.nickname = nickname
            st.session_state.user_id = str(uuid.uuid4())
            st.success(f"{nickname}님, 환영합니다!")
            
            # 다음 단계로 이동
            st.session_state.step = "company_select"
            st.rerun()
        elif submit and not nickname:
            st.error("닉네임을 입력해주세요.")

    # 로그인 안내
    st.markdown("""
    ---
    ### 시뮬레이션 안내
    이 애플리케이션은 고객 서비스 상담 시뮬레이션입니다.
    다양한 기업의 페르소나를 선택하고, 가상 상담 시나리오에서 대화를 연습해볼 수 있습니다.

    1. 닉네임을 입력하고 시작하기를 클릭하세요.
    2. 상담을 원하는 기업을 선택하세요.
    3. 시나리오를 선택하고 대화를 시작하세요.
    4. 대화 내용은 분석되어 평가 결과를 제공합니다.
    """)

elif st.session_state.step == "company_select":
    # 기업 선택 화면
    st.write("<div class='subtitle'>기업 선택</div>", unsafe_allow_html=True)
    st.write("<div class='paragraph'>상담을 원하는 기업을 선택해주세요.</div>", unsafe_allow_html=True)

    # 사용 가능한 기업 페르소나 목록 가져오기
    companies = list_available_personas()

    # 기업 카드 표시
    cols = st.columns(3)
    for i, company in enumerate(companies):
        with cols[i % 3]:
            # 카드를 클릭할 수 있는 컨테이너로 변경
            card_html = f"""
            <div class='company-card clickable-card' onclick="document.getElementById('button_{company['id']}').click();">
                <div class='company-name'>{company['name']}</div>
                <div class='company-desc'>{company['description']}</div>
                <div class='company-info'>산업: {company['industry']}</div>
            </div>
            """
            st.write(card_html, unsafe_allow_html=True)
            
            # 숨겨진 버튼 (직접 클릭됨)
            with st.container():
                st.markdown(f"<div class='hidden-button'>", unsafe_allow_html=True)
                st.button("선택", key=f"button_{company['id']}", on_click=select_company, args=(company,), help="기업 선택")
                st.markdown("</div>", unsafe_allow_html=True)

    # 뒤로 가기 버튼
    if st.button("◀ 뒤로 가기", key="back_to_login"):
        st.session_state.nickname = None
        st.session_state.user_id = None
        st.session_state.step = "login"
        st.rerun()

elif st.session_state.step == "scenario_select":
    # 시나리오 선택 화면
    company = st.session_state.company
    st.write(f"<div class='subtitle'>{company['name']} - 시나리오 선택</div>", unsafe_allow_html=True)
    st.write("<div class='paragraph'>상담 시나리오를 선택해주세요.</div>", unsafe_allow_html=True)

    # 사용 가능한 시나리오 목록 가져오기
    scenarios = get_scenarios_by_company(company['id'])

    # 시나리오 카드 표시
    for i, scenario in enumerate(scenarios):
        with st.container():
            # 클릭 가능한 시나리오 카드
            card_html = f"""
            <div class='scenario-box clickable-card' onclick="document.getElementById('scenario_button_{scenario['id']}').click();">
                <h3>{scenario['title']}</h3>
                <p>{scenario['description']}</p>
                <p><strong>난이도:</strong> {'⭐' * scenario.get('difficulty', 1)}</p>
                <p><strong>목표:</strong> {scenario.get('objective', '시나리오 목표 없음')}</p>
            </div>
            """
            st.write(card_html, unsafe_allow_html=True)
            
            # 숨겨진 버튼 (직접 클릭됨)
            with st.container():
                st.markdown(f"<div class='hidden-button'>", unsafe_allow_html=True)
                st.button("선택", key=f"scenario_button_{scenario['id']}", on_click=select_scenario, args=(scenario,), help="시나리오 선택")
                st.markdown("</div>", unsafe_allow_html=True)

    # 뒤로 가기 버튼
    if st.button("◀ 뒤로 가기", key="back_to_company"):
        st.session_state.company = None
        st.session_state.step = "company_select"
        st.rerun()

elif st.session_state.step == "chat":
    # 채팅 화면
    company = st.session_state.company
    scenario = st.session_state.scenario
    user_id = st.session_state.user_id

    # 채팅 페이지 제목
    st.write(f"<div class='subtitle'>{company['name']} - {scenario['title']}</div>", unsafe_allow_html=True)

    # 시나리오 설명
    with st.expander("시나리오 설명", expanded=True):
        st.write(f"""
        **시나리오**: {scenario['description']}
        
        **고객 목표**: {scenario.get('customer_objective', '지정된 목표 없음')}
        
        **기업 목표**: {scenario.get('company_objective', '지정된 목표 없음')}
        """)

    # LangGraph 스레드 초기화
    if 'thread_id' not in st.session_state or not st.session_state.thread_id:
        # 비동기 함수를 실행하기 위한 설정
        async def init_thread():
            client = await create_langgraph_client()
            try:
                # 스레드 생성
                thread_id = await create_thread(client)
                st.session_state.thread_id = thread_id
                
                # 설정 정보
                config = {
                    "user_id": user_id,
                    "todo_category": f"{company['id']}_{scenario['id']}",
                    "company_id": company['id'],
                    "scenario_id": scenario['id']
                }
                
                # 항상 새로운 어시스턴트 생성
                try:
                    assistant_id = await find_or_create_assistant(
                        client,
                        "persona_graph",
                        {"configurable": config}
                    )
                    
                    st.session_state.assistant_id = assistant_id
                    
                except Exception as e:
                    st.error(f"어시스턴트 생성 중 오류가 발생했습니다: {str(e)}")
                
                # 초기 메시지 설정 - 환영 메시지 추가
                welcome_message = {
                    "role": "assistant",
                    "content": f"안녕하세요, {st.session_state.nickname}님. {company['name']}입니다. 무엇을 도와드릴까요?"
                }
                
                # 메시지 목록에 추가
                if 'chat_messages' not in st.session_state:
                    st.session_state.chat_messages = []
                st.session_state.chat_messages.append(welcome_message)
                
            except Exception as e:
                st.error(f"스레드 초기화 중 오류가 발생했습니다: {str(e)}")
            finally:
                # 연결 종료 - 필요시 추가
                pass
        
        # 비동기 함수 실행
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            with st.spinner('초기화 중...'):
                loop.run_until_complete(init_thread())
        except Exception as e:
            st.error(f"비동기 실행 오류: {str(e)}")
        finally:
            loop.close()

    # 메시지 표시 컨테이너
    chat_container = st.container()
    chat_container.write("<div class='chat-container' id='chat-container'>", unsafe_allow_html=True)

    # 메시지 표시
    for msg in st.session_state.chat_messages:
        role_class = "user-message" if msg["role"] == "user" else "bot-message"
        chat_container.write(f"<div class='{role_class}'>{msg['content']}</div>", unsafe_allow_html=True)

    chat_container.write("</div>", unsafe_allow_html=True)

    # 대화 종료 버튼
    col1, col2 = st.columns([4, 1])
    with col2:
        if st.button("대화 평가하기"):
            st.session_state.step = "evaluation"
            st.rerun()

    # 입력 폼
    with st.form(key="chat_form", clear_on_submit=True):
        user_input = st.text_input("메시지 입력:", key="user_message")
        send_button = st.form_submit_button("전송")
        
        if send_button and user_input:
            # 사용자 메시지 추가
            user_message = {"role": "user", "content": user_input}
            st.session_state.chat_messages.append(user_message)
            
            # 비동기 함수로 LangGraph API 호출
            async def send_message():
                client = await create_langgraph_client()
                try:
                    # 응답 생성 - generate_company_response_async 함수 사용
                    response_content = await generate_company_response_async(
                        client,
                        st.session_state.thread_id,
                        user_input,
                        company['id'],
                        scenario['id'],
                        user_id
                    )
                    
                    # AI 응답 메시지 추가
                    if response_content:
                        assistant_message = {
                            "role": "assistant", 
                            "content": response_content
                        }
                        st.session_state.chat_messages.append(assistant_message)
                    else:
                        # 응답이 없는 경우
                        st.session_state.chat_messages.append({
                            "role": "assistant",
                            "content": "죄송합니다. 응답을 처리하는 중 오류가 발생했습니다."
                        })
                except Exception as e:
                    # 오류 메시지 표시
                    st.session_state.chat_messages.append({
                        "role": "assistant",
                        "content": f"죄송합니다. 응답 처리 중 오류가 발생했습니다: {str(e)}"
                    })
                    print(f"응답 생성 오류: {str(e)}")
            
            # 메시지 전송 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                with st.spinner('응답 생성 중...'):
                    loop.run_until_complete(send_message())
            except Exception as e:
                st.error(f"비동기 실행 오류: {str(e)}")
            finally:
                loop.close()
            
            # 페이지 새로고침
            st.rerun()

    # 뒤로 가기 버튼
    if st.button("◀ 다른 시나리오 선택", key="back_to_scenario"):
        st.session_state.scenario = None
        st.session_state.thread_id = None
        st.session_state.chat_messages = []
        st.session_state.assistant_id = None
        st.session_state.step = "scenario_select"
        st.rerun()

elif st.session_state.step == "evaluation":
    # 평가 화면
    company = st.session_state.company
    scenario = st.session_state.scenario
    user_id = st.session_state.user_id
    
    # 페이지 제목
    st.write(f"<div class='subtitle'>대화 평가 결과</div>", unsafe_allow_html=True)
    
    # 평가 결과가 없는 경우 생성
    if not st.session_state.evaluation_result:
        with st.spinner("대화 평가 중..."):
            # 비동기 함수로 평가 결과 생성
            async def generate_evaluation():
                client = await create_langgraph_client()
                try:
                    # 평가 어시스턴트 생성
                    evaluation_config = {
                        "user_id": user_id,
                        "company_id": company['id'],
                        "scenario_id": scenario['id'],
                        "conversation": st.session_state.chat_messages
                    }
                    
                    # 평가 어시스턴트 찾기 또는 생성
                    eval_assistant_id = await find_or_create_assistant(
                        client,
                        "evaluation_graph",
                        {"configurable": evaluation_config}
                    )
                    
                    # 새 스레드 생성
                    eval_thread_id = await create_thread(client)
                    
                    # 메시지 추가
                    await add_message_to_thread(
                        client,
                        eval_thread_id,
                        "user",
                        "대화를 평가해 주세요."
                    )
                    
                    # 응답 대기
                    response = await send_message_and_wait_response(
                        client,
                        eval_thread_id,
                        eval_assistant_id
                    )
                    
                    # 결과 처리
                    result = response.get("content", "평가 결과를 받아오지 못했습니다.")
                    
                    # 세션 상태에 결과 저장
                    st.session_state.evaluation_result = {
                        "text": result,
                        "scores": {
                            "친절도": 4.5,
                            "전문성": 4.2,
                            "해결력": 3.8,
                            "효율성": 4.0,
                            "전반적 만족도": 4.2
                        },
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    
                except Exception as e:
                    st.error(f"평가 생성 중 오류가 발생했습니다: {str(e)}")
                    st.session_state.evaluation_result = {
                        "text": f"평가 생성 중 오류가 발생했습니다: {str(e)}",
                        "scores": {},
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
            
            # 비동기 함수 실행
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(generate_evaluation())
            except Exception as e:
                st.error(f"비동기 실행 오류: {str(e)}")
            finally:
                loop.close()
    
    # 평가 결과 표시
    if st.session_state.evaluation_result:
        # 결과 컨테이너
        with st.container():
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # 평가 내용
                st.write("<div class='scenario-box'>", unsafe_allow_html=True)
                st.write("<h3>평가 세부 내용</h3>", unsafe_allow_html=True)
                st.write(st.session_state.evaluation_result["text"])
                st.write("<p class='company-info'>평가 시간: " + st.session_state.evaluation_result["timestamp"] + "</p>", unsafe_allow_html=True)
                st.write("</div>", unsafe_allow_html=True)
                
                # 대화 내용
                with st.expander("전체 대화 내용", expanded=False):
                    st.write("<div class='chat-container'>", unsafe_allow_html=True)
                    for msg in st.session_state.chat_messages:
                        role_class = "user-message" if msg["role"] == "user" else "bot-message"
                        st.write(f"<div class='{role_class}'>{msg['content']}</div>", unsafe_allow_html=True)
                    st.write("</div>", unsafe_allow_html=True)
            
            with col2:
                # 점수 표시
                st.write("<div class='company-card'>", unsafe_allow_html=True)
                st.write("<h3>평가 점수</h3>", unsafe_allow_html=True)
                
                for category, score in st.session_state.evaluation_result["scores"].items():
                    # 점수에 따른 색상 결정
                    if score >= 4.5:
                        score_color = "#4CAF50"  # 초록색 (매우 좋음)
                    elif score >= 4.0:
                        score_color = "#2196F3"  # 파란색 (좋음)
                    elif score >= 3.0:
                        score_color = "#FF9800"  # 주황색 (보통)
                    else:
                        score_color = "#F44336"  # 빨간색 (좋지 않음)
                    
                    # 별점 표시
                    stars = "⭐" * int(score)
                    if score - int(score) >= 0.5:
                        stars += "★"
                    
                    st.write(f"""
                    <div style="margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span>{category}</span>
                            <span style="color: {score_color}; font-weight: bold;">{score:.1f}</span>
                        </div>
                        <div style="margin-top: 5px;">{stars}</div>
                        <div style="height: 6px; background-color: #eee; border-radius: 3px; margin-top: 5px;">
                            <div style="height: 100%; width: {score*20}%; background-color: {score_color}; border-radius: 3px;"></div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                
                st.write("</div>", unsafe_allow_html=True)
    
    # 공유 버튼
    st.write("<div style='text-align: center; margin: 20px 0;'>", unsafe_allow_html=True)
    st.download_button(
        label="평가 결과 다운로드",
        data=str(st.session_state.evaluation_result),
        file_name=f"chat_evaluation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
        mime="text/plain"
    )
    st.write("</div>", unsafe_allow_html=True)
    
    # 새 시뮬레이션 시작 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("새 시뮬레이션 시작하기", key="new_simulation"):
            # 세션 상태 일부 초기화
            st.session_state.scenario = None
            st.session_state.thread_id = None
            st.session_state.chat_messages = []
            st.session_state.assistant_id = None
            st.session_state.evaluation_result = None
            st.session_state.step = "company_select"
            st.rerun()
        
        if st.button("같은 시나리오로 다시 시작", key="restart_same"):
            # 채팅 관련 상태만 초기화
            st.session_state.thread_id = None
            st.session_state.chat_messages = []
            st.session_state.assistant_id = None
            st.session_state.evaluation_result = None
            st.session_state.step = "chat"
            st.rerun()