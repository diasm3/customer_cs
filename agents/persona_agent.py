# agents/persona_agent.py
import uuid
import re
import json
import copy
from datetime import datetime

import asyncio
from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Literal, Optional, TypedDict, Any, Dict, List

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage 

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

# 🆕 키워드 분석 유틸리티 임포트
from utils.keyword_analyzer import (
    analyze_user_query_keywords,
    hybrid_search_neo4j
)

# 🆕 모델 유틸리티 임포트
from utils.model_utils import (
    MODEL_TYPE,
    generate_model_response
)

print("Enhanced Persona Assistant 로딩 중...")

# MCP client setup function
async def setup_mcp_client():
    client = MultiServerMCPClient(
        {
            "search_web": {
                "url": "http://localhost:8888/mcp",
                "transport": "sse",
                "headers": {
                    "X-API-Key": "BSAr3F0nX--2BIzA9UuHboU56Pi62E6",
                    "x-subscription-token": "BSAr3F0nX--2BIzA9UuHboU56Pi62E6"
                }
            },
        }
    )
    await client.__aenter__()
    return client

# MCP tool handling node
async def handle_mcp_tools(state: MessagesState, config: RunnableConfig, store: BaseStore):
    print("Handling MCP tool call...")
    client = await setup_mcp_client()
    try:
        tools = client.get_tools()
        print(f"Retrieved tools: {tools}")
        
        last_message = state["messages"][-1]
        tool_calls = last_message.tool_calls
        
        result_messages = []
        for tool_call in tool_calls:
            tool_call_id = tool_call["id"]
            tool_name = tool_call["name"]
            
            try:
                tool = next((t for t in tools if t.name == tool_name), None)
                if tool:
                    tool_args = tool_call.get("args", {})
                    tool_result = await tool.ainvoke(tool_args)
                    
                    result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": str(tool_result)
                    })
                else:
                    result_messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": f"Tool '{tool_name}' not found"
                    })
            except Exception as e:
                print(f"Error executing tool {tool_name}: {str(e)}")
                result_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": f"Error executing tool: {str(e)}"
                })
        
        return {"messages": result_messages}
    except Exception as e:
        print(f"Error in handle_mcp_tools: {str(e)}")
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

# Neo4j 비동기 Cypher 실행을 위한 확장 메서드 추가
async def async_execute_cypher(self, query: str, parameters: dict = None):
    """Neo4j에서 비동기 Cypher 쿼리 실행"""
    async with self._driver.session() as session:
        result = await session.run(query, parameters or {})
        return await result.data()

# Neo4jHybridSearch 클래스에 메서드 추가 (monkeypatch)
setattr(Neo4jHybridSearch, 'async_execute_cypher', async_execute_cypher)

