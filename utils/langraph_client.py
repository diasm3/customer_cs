from langgraph_sdk import get_client
from typing import Dict, List, Any, Optional, AsyncIterator
import asyncio
import json

# LangGraph SDK 클라이언트 생성
async def create_langgraph_client(base_url: str = "http://localhost:2024"):
    """LangGraph SDK 클라이언트를 생성합니다."""
    try:
        # SDK의 get_client 함수를 사용하여 클라이언트 생성
        client = get_client(url=base_url)
        print("LangGraph 클라이언트 생성 완료", client)
        return client
    except Exception as e:
        print(f"LangGraph 클라이언트 생성 오류: {str(e)}")
        raise e

# LangGraph 클라이언트 확장 유틸리티 함수들
async def create_thread(client):
    """새 스레드를 생성합니다."""
    try:
        thread = await client.threads.create()
        return thread["thread_id"]
    except Exception as e:
        print(f"스레드 생성 오류: {str(e)}")
        raise e

async def add_message_to_thread(client, thread_id: str, message: str, role: str = "user"):
    """스레드에 메시지를 추가합니다."""
    try:
        message_data = {"role": role, "content": message}
        await client.messages.create(thread_id, message_data)
    except Exception as e:
        print(f"메시지 추가 오류: {str(e)}")
        raise e

async def run_thread_with_graph(client, thread_id: str, graph_id: str, config: Optional[Dict[str, Any]] = None):
    """스레드를 특정 그래프로 실행합니다."""
    try:
        run_params = {}
        if config:
            run_params["config"] = config
            
        run = await client.runs.create(thread_id, graph_id, **run_params)
        return run["run_id"]
    except Exception as e:
        print(f"스레드 실행 오류: {str(e)}")
        raise e

async def wait_for_run_completion(client, thread_id: str, run_id: str, interval: float = 0.5):
    """실행이 완료될 때까지 대기합니다."""
    try:
        while True:
            run_state = await client.runs.get(thread_id, run_id)
            if run_state["status"] in ["succeeded", "failed", "cancelled"]:
                return run_state
            await asyncio.sleep(interval)
    except Exception as e:
        print(f"실행 상태 확인 오류: {str(e)}")
        raise e

async def get_thread_messages(client, thread_id: str):
    """스레드의 모든 메시지를 가져옵니다."""
    try:
        messages = await client.messages.list(thread_id)
        return messages
    except Exception as e:
        print(f"메시지 가져오기 오류: {str(e)}")
        raise e

async def get_assistants(client):
    """사용 가능한 assistants 목록을 가져옵니다."""
    try:
        assistants = await client.assistants.list()
        return assistants
    except Exception as e:
        print(f"어시스턴트 목록 가져오기 오류: {str(e)}")
        raise e

async def create_assistant(client, graph_id: str, config: Dict[str, Any] = None):
    """새 assistant를 생성합니다."""
    try:
        assistant_params = {}
        if config:
            assistant_params["config"] = config
            
        assistant = await client.assistants.create(graph_id, **assistant_params)
        return assistant
    except Exception as e:
        print(f"어시스턴트 생성 오류: {str(e)}")
        raise e

async def find_or_create_assistant(client, graph_id: str, config: Dict[str, Any]):
    """설정에 맞는 assistant를 찾거나 생성합니다."""
    try:
        # 현재 모든 어시스턴트 목록 가져오기
        assistants = await client.assistants.search()
        # assistants = await client.assistants.list()
        print(f"현재 어시스턴트 목록: {assistants}")
        
        # 설정값과 일치하는 어시스턴트 찾기
        for assistant in assistants:
            if assistant.get("graph_id") == graph_id:
                assistant_config = assistant.get("config", {}).get("configurable", {})
                
                # 주요 설정값이 일치하는지 확인 (company_id, scenario_id)
                if (assistant_config.get("company_id") == config.get("configurable", {}).get("company_id") and
                    assistant_config.get("scenario_id") == config.get("configurable", {}).get("scenario_id")):
                    return assistant["assistant_id"]
        
        # 일치하는 어시스턴트가 없으면 새로 생성
        new_assistant = await client.assistants.create(graph_id, **config)
        return new_assistant["assistant_id"]
    except Exception as e:
        print(f"어시스턴트 찾기/생성 오류: {str(e)}")
        raise e

