import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from trustcall import create_extractor

from typing import Literal, Optional, TypedDict, Any, Dict

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import merge_message_runs
from langchain_core.messages import SystemMessage, HumanMessage

from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

# MCP Client import
from langchain_mcp_adapters.client import MultiServerMCPClient

# 기업 페르소나 모듈 임포트
from personas.company_personas import (
    get_persona_by_id, 
    get_persona_prompt, 
    list_available_personas,
    get_scenarios_by_company,
    get_scenario
)

from neo4j.neo4j import  (
    Neo4jHybridSearch,
    save_conversation_log
)

import configuration




# 업데이트된 Configuration 클래스 정의
class PersonaConfiguration(configuration.Configuration):
    company_id: str = "skt"
    scenario_id: str = "usim_protection" 
    print(f"Initializing PersonaConfiguration with company_id: {company_id} and scenario_id: {scenario_id}")
    
    def get_persona_prompt(self) -> str:
        """회사 ID에 해당하는 페르소나 프롬프트를 반환합니다."""
        print(f"Fetching persona for company ID: {self.company_id}")
        return get_persona_prompt(self.company_id)
    
    def get_scenario_info(self) -> Optional[Dict]:
        """현재 시나리오 정보를 반환합니다."""
        print(f"Fetching persona for scenario ID: {self.scenario_id}")
        if not self.scenario_id:
            return None
        return get_scenario(self.company_id, self.scenario_id)

# Initialize the model
model = ChatOpenAI(model="gpt-4o", temperature=0)

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
            }
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
        
        # Use ToolNode to handle the tool calls
        tool_node = ToolNode(tools)
        
        # Process the state with tool node
        result = await tool_node.ainvoke(state)
        print(f"MCP tool result: {result}")
        
        return result
    except Exception as e:
        print(f"Error in handle_mcp_tools: {str(e)}")
        # Return a fallback response if MCP tool fails
        return {"messages": [{"role": "tool", "content": f"검색 실패: {str(e)}", "tool_call_id": state['messages'][-1].tool_calls[0]['id']}]}
    finally:
        await client.__aexit__(None, None, None)

# 페르소나 기반 응답 생성 함수
async def persona_assistant(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """페르소나 기반 응답을 생성하는 노드 함수"""
    
    # 설정에서 페르소나 정보 가져오기
    configurable = PersonaConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    todo_category = configurable.todo_category
    company_id = configurable.company_id
    scenario_id = configurable.scenario_id

    
     # Neo4j 하이브리드 검색 초기화
    neo4j_search = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )
    
    # 대화 컨텍스트 생성
    conversation_context = {
        'company_id': company_id,
        'scenario_id': scenario_id,
        'conversation_history': state["messages"][-5:] if len(state["messages"]) > 5 else state["messages"]
    }
    
    # 사용자 메시지에서 쿼리 추출
    last_message = state["messages"][-1]
    if isinstance(last_message, HumanMessage):
        query = last_message.content
        
        # 하이브리드 검색 실행
        search_results = neo4j_search.hybrid_search(query, conversation_context)
        
        # 검색 결과를 컨텍스트에 추가
        search_context = "\n\n관련 정보:\n"
        for result in search_results:
            search_context += f"- {result['content']}\n"
    else:
        search_context = ""
    
    # 페르소나 프롬프트 가져오기
    persona_prompt = configurable.get_persona_prompt()
    scenario_info = configurable.get_scenario_info()
    
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

당신의 역할은 위의 기업 페르소나에 맞게 고객 응대를 하는 것입니다.{scenario_context}

고객 정보: 
{user_profile}

메모:
{todo}

추가 지침:
{instructions}

