import uuid
from datetime import datetime
from pydantic import BaseModel, Field
import json
import re

from typing import Literal, Optional, TypedDict, Any, Dict, List

from langchain_core.runnables import RunnableConfig
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.messages import merge_message_runs
from langchain_openai import ChatOpenAI

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.store.base import BaseStore
from langgraph.store.memory import InMemoryStore

from graphDB.neo4j import (
    Neo4jHybridSearch,
    save_conversation_log,
    async_save_conversation_log,
    async_check_schema
)

import agents.configuration as configuration

# Initialize the model
model = ChatOpenAI(model="gpt-4.1", temperature=0)

# 평가 관련 설정 클래스
class EvaluationConfiguration(BaseModel):
    """대화 평가 관련 설정"""
    user_id: str = Field(..., description="평가 대상 사용자 ID")
    company_id: str = Field(..., description="평가 대상 기업 ID")
    scenario_id: str = Field(..., description="평가 시나리오 ID")
    customer_objective: Optional[str] = Field(None, description="고객의 목표")
    company_objective: Optional[str] = Field(None, description="기업의 목표")
    
    @classmethod
    def from_runnable_config(cls, config: Dict[str, Any]) -> "EvaluationConfiguration":
        """RunnableConfig에서 EvaluationConfiguration 객체 생성"""
        config_dict = config.get("configurable", {})
        return cls(**config_dict)

# 대화 전처리 함수
def preprocess_conversation(conversation_history):
    """
    대화 내용을 전처리하여 분석에 적합한 형태로 변환

    Args:
        conversation_history: 원본 대화 내용

    Returns:
        list: 전처리된 대화 내용
    """
    processed = []

    for idx, msg in enumerate(conversation_history):
        # 역할 정규화 (user -> customer, assistant -> company)
        if hasattr(msg, 'role'):
            role = "customer" if msg.role == "user" else "company"
        else:
            role = "customer" if isinstance(msg, HumanMessage) else "company"

        # 메시지 내용 정규화
        if hasattr(msg, 'content'):
            content = clean_text(msg.content)
        else:
            content = clean_text(msg.content if hasattr(msg, 'content') else str(msg))

        # 대화 턴 정보 추가
        turn_number = len(processed) // 2 + 1 if role == "customer" else len(processed) // 2

        processed.append({
            "role": role,
            "content": content,
            "turn": turn_number
        })

    return processed

# 텍스트 정리 함수
def clean_text(text):
    """텍스트에서 불필요한 마크업이나 특수문자 등을 제거"""
    if not text:
        return ""
    
    # HTML 태그 제거
    text = re.sub(r'<[^>]+>', '', text)
    
    # 연속된 공백 제거
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()

# 대화 맥락 분석
def analyze_conversation_context(processed_conversation, customer_objective, company_objective, scenario_context):
    """
    대화 내용의 맥락을 분석하여 주요 특성 추출

    Args:
        processed_conversation: 전처리된 대화 내용
        customer_objective: 고객의 목표
        company_objective: 기업의 목표
        scenario_context: 시나리오 컨텍스트 정보

    Returns:
        dict: 대화 맥락 분석 결과
    """
    # 대화 길이 및 턴 수 분석
    customer_messages = [msg for msg in processed_conversation if msg["role"] == "customer"]
    company_messages = [msg for msg in processed_conversation if msg["role"] == "company"]
    
    total_turns = max([msg["turn"] for msg in processed_conversation if msg["role"] == "customer"]) if customer_messages else 0

    # 고객 요구사항 추출
    customer_demands = extract_customer_demands(processed_conversation)

    # 기업 제안사항 추출
    company_offers = extract_company_offers(processed_conversation)

    # 감정 분석
    emotion_analysis = analyze_emotions(processed_conversation)

    # 주요 논쟁점 식별
    key_points = identify_key_points(processed_conversation)

    # 합의점 도출
    agreement_points = identify_agreements(processed_conversation)

    # 목표 달성 여부 예비 평가
    preliminary_assessment = assess_goal_achievement(
        processed_conversation,
        customer_objective,
        company_objective,
        customer_demands,
        company_offers
    )

    return {
        "total_turns": total_turns,
        "customer_demands": customer_demands,
        "company_offers": company_offers,
        "emotion_analysis": emotion_analysis,
        "key_points": key_points,
        "agreement_points": agreement_points,
        "preliminary_assessment": preliminary_assessment
    }

