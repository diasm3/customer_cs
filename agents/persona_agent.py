import uuid
import re
import json
import copy  # copy 모듈 추가
from datetime import datetime

import asyncio
from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Literal, Optional, TypedDict, Any, Dict, List

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage 

# Transformers 및 토치 임포트 추가
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, GenerationConfig  # GenerationConfig 추가
from peft import PeftModel  # PeftModel 추가

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore


from graphDB.neo4j import (
    Neo4jHybridSearch,
    save_conversation_log,
    async_save_conversation_log,
    async_check_schema
)

# MCP Client import
from langchain_mcp_adapters.client import MultiServerMCPClient


# 기업 페르소나 모듈 임포트
from data.personas.company_personas import (
    get_persona_by_id, 
    get_persona_prompt, 
    list_available_personas,
    get_scenarios_by_company,
    get_scenario
)

# 절대 경로로 configuration 모듈 임포트
import agents.configuration as configuration


# 모델 타입 정의
MODEL_TYPE = Literal["solar", "qwen3"]

# SOLAR 모델 초기화 - Transformers 라이브러리 사용
print("로컬에서 모델 로딩 준비 중...")

# 전역 변수로 모델 및 토크나이저 선언
tokenizer = None
model = None
qwen3_tokenizer = None
qwen3_model = None

# 모델 로딩 함수 정의
def load_solar_model():
    global tokenizer, model
    try:
        # 모델이 이미 로드되었는지 확인
        if tokenizer is not None and model is not None:
            return
            
        # 토크나이저 및 모델 로드
        tokenizer = AutoTokenizer.from_pretrained("Upstage/SOLAR-10.7B-Instruct-v1.0")
        model = AutoModelForCausalLM.from_pretrained(
            "Upstage/SOLAR-10.7B-Instruct-v1.0",
            device_map="auto",
            torch_dtype=torch.float16,
        )
        print("SOLAR 모델 로딩 완료!")
    except Exception as e:
        print(f"SOLAR 모델 로딩 중 오류 발생: {str(e)}")
        raise

# Qwen3 모델 로딩 함수 정의
def load_qwen3_model():
    global qwen3_tokenizer, qwen3_model
    try:
        # 모델이 이미 로드되었는지 확인
        if qwen3_tokenizer is not None and qwen3_model is not None:
            return
            
        # 기본 모델 및 파인튜닝된 모델 경로
        base_model = "Qwen/Qwen3-4B"
        output_dir = "./models/skt_persona_qwen3_final"
        
        # 파인튜닝된 Qwen3 모델 로드
        qwen3_tokenizer = AutoTokenizer.from_pretrained(output_dir, trust_remote_code=True)
        
        # 기본 모델 로드 후 어댑터 적용
        base_model_instance = AutoModelForCausalLM.from_pretrained(
            base_model,
            device_map="auto",
            torch_dtype=torch.float16,
            trust_remote_code=True
        )
        
        # PeftModel을 사용하여 어댑터 로드
        qwen3_model = PeftModel.from_pretrained(base_model_instance, output_dir)
        qwen3_model.eval()
        
        print("Qwen3 모델 로딩 완료!")
    except Exception as e:
        print(f"Qwen3 모델 로딩 중 오류 발생: {str(e)}")
        raise

# 비동기적으로 SOLAR 모델을 사용하여 응답 생성
async def generate_solar_response(messages, temperature=0.2, max_length=4096):
    """SOLAR 모델을 사용하여 메시지에 대한 응답을 생성합니다."""
    try:
        # 모델이 로드되었는지 확인
        if tokenizer is None or model is None:
            # 별도 스레드에서 모델 로드
            await asyncio.to_thread(load_solar_model)
        
        # 채팅 형식으로 변환
        conversation = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                conversation.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "assistant", "content": msg.content})
            elif getattr(msg, 'role', None) == 'tool':
                # 도구 응답은 사용자 메시지처럼 처리
                conversation.append({"role": "user", "content": f"도구 응답: {msg.content}"})
        
        # 프롬프트 생성
        prompt = await asyncio.to_thread(
            lambda: tokenizer.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
        )
        
        # 모델 입력 토큰화
        inputs = await asyncio.to_thread(
            lambda: tokenizer(prompt, return_tensors="pt").to(model.device)
        )
        
        # 생성 매개변수 설정 - 수정된 방식
        # 방법 1: 직접 파라미터 전달 방식
        generation_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "max_length": max_length,
            "repetition_penalty": 1.1,
            "top_p": 0.95
        }
        
        # 응답 생성 - 직접 매개변수 사용
        outputs = await asyncio.to_thread(
            lambda: model.generate(**inputs, **generation_kwargs)
        )
        
        # 결과 디코딩
        output_text = await asyncio.to_thread(
            lambda: tokenizer.decode(outputs[0], skip_special_tokens=True)
        )
        
        # 원본 프롬프트 제거하여 실제 응답만 추출
        response_only = output_text[len(prompt):].strip()
        
        print(f"SOLAR 생성 결과: {response_only}")
        return response_only
        
    except Exception as e:
        print(f"SOLAR 응답 생성 중 오류 발생: {str(e)}")
        return f"죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"