당신은 또한 웹 검색 도구를 사용할 수 있습니다. 고객이 최신 정보나 사실 확인이 필요한 질문을 할 경우, 검색 도구를 사용하세요.
검색 결과는 기업의 톤앤매너와 원칙에 맞게 전달하세요.
"""
        
        # Respond using memory, chat history, and MCP tools - use ainvoke instead of invoke
        response = await model.bind_tools(all_tools, parallel_tool_calls=True).ainvoke(
            [SystemMessage(content=system_msg)] + state["messages"]
        )

        await save_conversation_log(state, response, conversation_context)

        
        return {"messages": [response]}
    finally:
        await client.__aexit__(None, None, None)

# Update memory tool
class UpdateMemory(TypedDict):
    """ Decision on what memory type to update """
    update_type: Literal['user', 'todo', 'instructions']

# 기존의 기능들은 동일하게 유지
def update_todos(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # ...existing code...
    return {"messages": [{"role": "tool", "content": "updated todos", "tool_call_id": state['messages'][-1].tool_calls[0]['id']}]}

def update_profile(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # ...existing code...
    return {"messages": [{"role": "tool", "content": "updated profile", "tool_call_id": state['messages'][-1].tool_calls[0]['id']}]}

def update_instructions(state: MessagesState, config: RunnableConfig, store: BaseStore):
    # ...existing code...
    return {"messages": [{"role": "tool", "content": "updated instructions", "tool_call_id": state['messages'][-1].tool_calls[0]['id']}]}

# 라우팅 함수 업데이트
def route_message(state: MessagesState, config: RunnableConfig, store: BaseStore) -> Literal[END, "update_todos", "update_instructions", "update_profile", "handle_mcp_tools"]:
    """Reflect on the memories and chat history to decide whether to update the memory collection."""
    message = state['messages'][-1]
    if len(message.tool_calls) == 0:
        return END
    else:
        tool_call = message.tool_calls[0]
        
        # Check if this is a search tool call (MCP)
        if tool_call.get('name') in ['brave_search', 'search_web']:
            return "handle_mcp_tools"
            
        # Check if this is an UpdateMemory tool call
        if tool_call.get('name') == 'UpdateMemory' and 'update_type' in tool_call.get('args', {}):
            update_type = tool_call['args']['update_type']
            if update_type == "user":
                return "update_profile"
            elif update_type == "todo":
                return "update_todos"
            elif update_type == "instructions":
                return "update_instructions"
        
        # Default case if we can't determine the route
        return END

# 대화 로그 저장 함수
async def save_conversation_log(state: MessagesState, response: Any, context: Dict):
    """대화 로그를 Neo4j에 저장"""
    neo4j_search = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )
    
    query = """
    CREATE (cl:ConversationLog {
        id: $id,
        timestamp: $timestamp,
        company_id: $company_id,
        scenario_id: $scenario_id,
        user_message: $user_message,
        assistant_response: $assistant_response
    })
    
    WITH cl
    MATCH (s:Scenario {id: $scenario_id})
    CREATE (s)-[:HAS_CONVERSATION]->(cl)
    """
    
    last_user_message = state["messages"][-1].content if state["messages"] else ""
    
    neo4j_search.graph.query(query, {
        'id': str(uuid.uuid4()),
        'timestamp': datetime.now().isoformat(),
        'company_id': context['company_id'],
        'scenario_id': context['scenario_id'],
        'user_message': last_user_message,
        'assistant_response': response.content if hasattr(response, 'content') else str(response)
    })

# 초기화 스크립트
async def initialize_neo4j():
    """Neo4j 벡터 인덱스 초기화 및 데이터 임베딩"""
    neo4j_search = Neo4jHybridSearch(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password123"
    )
    
    # 벡터 인덱스 생성
    neo4j_search.setup_vector_index()
    
    # 기존 지식 베이스 임베딩
    neo4j_search.embed_knowledge_base()
    
    print("Neo4j initialization completed")

# Create the graph + all nodes
builder = StateGraph(MessagesState, config_schema=PersonaConfiguration)

# 설정 스키마 정의
# builder.set_config_schema(PersonaConfiguration)

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