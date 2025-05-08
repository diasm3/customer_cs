# 대화 평가 알고리즘

## 개요

대화 평가 알고리즘은 고객과 기업 간의 대화를 분석하여 양측의 성과를 객관적으로 평가하는 시스템입니다. LLM을 활용한 자연어 이해와 맥락 분석을 통해 다차원적 평가를 수행합니다.

## 알고리즘 구조

```python
def evaluate_conversation(conversation_history, customer_objective, company_objective, scenario_context):
    """
    대화 내용을 분석하여 고객과 기업 양측의 성과를 평가

    Args:
        conversation_history: 대화 내용 목록 (각 항목은 role, content로 구성)
        customer_objective: 고객의 목표
        company_objective: 기업의 목표
        scenario_context: 시나리오 컨텍스트 정보

    Returns:
        dict: 평가 결과 (각 평가 지표별 점수 및 총점, 승자, 상세 설명 포함)
    """
    # 1. 대화 전처리
    processed_conversation = preprocess_conversation(conversation_history)

    # 2. 대화 맥락 분석
    context_analysis = analyze_conversation_context(processed_conversation, customer_objective, company_objective, scenario_context)

    # 3. 평가 프롬프트 구성
    prompt = construct_evaluation_prompt(processed_conversation, context_analysis, customer_objective, company_objective)

    # 4. LLM 기반 평가 실행
    evaluation_result = run_llm_evaluation(prompt)

    # 5. 후처리 및 결과 구조화
    final_result = postprocess_evaluation(evaluation_result)

    return final_result
```

## 주요 컴포넌트 설명

### 1. 대화 전처리 (preprocess_conversation)

```python
def preprocess_conversation(conversation_history):
    """
    대화 내용을 전처리하여 분석에 적합한 형태로 변환

    Args:
        conversation_history: 원본 대화 내용

    Returns:
        list: 전처리된 대화 내용
    """
    processed = []

    for msg in conversation_history:
        # 역할 정규화 (user -> customer, assistant -> company)
        role = "customer" if msg["role"] == "user" else "company"

        # 메시지 내용 정규화 (필요시 HTML 태그 제거, 특수문자 처리 등)
        content = clean_text(msg["content"])

        # 대화 턴 정보 추가
        turn_number = len(processed) // 2 + 1 if role == "customer" else len(processed) // 2

        processed.append({
            "role": role,
            "content": content,
            "turn": turn_number
        })

    return processed
```

### 2. 대화 맥락 분석 (analyze_conversation_context)

```python
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
    total_turns = max([msg["turn"] for msg in processed_conversation if msg["role"] == "customer"])

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
```

### 3. 평가 프롬프트 구성 (construct_evaluation_prompt)

```python
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
    prompt = {
        'role': 'user',
        'content': f"""
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
        최종 결과는 JSON 형식으로 제공해주세요.
        """
    }

    return prompt
```

### 4. 평가 지표별 점수 산출 함수

```python
def calculate_tactical_effectiveness(conversation, customer_demands, company_offers, agreement_points):
    """
    고객의 전술적 효과성 평가

    Args:
        conversation: 대화 내용
        customer_demands: 고객 요구사항
        company_offers: 기업 제안사항
        agreement_points: 합의된 내용

    Returns:
        int: 전술적 효과성 점수 (0-100)
    """
    # 1. 초기 요구사항 대비 최종 합의 내용 분석
    demands_met = analyze_demands_met(customer_demands, agreement_points)

    # 2. 협상 과정에서의 양보 수준 분석
    concession_level = analyze_concessions(customer_demands, agreement_points)

    # 3. 추가 이득 획득 여부 분석
    additional_gains = analyze_additional_gains(customer_demands, agreement_points)

    # 4. 승패 결정에 미치는 영향력 분석
    influence_on_outcome = analyze_outcome_influence(conversation)

    # 5. 전략 실행 효율성 분석
    strategy_efficiency = analyze_strategy_efficiency(conversation)

    # 6. 가중치 적용 및 종합 점수 계산
    weighted_score = (
        demands_met * 0.35 +
        (100 - concession_level) * 0.2 +
        additional_gains * 0.15 +
        influence_on_outcome * 0.15 +
        strategy_efficiency * 0.15
    )

    return min(100, max(0, round(weighted_score)))
```

## 평가 결과 형식