async def send_message_and_wait_response(client, graph_id: str, thread_id: str, message: str, config: Optional[Dict[str, Any]] = None):
    """메시지를 전송하고 응답을 기다리는 편의 함수"""
    try:
        # 어시스턴트 ID 찾기 또는 생성
        assistant_id = await find_or_create_assistant(client, graph_id, {"configurable": config} if config else {})
        
        # 메시지 추가
        await client.messages.create(thread_id, {"role": "user", "content": message})
        
        # 실행 시작
        run = await client.runs.create(thread_id, assistant_id)
        run_id = run["run_id"]
        
        # 실행 완료 대기
        await wait_for_run_completion(client, thread_id, run_id)
        
        # 메시지 가져오기
        messages = await client.messages.list(thread_id)
        
        # 마지막 응답 반환
        for msg in reversed(messages):
            if msg["role"] == "assistant":
                return msg["content"]
        
        return "응답을 찾을 수 없습니다."
    except Exception as e:
        print(f"메시지 처리 오류: {str(e)}")
        raise e

async def stream_run(client, thread_id: str, assistant_id: str, input_data: Optional[Dict[str, Any]] = None, stream_mode: str = "values"):
    """
    스트리밍 방식으로 실행 결과를 받습니다.
    
    Args:
        client: LangGraph 클라이언트
        thread_id: 스레드 ID
        assistant_id: 어시스턴트 ID
        input_data: 입력 데이터 (메시지 등)
        stream_mode: 스트림 모드 ("values" 또는 "steps")
        
    Returns:
        AsyncIterator: 스트리밍 결과 이터레이터
    """
    try:
        # 실행 파라미터 설정
        run_params = {}
        if input_data:
            run_params["input"] = input_data
            
        # 스트리밍 실행 시작
        stream = client.runs.stream(
            thread_id=thread_id,
            assistant_id=assistant_id,
            stream_mode=stream_mode,
            **run_params
        )
        
        return stream
    except Exception as e:
        print(f"스트리밍 실행 오류: {str(e)}")
        raise e

async def get_last_assistant_message(messages: List[Dict[str, Any]]) -> Optional[str]:
    """
    메시지 목록에서 마지막 어시스턴트 메시지를 추출합니다.
    
    Args:
        messages: 메시지 목록
        
    Returns:
        Optional[str]: 마지막 어시스턴트 메시지 내용 또는 None
    """
    for msg in reversed(messages):
        if msg.get("role") == "assistant" or msg.get("type") == "ai":
            if isinstance(msg.get("content"), str) and msg.get("content"):
                return msg.get("content")
    return None

async def generate_company_response_async(client, thread_id: str, user_message: str, company_id: str, scenario_id: str, user_id: str):
    """
    사용자 메시지에 대한 기업 응답을 생성합니다 (스트리밍 방식).
    
    Args:
        client: LangGraph 클라이언트
        thread_id: 스레드 ID
        user_message: 사용자 메시지
        company_id: 기업 ID
        scenario_id: 시나리오 ID
        user_id: 사용자 ID
        
    Returns:
        str: 생성된 응답 메시지
    """
    try:
        # 설정 정보
        config = {
            "user_id": user_id,
            "todo_category": f"{company_id}_{scenario_id}",
            "company_id": company_id,
            "scenario_id": scenario_id
        }
        
        # 새 어시스턴트 생성
        assistant_id = await find_or_create_assistant(
            client, 
            "persona_graph", 
            {"configurable": config}
        )
        
        # 입력 데이터 구성
        input_data = {"messages": [{"role": "user", "content": user_message}]}
        
        # 응답 청크 및 최신 AI 메시지 초기화
        response_chunks = []
        latest_ai_message = None
        
        # 스트림 실행 및 청크 처리
        async for chunk in await stream_run(client, thread_id, assistant_id, input_data, "values"):
            if chunk.event == 'values':
                state = chunk.data
                if 'messages' in state:
                    # 최신 AI 메시지 검색
                    current_message = await get_last_assistant_message(state['messages'])
                    if current_message and current_message != latest_ai_message:
                        latest_ai_message = current_message
                        # 이미 있는 응답이 아니라면 추가
                        if current_message not in response_chunks:
                            response_chunks.append(current_message)
        
        # 최종 응답 반환
        return latest_ai_message if latest_ai_message else "응답을 생성하지 못했습니다."
    
    except Exception as e:
        print(f"응답 생성 오류: {str(e)}")
        return f"죄송합니다. 응답 생성 중 오류가 발생했습니다: {str(e)}"