# 고객 요구사항 추출
def extract_customer_demands(processed_conversation):
    """고객 메시지에서 주요 요구사항 추출"""
    # 실제 구현에서는 LLM을 통한 요구사항 추출 로직 구현
    # 간단한 예시로 고객 메시지에서 키워드 기반 추출
    customer_messages = [msg["content"] for msg in processed_conversation if msg["role"] == "customer"]
    customer_text = " ".join(customer_messages)
    
    # 여기서는 간단히 처리하지만, 실제로는 LLM을 활용해 요구사항 추출
    return ["고객의 주요 요구사항 추출 필요"]

# 기업 제안사항 추출
def extract_company_offers(processed_conversation):
    """기업 메시지에서 주요 제안사항 추출"""
    # 실제 구현에서는 LLM을 통한 제안사항 추출 로직 구현
    company_messages = [msg["content"] for msg in processed_conversation if msg["role"] == "company"]
    company_text = " ".join(company_messages)
    
    # 여기서는 간단히 처리하지만, 실제로는 LLM을 활용해 제안사항 추출
    return ["기업의 주요 제안사항 추출 필요"]

# 감정 분석
def analyze_emotions(processed_conversation):
    """대화 내용의 감정 분석"""
    # 실제 구현에서는 LLM 또는 감정 분석 모델을 활용할 수 있음
    emotions = {
        "customer": {
            "dominant_emotion": "확인 필요",
            "emotion_progression": ["확인 필요"],
            "intensity": "중간"
        },
        "company": {
            "dominant_emotion": "확인 필요",
            "emotion_progression": ["확인 필요"],
            "intensity": "중간"
        }
    }
    return emotions

# 주요 논쟁점 식별
def identify_key_points(processed_conversation):
    """대화에서 주요 논쟁점 식별"""
    # 실제 구현에서는 LLM을 활용하여 논쟁점 추출
    return ["주요 논쟁점 확인 필요"]

# 합의점 도출
def identify_agreements(processed_conversation):
    """대화에서 합의된 사항 식별"""
    # 실제 구현에서는 LLM을 활용하여 합의점 추출
    return ["합의점 확인 필요"]

# 목표 달성 여부 예비 평가
def assess_goal_achievement(processed_conversation, customer_objective, company_objective, customer_demands, company_offers):
    """목표 달성 여부에 대한 예비 평가"""
    # 실제 구현에서는 LLM을 통한 목표 달성 평가
    assessment = {
        "customer": {
            "goal_achievement": "평가 필요",
            "confidence": "중간"
        },
        "company": {
            "goal_achievement": "평가 필요",
            "confidence": "중간"
        }
    }
    return assessment

# 평가 프롬프트 구성
def construct_evaluation_prompt(processed_conversation, context_analysis, customer_objective, company_objective):
    """
    LLM 기반 평가를 위한 프롬프트 구성

    Args:
        processed_conversation: 전처리된 대화 내용
        context_analysis: 대화 맥락 분석 결과
        customer_objective: 고객의 목표
        company_objective: 기업의 목표

    Returns:
        dict: LLM 평가를 위한 프롬프트
    """
    # 대화 내용 형식화
    formatted_conversation = format_conversation_for_prompt(processed_conversation)

    # 평가 지침 구성
    evaluation_guidelines = construct_evaluation_guidelines()

    # 맥락 정보 요약
    context_summary = summarize_context(context_analysis)

    # 최종 프롬프트 구성
    prompt = f"""
    다음 대화를 평가하고, 고객과 기업 각각의 점수를 산정해주세요.

    ### 고객 목표
    {customer_objective}

    ### 기업 목표
    {company_objective}

    ### 대화 맥락 요약
    {context_summary}

    ### 대화 내용
    {formatted_conversation}

    ### 평가 지침
    {evaluation_guidelines}

    각 평가 지표별로 0-100점 사이의 점수를 부여하고, 구체적인 근거를 제시해주세요.
    최종 결과는 다음 JSON 형식으로 제공해주세요.

    ```json
    {{
      "customer_scores": {{
        "tactical_effectiveness": 85,
        "logical_reasoning": 70,
        "emotional_appeal": 90,
        "crisis_response": 75,
        "negotiation_skills": 80,
        "total": 400
      }},
      "company_scores": {{
        "customer_retention": 65,
        "cost_minimization": 85,
        "policy_compliance": 90,
        "empathy_expression": 60,
        "solution_proposal": 75,
        "total": 375
      }},
      "winner": "customer",
      "margin": 25,
      "explanation": "평가 설명...",
      "key_moments": [
        {{
          "turn": 3,
          "description": "중요 순간에 대한 설명",
          "impact": "높음",
          "score_change": "+15 전술 효과성"
        }}
      ],
      "improvement_suggestions": {{
        "customer": "고객 개선점 제안",
        "company": "기업 개선점 제안"
      }}
    }}
    ```
    """

    return prompt