# 비동기적으로 Qwen3 모델을 사용하여 응답 생성
async def generate_qwen3_response(messages, temperature=0.2, max_length=4096):
    """Qwen3 모델을 사용하여 메시지에 대한 응답을 생성합니다."""
    try:
        # 모델이 로드되었는지 확인
        if qwen3_tokenizer is None or qwen3_model is None:
            # 별도 스레드에서 모델 로드
            await asyncio.to_thread(load_qwen3_model)
        
        # 채팅 형식으로 변환
        conversation = []
        for msg in messages:
            if isinstance(msg, SystemMessage):
                conversation.append({"role": "system", "content": msg.content})
            elif isinstance(msg, HumanMessage):
                conversation.append({"role": "user", "content": msg.content})
            elif isinstance(msg, AIMessage):
                conversation.append({"role": "assistant", "content": msg.content})
            elif getattr(msg, 'role', None) == 'tool':
                # 도구 응답은 사용자 메시지처럼 처리
                conversation.append({"role": "user", "content": f"도구 응답: {msg.content}"})
        
        # 프롬프트 생성
        prompt = await asyncio.to_thread(
            lambda: qwen3_tokenizer.apply_chat_template(conversation, tokenize=False, add_generation_prompt=True)
        )
        
        # 모델 입력 토큰화
        inputs = await asyncio.to_thread(
            lambda: qwen3_tokenizer(prompt, return_tensors="pt").to(qwen3_model.device)
        )
        
        # 생성 매개변수 설정
        generation_kwargs = {
            "do_sample": True,
            "temperature": temperature,
            "max_length": max_length,
            "repetition_penalty": 1.1,
            "top_p": 0.95
        }
        
        # 응답 생성
        outputs = await asyncio.to_thread(
            lambda: qwen3_model.generate(**inputs, **generation_kwargs)
        )
        
        # 결과 디코딩
        output_text = await asyncio.to_thread(
            lambda: qwen3_tokenizer.decode(outputs[0], skip_special_tokens=True)
        )
        
        # 원본 프롬프트 제거하여 실제 응답만 추출
        response_only = output_text[len(prompt):].strip()
        
        print(f"Qwen3 생성 결과: {response_only}")
        return response_only
        
    except Exception as e:
        print(f"Qwen3 응답 생성 중 오류 발생: {str(e)}")
        return f"죄송합니다, 응답을 생성하는 중에 오류가 발생했습니다: {str(e)}"

# 선택한 모델에 따라 응답 생성
async def generate_model_response(messages, model_type: MODEL_TYPE = "qwen3", temperature=0.2, max_length=4096):
    """선택된 모델 타입에 따라 적절한 모델을 사용하여 응답을 생성합니다."""
    if model_type == "solar":
        return await generate_solar_response(messages, temperature, max_length)
    elif model_type == "qwen3":
        return await generate_qwen3_response(messages, temperature, max_length)
    else:
        raise ValueError(f"지원되지 않는 모델 타입입니다: {model_type}")

# MCP client setup function
async def setup_mcp_client():
    """Set up MCP client and get tools."""
    client = MultiServerMCPClient(
        {
            "search_web": {  # Updated tool name to match what the model is calling
                "url": "http://localhost:8888/mcp",
                "transport": "sse",
                "headers": {
                    "X-API-Key": "BSAr3F0nX--2BIzA9UuHboU56Pi62E6",
                    "x-subscription-token": "BSAr3F0nX--2BIzA9UuHboU56Pi62E6"
                }
            },
            # "neo4j-aura": {
            #     "command": "uvx",
            #     "args": ["mcp-neo4j-cypher@0.2.1"],
            #     "env": {
            #         "NEO4J_URI": "bolt://localhost:7687",
            #         "NEO4J_USERNAME": "neo4j",
            #         "NEO4J_PASSWORD": "password123",
            #         "NEO4J_DATABASE": "neo4j"
            #     },
            #     "transport": "stdio",
            # },
        }
    )
    await client.__aenter__()
    return client

