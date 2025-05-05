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




# Initialize the model
model = ChatOpenAI(model="gpt-4.1-nano", temperature=0)

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
            "neo4j-aura": {
                "command": "uvx",
                "args": ["mcp-neo4j-cypher@0.2.1"],
                "env": {
                    "NEO4J_URI": "bolt://localhost:7687",
                    "NEO4J_USERNAME": "neo4j",
                    "NEO4J_PASSWORD": "password123",
                    "NEO4J_DATABASE": "neo4j"
                },
                "transport": "stdio",
            },
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
            
            # 비동기적으로 대화 로그 저장
            await async_save_conversation_log(state, response, conversation_context)
            
            return {"messages": [response]}
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