import streamlit as st
import json
import time
import asyncio
from datetime import datetime
from langchain_core.messages import HumanMessage
from langgraph_sdk import get_client

# LangGraph 클라이언트 설정
URL_FOR_DEPLOYMENT = "http://localhost:2024"  # LangGraph 서버 URL
try:
    client = get_client(url=URL_FOR_DEPLOYMENT)
except Exception as e:
    st.error(f"LangGraph 서버 연결 실패: {str(e)}")
    client = None

# LangGraph 비동기 함수 실행을 위한 헬퍼 함수
async def run_async(coroutine):
    return await coroutine

# LangGraph와 연동하여 AI 응답을 비동기적으로 생성
async def generate_company_response_async(message, company_id, scenario_id, assistant_id=None):
    """LangGraph를 통해 AI 응답을 비동기적으로 생성합니다."""
    if client is None:
        return "서버 연결에 실패했습니다. 관리자에게 문의하세요."
    
    try:
        # 어시스턴트 ID가 없으면 새 어시스턴트 생성
        if assistant_id is None:
            # 어시스턴트 목록 조회
            assistants = await client.assistants.search()
            
            # 회사 ID와 시나리오에 맞는 어시스턴트 찾기
            for assistant in assistants:
                config = assistant.get("config", {}).get("configurable", {})
                if config.get("company_id") == company_id and config.get("scenario_id") == scenario_id:
                    assistant_id = assistant["assistant_id"]
                    break
            
            # 찾지 못했다면 새 어시스턴트 생성
            if assistant_id is None:
                # 페르소나 에이전트를 사용하여 응답 생성
                graph_name = "graph"  # 수정된 그래프 이름
                st.info(f"회사 '{company_id}'와 시나리오 '{scenario_id}'에 맞는 어시스턴트를 생성합니다.")
                
                # PersonaConfiguration 스키마에 맞는 설정 생성
                assistant = await client.assistants.create(
                    graph_name,
                    config={
                        "configurable": {
                            # "user_id": st.session_state.nickname,
                            # "todo_category": company_id,
                            "company_id": company_id,
                            "scenario_id": scenario_id,
                            # "task_maistro_role": f"{company_id} 기업의 CS 담당자로서 고객 응대를 하는 역할"
                        }
                    }
                )
                assistant_id = assistant["assistant_id"]
        
        # 쓰레드 생성 또는 기존 쓰레드 사용
        if "thread_id" not in st.session_state:
            thread = await client.threads.create()
            st.session_state.thread_id = thread["thread_id"]
        
        # 메시지를 LangGraph로 전송
        input_data = {"messages": [HumanMessage(content=message)]}
        
        # 스트리밍으로 응답 받기
        response_chunks = []
        async for chunk in client.runs.stream(
            st.session_state.thread_id,
            assistant_id,
            input=input_data,
            stream_mode="values"
        ):
            if chunk.event == 'values':
                state = chunk.data
                for msg in state.get("messages", []):
                    if hasattr(msg, "content") and msg.content:
                        response_chunks.append(msg.content)
        
        # 응답 합치기
        full_response = "".join(response_chunks) if response_chunks else "응답을 생성하지 못했습니다."
        return full_response
        
    except Exception as e:
        st.error(f"LangGraph API 호출 중 오류 발생: {str(e)}")
        return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"

def generate_company_response(message, company_id, scenario_id):
    """동기적 래퍼 함수"""
    # asyncio run_in_executor 사용하기 위한 헬퍼 함수
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        # 비동기 함수 실행
        with st.spinner('응답 생성 중...'):
            result = loop.run_until_complete(
                generate_company_response_async(message, company_id, scenario_id)
            )
        return result
    except Exception as e:
        st.error(f"응답 생성 오류: {str(e)}")
        return "죄송합니다. 일시적인 오류가 발생했습니다. 잠시 후 다시 시도해 주세요."
    finally:
        loop.close()

# 페이지 설정
st.set_page_config(layout="wide", page_title="CS 대화 시뮬레이션")