# 대화 내용 프롬프트 형식화
def format_conversation_for_prompt(processed_conversation):
    """대화 내용을 프롬프트용으로 형식화"""
    formatted = ""
    for msg in processed_conversation:
        role_display = "고객" if msg["role"] == "customer" else "기업"
        formatted += f"[턴 {msg['turn']}] {role_display}: {msg['content']}\n\n"
    return formatted

# 평가 지침 구성
def construct_evaluation_guidelines():
    """평가 지침 구성"""
    return """
    ## 고객 평가 지표
    1. **전술적 효과성 (0-100점)**
       - 0점: 초기 목표 달성에 완전히 실패
       - 50점: 초기 목표의 일부만 달성
       - 100점: 초기 목표를 완전히 달성하고 추가 이득까지 얻음

    2. **논리적 추론 (0-100점)**
       - 0점: 일관성 없고 논리적 오류가 많음
       - 50점: 기본적인 논리는 있으나 일부 허점 존재
       - 100점: 완벽하게 논리적이고 일관된 주장

    3. **감정적 호소 (0-100점)**
       - 0점: 감정 활용에 실패하거나 부적절한 감정 표현
       - 50점: 일부 상황에서 효과적인 감정 활용
       - 100점: 상대방의 감정을 효과적으로 이끌어내고 활용

    4. **위기 대응 (0-100점)**
       - 0점: 어려운 순간에 무너짐
       - 50점: 위기 상황에서 기본적인 대응은 가능
       - 100점: 위기를 기회로 전환하는 탁월한 대응

    5. **협상 기술 (0-100점)**
       - 0점: 협상 전략 부재
       - 50점: 기본적인 협상 기술 사용
       - 100점: 다양한 협상 전략을 상황에 맞게 탁월하게 활용

    ## 기업 평가 지표
    1. **고객 유지 (0-100점)**
       - 0점: 고객 관계 완전 손상
       - 50점: 고객 관계 유지는 했으나 손상됨
       - 100점: 고객 충성도 강화 및 관계 개선

    2. **비용 최소화 (0-100점)**
       - 0점: 불필요한 양보로 많은 비용 발생
       - 50점: 적절한 수준의 비용 관리
       - 100점: 최소한의 비용으로 최대 효과 달성

    3. **정책 준수 (0-100점)**
       - 0점: 회사 정책 위반
       - 50점: 기본적인 정책 준수
       - 100점: 정책 내에서 최대한의 유연성 발휘

    4. **공감 표현 (0-100점)**
       - 0점: 고객 감정에 무관심
       - 50점: 기본적인 공감 표현
       - 100점: 탁월한 공감 능력으로 고객 신뢰 획득

    5. **해결책 제안 (0-100점)**
       - 0점: 문제 해결책 제시 실패
       - 50점: 기본적인 해결책 제시
       - 100점: 창의적이고 효과적인 맞춤형 해결책 제안
    """

# 맥락 정보 요약
def summarize_context(context_analysis):
    """맥락 분석 정보 요약"""
    summary = f"""
    - 총 대화 턴수: {context_analysis['total_turns']}
    - 고객 주요 요구사항: {', '.join(context_analysis['customer_demands'])}
    - 기업 주요 제안사항: {', '.join(context_analysis['company_offers'])}
    - 주요 논쟁점: {', '.join(context_analysis['key_points'])}
    - 합의된 사항: {', '.join(context_analysis['agreement_points'])}
    """
    return summary

# LLM 기반 평가 실행
async def run_llm_evaluation(prompt):
    """LLM을 활용한 평가 실행"""
    try:
        response = await model.ainvoke([SystemMessage(content="당신은 고객과 기업 간의 대화를 객관적으로 평가하는 전문가입니다."), 
                                       HumanMessage(content=prompt)])
        return response.content
    except Exception as e:
        print(f"LLM 평가 과정에서 오류 발생: {str(e)}")
        return "평가 오류 발생"