# MCP tool handling node
async def handle_mcp_tools(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Node to handle MCP tools like search."""
    print("Handling MCP tool call...")
    # Get the MCP client and tools
    client = await setup_mcp_client()
    try:
        # Get tools from MCP server
        tools = client.get_tools()
        print(f"Retrieved tools: {tools}")
        
        # Extract the tool call details
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        # Process each tool call
        result_messages = []
        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            tool_name = tool_call["name"]
            
            try:
                # Find the matching tool
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool:
                    # Execute the tool - use ainvoke instead of invoke for async tools
                    tool_args = tool_call.get("args", {})
                    tool_result = await tool.ainvoke(tool_args)
                    
                    # Create a proper tool response message
                    result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(tool_result)
                    })
                else:
                    # Tool not found
                    result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"Tool '{tool_name}' not found"
                    })
            except Exception as e:
                # Handle tool execution error
                print(f"Error executing tool {tool_name}: {str(e)}")
                result_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error executing tool: {str(e)}"
                })
        
        # Return all tool response messages
        return {"messages": result_messages}
    except Exception as e:
        print(f"Error in handle_mcp_tools: {str(e)}")
        # Return fallback responses for all tool calls
        result_messages = []
        for tool_call in state["messages"][-1].tool_calls:
            result_messages.append({
                "role": "tool",
                "tool_call_id": tool_call["id"],
                "content": f"검색 실패: {str(e)}"
            })
        return {"messages": result_messages}
    finally:
        await client.__aexit__(None, None, None)

# 페르소나 기반 응답 생성 함수
async def persona_assistant(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """페르소나 기반 응답을 생성하는 노드 함수"""

    print(f"Initializing Persona Assistant...{config}")
    
    # 설정에서 페르소나 정보 가져오기
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    print(f"Configurable: {configurable}")
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    company_id = configurable.company_id
    scenario_id = configurable.scenario_id
    model_type = getattr(configurable, 'model_type', "qwen3")  # 기본값은 SOLAR 모델

    # Neo4j 객체 생성은 동기적이지만 실제 DB 연결이나 쿼리는 비동기 처리
    # 싱글톤 패턴 활용
    neo4j_search = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password123"
    )

    print(f"Persona Assistant initialized with company_id: {company_id} and scenario_id: {scenario_id} {neo4j_search}")

    # 대화 컨텍스트 생성
    conversation_context = {
        'company_id': company_id,
        'scenario_id': scenario_id,
        'conversation_history': state["messages"][-5:] if len(state["messages"]) > 5 else state["messages"]
    }
    
    try:
        last_message = state["messages"][-1]
        if isinstance(last_message, HumanMessage):
            query = last_message.content
            print(f"User query: {query}")
            
            # 비동기적으로 하이브리드 검색 실행
            search_results = await neo4j_search.async_hybrid_search(query, conversation_context)

            print(f"Search results: {search_results}")
            
            # 검색 결과를 컨텍스트에 추가
            search_context = "\n\n관련 정보:\n"
            for result in search_results:
                search_context += f"- {result['content']}\n"
        else:
            search_context = ""
        
        # 페르소나 프롬프트 가져오기
        persona_prompt = configurable.get_persona_prompt()
        scenario_info = configurable.get_scenario_info()
        print(f"Persona prompt: {persona_prompt} {scenario_info}")
        
        scenario_context = ""
        if scenario_info:
            scenario_context = f"\n시나리오: {scenario_info['title']} - {scenario_info['description']}"
    
        # Retrieve profile memory from the store
        namespace = ("profile", todo_category, user_id)
        memories = await store.asearch(namespace)
        if memories:
            user_profile = memories[0].value
        else:
            user_profile = None
    
        # Retrieve people memory from the store
        namespace = ("todo", todo_category, user_id)
        memories = await store.asearch(namespace)
        todo = "\n".join(f"{mem.value}" for mem in memories)
    
        # Retrieve custom instructions
        namespace = ("instructions", todo_category, user_id)
        memories = await store.asearch(namespace)
        if memories:
            instructions = memories[0].value
        else:
            instructions = ""
        
        # Setup MCP client to get tools
        client = await setup_mcp_client()
        try:
            # Get tools from MCP server
            mcp_tools = client.get_tools()
            
            # Combine MCP tools with existing tools
            all_tools = [UpdateMemory] + mcp_tools
            
            # 페르소나 기반 시스템 메시지 구성
            system_msg = f"""당신은 {persona_prompt}
    
    당신의 역할은 위의 기업 페르소나에 맞게 고객 응대를 하는 것입니다.
    
    <scenario context>
    {scenario_context}
    </search context>
    
    고객 정보: 
    <user_profile>
    {user_profile}
    </user_profile>
    
    메모:
    <todo>
    {todo}
    </todo>
    
    추가 지침:
    <instructions>
    {instructions}
    </instructions>
    
    당신은 또한 웹 검색 도구를 사용할 수 있습니다. 고객이 최신 정보나 사실 확인이 필요한 질문을 할 경우, 검색 도구를 사용하세요.
    검색 결과는 기업의 톤앤매너와 원칙에 맞게 전달하세요.
    """
            
            # SOLAR 또는 Qwen3 모델 사용하여 응답 생성
            messages = [SystemMessage(content=system_msg)] + state["messages"]
            
            try:
                # 선택된 모델을 사용하여 응답 생성
                response_text = await generate_model_response(messages, model_type)
                
                # 도구 호출 확인 및 추출
                # tool_calls = extract_tool_calls(response_text)
                
                # AIMessage 생성
                ai_message = AIMessage(content=response_text)
                
                # 도구 호출이 있다면 추가
                # if tool_calls:
                #     ai_message.tool_calls = tool_calls
                
                # 비동기적으로 대화 로그 저장
                await async_save_conversation_log(state, ai_message, conversation_context)
                
                return {"messages": [ai_message]}
            except Exception as e:
                print(f"모델 응답 생성 오류: {str(e)}")
                error_msg = f"죄송합니다, 응답을 생성하는 중에 문제가 발생했습니다: {str(e)}"
                return {"messages": [AIMessage(content=error_msg)]}
        finally:
            await client.__aexit__(None, None, None)
    finally:
        # 명시적으로 비동기 종료 메서드 호출 - 이것은 neo4j 연결을 직접 닫지 않고 관리만 함
        await neo4j_search.async_close()

# Update memory tool
class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['user', 'todo', 'instructions']

# Update memory functions with proper tool response format
def update_todos(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Update todos memory."""
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    # Get the tool call
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    # Process todo update logic
    todo_info = tool_call.get("args", {}).get("information", "")
    if todo_info:
        # Save new todo to the store
        namespace = ("todo", todo_category, user_id)
        key = f"todo_{uuid.uuid4()}"
        store.put(namespace, key, todo_info)
    
    # Return a proper tool response
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "Todos updated successfully"}]}