# CSS 적용
st.write("""
<style>
    .main-title {
        font-size: 28px;
        font-weight: bold;
        margin-bottom: 20px;
    }
    .subtitle {
        font-size: 20px;
        font-weight: bold;
        margin: 15px 0;
    }
    .paragraph {
        margin: 10px 0;
    }
    .chat-container {
        height: 400px;
        overflow-y: auto;
        padding: 20px;
        border-radius: 10px;
        background-color: #f9f9f9;
        margin-bottom: 10px;
    }
    .user-message {
        background-color: #dcf8c6;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 80%;
        margin-left: auto;
        word-wrap: break-word;
    }
    .bot-message {
        background-color: #e5e5ea;
        padding: 10px;
        border-radius: 10px;
        margin: 5px 0;
        max-width: 80%;
        word-wrap: break-word;
    }
    .company-card {
        padding: 15px;
        border-radius: 10px;
        margin-bottom: 10px;
        background-color: #f0f2f6;
        border: 1px solid #ddd;
    }
    .company-name {
        font-size: 18px;
        font-weight: bold;
        margin-bottom: 8px;
    }
    .company-desc {
        margin-bottom: 8px;
    }
    .company-info {
        font-size: 14px;
        color: #666;
    }
    .divider {
        height: 1px;
        background-color: #ddd;
        margin: 20px 0;
    }
    .label {
        font-weight: bold;
        margin-right: 5px;
    }
    .scenario-box {
        background-color: #f8f9fa;
        border: 1px solid #dee2e6;
        border-radius: 8px;
        padding: 15px;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

# 세션 상태 초기화
if 'page' not in st.session_state:
    st.session_state.page = "login"
if 'chat_messages' not in st.session_state:
    st.session_state.chat_messages = []
if 'company' not in st.session_state:
    st.session_state.company = None
if 'scenario' not in st.session_state:
    st.session_state.scenario = None
if 'nickname' not in st.session_state:
    st.session_state.nickname = None

# 예시 기업 데이터
companies = [
    {
        "id": "skt",
        "name": "SK텔레콤",
        "description": "대한민국 1위 이동통신사로 최근 유심 해킹 사태를 겪고 있습니다.",
        "cs_style": "정중하고 전문적인 어조, 고객 보안을 최우선으로 고려",
        "industry": "통신"
    },
    {
        "id": "samsung",
        "name": "삼성전자",
        "description": "글로벌 전자제품 제조사로 스마트폰, 가전제품 등을 생산합니다.",
        "cs_style": "친절하고 기술적인 설명에 능숙함, 제품 전문성 강조",
        "industry": "전자제품"
    },
    {
        "id": "coupang",
        "name": "쿠팡",
        "description": "국내 최대 이커머스 플랫폼으로 로켓배송 서비스를 제공합니다.",
        "cs_style": "신속하고 효율적인 문제 해결, 고객 만족 중심",
        "industry": "이커머스"
    }
]

# 시나리오 데이터
scenarios = {
    "skt": [
        {
            "id": "usim_protection",
            "title": "유심 보호 서비스 문의",
            "description": "최근 유심 해킹 사태와 관련하여 유심 보호 서비스에 대해 문의하는 시나리오",
            "initial_response": "안녕하세요, SK텔레콤 고객센터입니다. 무엇을 도와드릴까요?"
        },
        {
            "id": "compensation_request",
            "title": "보상 요구",
            "description": "해킹 사태로 인한 정신적 피해에 대한 보상을 요구하는 시나리오",
            "initial_response": "안녕하세요, SK텔레콤입니다. 어떤 문제로 연락주셨나요?"
        }
    ],
    "samsung": [
        {
            "id": "device_issue",
            "title": "제품 불량 문의",
            "description": "스마트폰 화면 깜빡임 현상에 대해 문의하는 시나리오",
            "initial_response": "안녕하세요, 삼성전자 고객센터입니다. 어떤 제품에 대해 문의하시나요?"
        }
    ],
    "coupang": [
        {
            "id": "delivery_delay",
            "title": "배송 지연 문의",
            "description": "로켓배송 상품이 예정일에 도착하지 않은 상황",
            "initial_response": "안녕하세요, 쿠팡 고객센터입니다. 배송 관련 문의이신가요?"
        }
    ]
}

# 채팅 메시지 추가
def add_message(message, is_user=True):
    if is_user:
        st.session_state.chat_messages.append({"role": "user", "content": message})
    else:
        st.session_state.chat_messages.append({"role": "assistant", "content": message})

# 메인 UI 로직
if st.session_state.page == "login":
    # 로그인 페이지
    st.write("<div class='main-title'>CS 대화 시뮬레이션</div>", unsafe_allow_html=True)
    
    with st.container():
        st.write("<div class='subtitle'>👋 환영합니다!</div>", unsafe_allow_html=True)
        st.write("<div class='paragraph'>고객 역할로 CS 담당자와 대화를 나눠보세요.</div>", unsafe_allow_html=True)
        
        nickname = st.text_input("닉네임", placeholder="닉네임을 입력하세요")
        
        if st.button("시작하기") and nickname:
            st.session_state.nickname = nickname
            st.session_state.page = "company_select"
            st.rerun()

elif st.session_state.page == "company_select":
    # 기업 선택 페이지
    st.write("<div class='main-title'>기업 선택</div>", unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.write(f"<div class='subtitle'>안녕하세요, {st.session_state.nickname}님!</div>", unsafe_allow_html=True)
        st.write("<div class='paragraph'>대화할 기업을 선택해주세요.</div>", unsafe_allow_html=True)
        
        if st.button("로그아웃"):
            st.session_state.nickname = None
            st.session_state.page = "login"
            st.rerun()
    
    # 기업 카드 표시
    st.write("<div class='subtitle'>어떤 기업과 대화하시겠어요?</div>", unsafe_allow_html=True)
    
    cols = st.columns(3)
    
    for i, company in enumerate(companies):
        with cols[i % 3]:
            st.write(f"""
            <div class='company-card'>
                <div class='company-name'>{company['name']}</div>
                <div class='company-desc'>{company['description']}</div>
                <div class='company-info'>산업: {company['industry']}</div>
                <div class='company-info'>CS 스타일: {company['cs_style']}</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("선택", key=f"company_{i}"):
                st.session_state.company = company
                st.session_state.page = "scenario_select"
                st.rerun()

elif st.session_state.page == "scenario_select":
    # 시나리오 선택 페이지
    st.write("<div class='main-title'>시나리오 선택</div>", unsafe_allow_html=True)
    
    # 사이드바
    with st.sidebar:
        st.write(f"<div class='subtitle'>{st.session_state.company['name']} CS 상담</div>", unsafe_allow_html=True)
        st.write(f"<div class='paragraph'>고객: {st.session_state.nickname}님</div>", unsafe_allow_html=True)
        
        if st.button("기업 다시 선택"):
            st.session_state.company = None
            st.session_state.page = "company_select"
            st.rerun()
    
    st.write(f"<div class='subtitle'>{st.session_state.company['name']} - 상황 선택</div>", unsafe_allow_html=True)
    
    company_scenarios = scenarios.get(st.session_state.company['id'], [])
    
    for i, scenario in enumerate(company_scenarios):
        st.write(f"""
        <div class='scenario-box'>
            <div class='subtitle'>{scenario['title']}</div>
            <div class='paragraph'>{scenario['description']}</div>
        </div>
        """, unsafe_allow_html=True)
        
        if st.button("이 상황으로 시작", key=f"scenario_{i}"):
            st.session_state.scenario = scenario
            st.session_state.chat_messages = []
            st.session_state.page = "chat"
            # 초기 인사 추가
            add_message(scenario['initial_response'], is_user=False)
            st.rerun()

elif st.session_state.page == "chat":
    # 채팅 페이지
    if st.session_state.company is None or st.session_state.scenario is None:
        st.warning("기업과 시나리오를 먼저 선택해주세요.")
        if st.button("돌아가기"):
            st.session_state.page = "company_select"
            st.rerun()
    else:
        # 사이드바
        with st.sidebar:
            st.write(f"<div class='subtitle'>{st.session_state.company['name']} CS</div>", unsafe_allow_html=True)
            st.write(f"<div class='paragraph'>시나리오: {st.session_state.scenario['title']}</div>", unsafe_allow_html=True)
            st.write(f"<div class='paragraph'>고객: {st.session_state.nickname}님</div>", unsafe_allow_html=True)
            
            st.write("<div class='divider'></div>", unsafe_allow_html=True)
            
            if st.button("시나리오 다시 선택"):
                st.session_state.scenario = None
                st.session_state.page = "scenario_select"
                st.rerun()
        
        # 메인 채팅 UI
        st.write(f"<div class='main-title'>{st.session_state.company['name']} CS 상담</div>", unsafe_allow_html=True)
        st.write(f"<div class='paragraph'>시나리오: {st.session_state.scenario['title']}</div>", unsafe_allow_html=True)
        
        # 채팅 메시지 표시
        chat_html = "<div class='chat-container'>"
        
        for msg in st.session_state.chat_messages:
            if msg["role"] == "user":
                chat_html += f"<div class='user-message'>{msg['content']}</div>"
            else:
                chat_html += f"<div class='bot-message'>{msg['content']}</div>"
        
        chat_html += "</div>"
        st.write(chat_html, unsafe_allow_html=True)
        
        # 메시지 입력
        with st.form(key="message_form", clear_on_submit=True):
            user_input = st.text_input("메시지 입력:", key="user_message")
            send_button = st.form_submit_button("전송")
            
            if send_button and user_input:
                # 사용자 메시지 추가
                add_message(user_input)
                
                # CS 응답 생성
                cs_response = generate_company_response(
                    user_input, 
                    st.session_state.company['id'], 
                    st.session_state.scenario['id']
                )
                add_message(cs_response, is_user=False)
                
                st.rerun()
        
        # 대화 종료 버튼
        if len(st.session_state.chat_messages) >= 4:  # 최소 2턴 이상 대화 후
            if st.button("대화 종료"):
                st.success("대화가 종료되었습니다!")
                st.write("<div class='subtitle'>상담 요약</div>", unsafe_allow_html=True)
                st.write(f"<div class='paragraph'>기업: {st.session_state.company['name']}</div>", unsafe_allow_html=True)
                st.write(f"<div class='paragraph'>시나리오: {st.session_state.scenario['title']}</div>", unsafe_allow_html=True)
                st.write(f"<div class='paragraph'>대화 턴 수: {len(st.session_state.chat_messages) // 2}</div>", unsafe_allow_html=True)
                
                if st.button("새 대화 시작"):
                    st.session_state.chat_messages = []
                    st.session_state.scenario = None
                    st.session_state.page = "scenario_select"
                    st.rerun()