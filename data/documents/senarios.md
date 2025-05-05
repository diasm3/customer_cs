# 시나리오 구조체

```json
{
  "scenario_id": "unique_id_string",
  "industry": "산업군",
  "scenario_name": "시나리오 이름",
  "scenario_description": "시나리오 전체 설명",
  "difficulty_level": 3,
  "typical_situations": [
    {
      "situation_id": "situation_1",
      "situation_name": "상황 이름",
      "situation_description": "상황 설명",
      "initial_prompt": "대화 시작 프롬프트",
      "customer_objective": "고객 목표",
      "company_objective": "기업 목표",
      "success_conditions": {
        "customer": ["고객 성공 조건 1", "고객 성공 조건 2"],
        "company": ["기업 성공 조건 1", "기업 성공 조건 2"]
      },
      "failure_conditions": {
        "customer": ["고객 실패 조건 1", "고객 실패 조건 2"],
        "company": ["기업 실패 조건 1", "기업 실패 조건 2"]
      },
      "expected_conversation_flow": [
        {
          "stage": "opening",
          "description": "대화 시작 단계 설명",
          "expected_customer_moves": ["고객 예상 행동 1", "고객 예상 행동 2"],
          "expected_company_moves": ["기업 예상 행동 1", "기업 예상 행동 2"]
        }
      ],
      "edge_cases": [
        {
          "description": "엣지 케이스 설명",
          "trigger_condition": "트리거 조건",
          "handling_guidance": "대처 방안"
        }
      ],
      "real_world_examples": [
        {
          "example_title": "실제 사례 제목",
          "example_description": "실제 사례 설명",
          "outcome": "결과",
          "learning_points": ["학습 포인트 1", "학습 포인트 2"]
        }
      ]
    }
  ],
  "scenario_specific_rules": ["시나리오 특정 규칙 1", "시나리오 특정 규칙 2"],
  "customer_personas": [
    "compatible_customer_persona_id_1",
    "compatible_customer_persona_id_2"
  ],
  "company_personas": [
    "compatible_company_persona_id_1",
    "compatible_company_persona_id_2"
  ]
}
```

## 구조적 특징

- **주요 필드 설명**
  - `scenario_id`: 고유 식별자
  - `industry`: 해당 산업 분야
  - `scenario_name`: 시나리오 이름
  - `scenario_description`: 시나리오 전체 설명
  - `difficulty_level`: 난이도 (1-5)
  - `typical_situations`: 대표적인 상황 목록
    - `situation_id`: 상황 고유 ID
    - `situation_name`: 상황 이름
    - `situation_description`: 상황 설명
    - `initial_prompt`: 대화 시작 프롬프트
    - `customer_objective`: 고객 목표
    - `company_objective`: 기업 목표
    - `success_conditions`: 성공 조건
    - `failure_conditions`: 실패 조건
    - `expected_conversation_flow`: 예상 대화 흐름
    - `edge_cases`: 예외 상황 처리
    - `real_world_examples`: 실제 사례
  - `scenario_specific_rules`: 시나리오별 특수 규칙
  - `customer_personas`: 호환 가능한 고객 페르소나 ID 목록
  - `company_personas`: 호환 가능한 기업 페르소나 ID 목록

## 응용 방법

- 산업군별 특화 시나리오 개발
- 실제 사례 기반 학습 자료 구성
- 게이미피케이션 요소 통합