def update_profile(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Update user profile memory."""
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    # Get the tool call
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    # Process profile update logic
    profile_info = tool_call.get("args", {}).get("information", "")
    if profile_info:
        # Update profile in the store
        namespace = ("profile", todo_category, user_id)
        key = "profile"
        store.put(namespace, key, profile_info)
    
    # Return a proper tool response
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "User profile updated successfully"}]}

def update_instructions(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """Update custom instructions memory."""
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    # Get the tool call
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    # Process instructions update logic
    instructions = tool_call.get("args", {}).get("information", "")
    if instructions:
        # Update instructions in the store
        namespace = ("instructions", todo_category, user_id)
        key = "instructions"
        store.put(namespace, key, instructions)
    
    # Return a proper tool response
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "Custom instructions updated successfully"}]}

# 라우팅 함수 업데이트
def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "update_todos", "update_instructions", "update_profile", "handle_mcp_tools"]:
    """Reflect on the memories and chat history to decide whether to update the memory collection."""
    message = state['messages'][-1]
    if len(message.tool_calls) == 0:
        return END
    else:
        # Check each tool call - we need to route ALL tool calls properly
        for tool_call in message.tool_calls:
            # Check for Neo4j or search tool calls (MCP)
            if tool_call.get('name') in ['brave_search', 'search_web', 'neo4j_cypher', 'get_neo4j_schema'] or 'neo4j' in tool_call.get('name', '').lower():
                return "handle_mcp_tools"
                
        # If none of the above, check for UpdateMemory tool calls
        tool_call = message.tool_calls[0]  # Use the first tool call for UpdateMemory
        if tool_call.get('name') == 'UpdateMemory' and 'update_type' in tool_call.get('args', {}):
            update_type = tool_call['args']['update_type']
            if update_type == "user":
                return "update_profile"
            elif update_type == "todo":
                return "update_todos"
            elif update_type == "instructions":
                return "update_instructions"
        
        # Default - route to handle_mcp_tools to ensure all tool calls get responses
        return "handle_mcp_tools"

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration)

# 설정 스키마 정의
# builder.set_config_schema(configuration)

# Define the nodes
builder.add_node("persona_assistant", persona_assistant)
builder.add_node("handle_mcp_tools", handle_mcp_tools)
builder.add_node("update_todos", update_todos)
builder.add_node("update_profile", update_profile)
builder.add_node("update_instructions", update_instructions)

# Define the flow
builder.add_edge(START, "persona_assistant")

# Add conditional edges for tool routing
builder.add_conditional_edges(
    "persona_assistant",
    route_message,
    {
        "update_todos": "update_todos",
        "update_profile": "update_profile",
        "update_instructions": "update_instructions",
        "handle_mcp_tools": "handle_mcp_tools",
        END: END
    }
)

# Add connections from MCP tool handling back to the assistant
builder.add_edge("handle_mcp_tools", "persona_assistant")

# Connect memory update nodes back to the assistant
builder.add_edge("update_todos", "persona_assistant")
builder.add_edge("update_profile", "persona_assistant")
builder.add_edge("update_instructions", "persona_assistant")

# Compile the graph
graph = builder.compile()