```json
{
  "customer_scores": {
    "tactical_effectiveness": 85,
    "logical_reasoning": 70,
    "emotional_appeal": 90,
    "crisis_response": 75,
    "negotiation_skills": 80,
    "total": 400
  },
  "company_scores": {
    "customer_retention": 65,
    "cost_minimization": 85,
    "policy_compliance": 90,
    "empathy_expression": 60,
    "solution_proposal": 75,
    "total": 375
  },
  "winner": "customer",
  "margin": 25,
  "explanation": "고객은 감정적 호소와 논리적 접근을 적절히 활용하여 초기 목표를 대부분 달성했습니다. 특히 감정적 호소와 위기 상황에서의 대응이 매우 효과적이었습니다. 기업은 정책 준수와 비용 최소화에서 높은 점수를 얻었지만, 공감 표현이 부족하여 고객 관계 유지에 어려움을 겪었습니다.",
  "key_moments": [
    {
      "turn": 3,
      "description": "고객이 법적 조치 언급으로 강력한 압박 시도",
      "impact": "높음",
      "score_change": "+15 전술 효과성"
    },
    {
      "turn": 4,
      "description": "기업이 부분적 보상 제안으로 협상 시작",
      "impact": "중간",
      "score_change": "+10 비용 최소화"
    }
  ],
  "improvement_suggestions": {
    "customer": "논리적 일관성을 더 강화하고, 명확한 증거를 제시하면 더 효과적일 것입니다.",
    "company": "고객의 감정에 더 공감하는 표현을 사용하고, 선제적 해결책 제안에 중점을 두면 좋겠습니다."
  }
}
```

## LLM 활용 전략

### 1. 프롬프트 엔지니어링 최적화

LLM을 활용한 정량 평가의 정확성을 높이기 위해 다음과 같은 프롬프트 전략을 활용합니다:

1. **구조화된 평가 기준 제시**

   - 각 평가 지표별 명확한 기준점 제시 (0점, 50점, 100점 상태 묘사)
   - 평가 근거를 반드시 포함하도록 지시

2. **객관성 강화 지시**

   - 평가 시 개인적 편향 배제 지시
   - 대화 내용 자체에 집중하고 가정 배제 요청

3. **단계적 평가 유도**

   - 각 평가 지표별 단계적 분석 후 종합 평가 유도
   - 증빙 사례를 대화에서 추출하여 인용 요청

4. **다양한 관점 고려**

   - 양측의 상황과 제약 사항 고려 지시
   - 맥락적 요소 (시나리오 특성, 산업 표준 등) 감안 지시

5. **일관성 검증 메커니즘**
   - 각 평가 지표 간 일관성 검토 요청
   - 최종 결론과 개별 평가 지표 간 정합성 확인 지시

### 2. 인간-AI 협력 평가 시스템

완전 자동화된 평가와 함께, 필요에 따라 인간 전문가의 검토를 병행하는 하이브리드 평가 시스템도 구현 가능합니다:

1. **LLM 기반 1차 평가**

   - 모든 대화에 대한 기본 평가 자동 수행
   - 정량적 점수 및 초기 분석 제공

2. **불확실성 표시**

   - 평가 신뢰도가 낮은 항목 표시
   - 추가 검토가 필요한 영역 식별

3. **인간 전문가 검토**

   - 복잡하거나 미묘한 사례에 대한 전문가 검토
   - 평가 지침 개선을 위한 피드백 수집

4. **지속적 학습 및 개선**
   - 전문가 피드백을 통한 평가 알고리즘 개선
   - 새로운 패턴 및 전략 식별을 위한 데이터 축적

## 기술적 구현 고려사항

1. **모델 선택**

   - 대화 평가에 최적화된 LLM 선택 (SOLAR-10.7B-Instruct-v1.0 또는 더 최신 모델)
   - 충분한 컨텍스트 윈도우 확보 (최소 8K 토큰 이상)

2. **성능 최적화**

   - 병렬 처리를 통한 대량 대화 평가 가속화
   - 캐싱 메커니즘을 통한 중복 계산 최소화

3. **확장성 고려**

   - 다양한 시나리오 및 산업군 맞춤형 평가 지표 확장 가능성
   - 다국어 지원을 위한 구조 설계

4. **보안 및 개인정보 보호**
   - 평가 과정에서 개인식별정보 익명화
   - 데이터 보관 정책 준수