# 🆕 키워드 분석이 통합된 페르소나 어시스턴트
async def enhanced_persona_assistant(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """키워드 분석이 통합된 페르소나 어시스턴트"""
    
    print(f"Initializing Enhanced Persona Assistant with keyword analysis...")
    
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    company_id = configurable.company_id
    scenario_id = configurable.scenario_id
    model_type = getattr(configurable, 'model_type', "gemma3:4b")

    neo4j_search = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password123"
    )

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
            
            # 🆕 유틸리티 함수로 키워드 분석 실행
            keyword_analysis = await analyze_user_query_keywords(query, company_id)
            print(f"Keyword Analysis: {keyword_analysis}")
            
            # 🆕 유틸리티 함수로 하이브리드 검색 실행
            search_results = await hybrid_search_neo4j(
                query, 
                keyword_analysis['transformed_query'], 
                neo4j_search
            )
            print(f"Search results: {search_results}")
            
            # 키워드 분석 결과를 검색 컨텍스트에 추가
            search_context = f"\n\n[키워드 분석 결과]\n"
            search_context += f"원본 질문: {query}\n"
            search_context += f"핵심 키워드: {keyword_analysis['transformed_query']}\n"
            search_context += f"주요 키워드: {', '.join([k['keyword'] for k in keyword_analysis['top_keywords']])}\n"
            search_context += f"질문 의도: {keyword_analysis['detected_intent']}\n"
            search_context += f"복잡도 점수: {keyword_analysis['complexity_score']:.2f}\n"
            
            # 카테고리별 키워드 정보 추가
            for category, keywords in keyword_analysis['categorized_keywords'].items():
                if keywords:
                    search_context += f"{category}: {', '.join([k['keyword'] for k in keywords])}\n"
            
            # 검색 결과를 컨텍스트에 추가
            search_context += "\n관련 정보:\n"
            for result in search_results:
                search_context += f"- {result['content']} (점수: {result['score']:.2f})\n"
        else:
            search_context = ""
            keyword_analysis = {}
        
        # 페르소나 및 메모리 정보 로드
        persona_prompt = configurable.get_persona_prompt()
        scenario_info = configurable.get_scenario_info()
        
        scenario_context = ""
        if scenario_info:
            scenario_context = f"\n시나리오: {scenario_info['title']} - {scenario_info['description']}"
    
        # 메모리 정보 로드
        namespace = ("profile", todo_category, user_id)
        memories = await store.asearch(namespace)
        user_profile = memories[0].value if memories else None
    
        namespace = ("todo", todo_category, user_id)
        memories = await store.asearch(namespace)
        todo = "\n".join(f"{mem.value}" for mem in memories)
    
        namespace = ("instructions", todo_category, user_id)
        memories = await store.asearch(namespace)
        instructions = memories[0].value if memories else ""
        
        try:
            all_tools = [UpdateMemory] 
            
            # 시스템 메시지 구성
            system_msg = f"""당신은 {persona_prompt}
    
당신의 역할은 위의 기업 페르소나에 맞게 고객 응대를 하는 것입니다.

<scenario context>
{scenario_context}
</scenario context>

<keyword analysis>
{search_context}
</keyword analysis>

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

검색 결과:
<search_results>
{search_context}
</search_results>

고객의 질문 의도와 주요 키워드를 참고하여 더 정확하고 맞춤형 응답을 제공하세요.
검색 결과는 기업의 톤앤매너와 원칙에 맞게 전달하세요.
"""
            
            # 🆕 모델 유틸리티로 응답 생성
            messages = [SystemMessage(content=system_msg)] + state["messages"]
            
            try:
                response_text = await generate_model_response(messages, model_type)
                ai_message = AIMessage(content=response_text)
                
                # 키워드 분석 정보를 포함한 대화 로그 저장
                enhanced_conversation_context = conversation_context.copy()
                enhanced_conversation_context['keyword_analysis'] = keyword_analysis
                
                await async_save_conversation_log(state, ai_message, enhanced_conversation_context)
                
                return {"messages": [ai_message]}
            except Exception as e:
                print(f"모델 응답 생성 오류: {str(e)}")
                error_msg = f"죄송합니다, 응답을 생성하는 중에 문제가 발생했습니다: {str(e)}"
                return {"messages": [AIMessage(content=error_msg)]}
        finally:
            print("Enhanced persona assistant completed")
    finally:
        await neo4j_search.async_close()

# Update memory tool
class UpdateMemory(TypedDict):
    update_type: Literal['user', 'todo', 'instructions']

# Update memory functions
def update_todos(state: MessagesState, config: RunnableConfig, store: BaseStore):
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    todo_info = tool_call.get("args", {}).get("information", "")
    if todo_info:
        namespace = ("todo", todo_category, user_id)
        key = f"todo_{uuid.uuid4()}"
        store.put(namespace, key, todo_info)
    
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "Todos updated successfully"}]}

def update_profile(state: MessagesState, config: RunnableConfig, store: BaseStore):
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    profile_info = tool_call.get("args", {}).get("information", "")
    if profile_info:
        namespace = ("profile", todo_category, user_id)
        key = "profile"
        store.put(namespace, key, profile_info)
    
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "User profile updated successfully"}]}

def update_instructions(state: MessagesState, config: RunnableConfig, store: BaseStore):
    configurable = configuration.PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    
    last_message = state["messages"][-1]
    tool_call = last_message.tool_calls[0]
    tool_call_id = tool_call["id"]
    
    instructions = tool_call.get("args", {}).get("information", "")
    if instructions:
        namespace = ("instructions", todo_category, user_id)
        key = "instructions"
        store.put(namespace, key, instructions)
    
    return {"messages": [{"role": "tool", "tool_call_id": tool_call_id, "content": "Custom instructions updated successfully"}]}

# 라우팅 함수
def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "update_todos", "update_instructions", "update_profile", "handle_mcp_tools"]:
    message = state['messages'][-1]
    if len(message.tool_calls) == 0:
        return END
    else:
        for tool_call in message.tool_calls:
            if tool_call.get('name') in ['brave_search', 'search_web', 'neo4j_cypher', 'get_neo4j_schema'] or 'neo4j' in tool_call.get('name', '').lower():
                return "handle_mcp_tools"
                
        tool_call = message.tool_calls[0]
        if tool_call.get('name') == 'UpdateMemory' and 'update_type' in tool_call.get('args', {}):
            update_type = tool_call['args']['update_type']
            if update_type == "user":
                return "update_profile"
            elif update_type == "todo":
                return "update_todos"
            elif update_type == "instructions":
                return "update_instructions"
        
        return "handle_mcp_tools"

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=configuration)

# Define the nodes
builder.add_node("persona_assistant", enhanced_persona_assistant)
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