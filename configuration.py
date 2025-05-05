import os
from dataclasses import dataclass, field, fields
from typing import Any, Optional, Dict

from langchain_core.runnables import RunnableConfig
from typing_extensions import Annotated
from dataclasses import dataclass

from personas.company_personas import (
    get_persona_by_id, 
    get_persona_prompt, 
    list_available_personas,
    get_scenarios_by_company,
    get_scenario
)


@dataclass(kw_only=True)
class PersonaConfiguration:
    """The configurable fields for the chatbot."""
    user_id: str = "default-user"
    todo_category: str = "general" 
    task_maistro_role: str = "You are a helpful task management assistant. You help you create, organize, and manage the user's ToDo list."
    company_id: str = "default"
    scenario_id: Optional[str] = None

    @classmethod
    def from_runnable_config(
        cls, config: Optional[RunnableConfig] = None
    ) -> "PersonaConfiguration":
        """Create a Configuration instance from a RunnableConfig."""
        configurable = (
            config["configurable"] if config and "configurable" in config else {}
        )
        values: dict[str, Any] = {
            f.name: os.environ.get(f.name.upper(), configurable.get(f.name))
            for f in fields(cls)
            if f.init
        }
        return cls(**{k: v for k, v in values.items() if v})

    def get_persona_prompt(self) -> str:
        """회사 ID에 해당하는 페르소나 프롬프트를 반환합니다."""
        # 실제 구현은 personas.company_personas 모듈에서 가져옵니다.
        # 이 함수는 선언만 해두고 실제 구현은 persona_agent.py에서 합니다.
        return f"회사 ID: {self.company_id}"
    
    def get_scenario_info(self) -> Optional[Dict]:
        """현재 시나리오 정보를 반환합니다."""
        # 실제 구현은 personas.company_personas 모듈에서 가져옵니다.
        # 이 함수는 선언만 해두고 실제 구현은 persona_agent.py에서 합니다.
        scenarios=get_scenario(self.company_id, self.scenario_id)
        return None if not self.scenario_id else {"id": self.scenario_id, "title": f"시나리오 {self.scenario_id}", "description": scenarios["description"], "initial_response": scenarios["initial_response"]}

# @dataclass(kw_only=True)
# class PersonaConfiguration(Configuration):
#     """기업 페르소나 기반 응답 생성을 위한 설정 클래스"""
#     company_id: str = "default"
#     scenario_id: Optional[str] = None
    