# 평가 결과 후처리
def postprocess_evaluation(evaluation_result):
    """평가 결과 구조화"""
    try:
        # JSON 형식으로 결과 추출
        json_match = re.search(r'```json\s*(.*?)\s*```', evaluation_result, re.DOTALL)
        if json_match:
            json_str = json_match.group(1)
            result = json.loads(json_str)
        else:
            # JSON 블록이 명시적으로 표시되지 않은 경우 직접 파싱 시도
            json_str = re.search(r'({.*})', evaluation_result, re.DOTALL)
            if json_str:
                result = json.loads(json_str.group(1))
            else:
                raise ValueError("평가 결과에서 JSON 형식을 찾을 수 없습니다.")
        
        return result
    except Exception as e:
        print(f"평가 결과 처리 과정에서 오류 발생: {str(e)}")
        # 오류 발생 시 기본 형식 반환
        return {
            "customer_scores": {"total": 0},
            "company_scores": {"total": 0},
            "winner": "평가 실패",
            "explanation": f"평가 결과 처리 중 오류: {str(e)}",
            "key_moments": [],
            "improvement_suggestions": {"customer": "", "company": ""}
        }

# 대화 평가 노드 함수
async def evaluate_conversation_node(state: MessagesState, config: RunnableConfig, store: BaseStore):
    """대화 내용을 평가하는 노드 함수"""
    print(f"Starting conversation evaluation...{config}")
    
    # 설정에서 평가 정보 가져오기
    configurable = EvaluationConfiguration.from_runnable_config(config)
    user_id = configurable.user_id
    company_id = configurable.company_id
    scenario_id = configurable.scenario_id
    customer_objective = configurable.customer_objective
    company_objective = configurable.company_objective
    
    try:
        # 대화 내용 가져오기
        conversation_history = state["messages"]
        
        # 대화 전처리
        processed_conversation = preprocess_conversation(conversation_history)
        
        # 시나리오 컨텍스트 정보 가져오기 (실제 구현에서는 데이터베이스에서 가져옴)
        scenario_context = {"scenario_id": scenario_id, "description": "시나리오 설명"}
        
        # 대화 맥락 분석
        context_analysis = analyze_conversation_context(
            processed_conversation, 
            customer_objective, 
            company_objective, 
            scenario_context
        )
        
        # 평가 프롬프트 구성
        prompt = construct_evaluation_prompt(
            processed_conversation,
            context_analysis,
            customer_objective,
            company_objective
        )
        
        # LLM 기반 평가 실행
        evaluation_result = await run_llm_evaluation(prompt)
        
        # 평가 결과 구조화
        final_result = postprocess_evaluation(evaluation_result)
        
        # 평가 결과를 AIMessage로 변환
        result_message = f"""
        # 대화 평가 결과

        ## 점수 요약
        - 고객 총점: {final_result['customer_scores']['total']}/500
        - 기업 총점: {final_result['company_scores']['total']}/500
        - 승자: {final_result['winner']} (점수차: {final_result.get('margin', '정보 없음')})

        ## 상세 분석
        {final_result['explanation']}

        ## 주요 순간
        {format_key_moments(final_result.get('key_moments', []))}

        ## 개선 제안
        - 고객: {final_result.get('improvement_suggestions', {}).get('customer', '정보 없음')}
        - 기업: {final_result.get('improvement_suggestions', {}).get('company', '정보 없음')}
        """
        
        # 평가 결과 저장 (실제 구현에서는 데이터베이스에 저장)
        evaluation_id = str(uuid.uuid4())
        namespace = ("evaluation", user_id, company_id)
        store.put(namespace, evaluation_id, final_result)
        
        return {"messages": [AIMessage(content=result_message)]}
    
    except Exception as e:
        error_message = f"대화 평가 중 오류 발생: {str(e)}"
        print(error_message)
        return {"messages": [AIMessage(content=error_message)]}

# 주요 순간 형식화
def format_key_moments(key_moments):
    if not key_moments:
        return "주요 순간 정보 없음"
    
    formatted = ""
    for moment in key_moments:
        formatted += f"- 턴 {moment.get('turn', '?')}: {moment.get('description', '설명 없음')} (영향: {moment.get('impact', '정보 없음')}, 점수 변화: {moment.get('score_change', '정보 없음')})\n"
    
    return formatted

# 그래프 구성
builder = StateGraph(MessagesState, config_schema=EvaluationConfiguration)

# 노드 정의
builder.add_node("evaluate_conversation", evaluate_conversation_node)

# 흐름 정의
builder.add_edge(START, "evaluate_conversation")
builder.add_edge("evaluate_conversation", END)

# 그래프 컴파일
graph = builder.compile()