"""
message_generator.py
LLM 기반 동적 메시지 생성기 - 경량 모델(google/gemma-3-27b-it) 활용
"""

import logging
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수"""
    log_message = f"[{step_name}] {status}: {message}"
    if status == "ERROR":
        logger.error(log_message)
    elif status == "WARNING":
        logger.warning(log_message)
    else:
        logger.info(log_message)


# LLMManager 대체 - 없으면 mock 사용
try:
    from chat_openai.llm_manager import LLMManager
except ImportError:
    LLMManager = None

class MessageGenerator:
    """경량 LLM을 사용한 사용자 친화적 메시지 생성"""
    
    # action → 사용자 친화적 메시지 매핑
    ACTION_MESSAGES = {
        "intent_classification_start": "질문을 분석하고 있습니다...",
        "intent_classification_complete": "질문 분석이 완료되었습니다.",
        "agent_selection_start": "분석에 필요한 에이전트를 선택하고 있습니다...",
        "agent_selection_complete": "분석 에이전트가 선택되었습니다.",
        "data_collection": "데이터를 수집하고 있습니다...",
        "financial_analysis": "재무 데이터를 분석하고 있습니다...",
        "governance_analysis": "지배구조를 분석하고 있습니다...",
        "document_analysis": "공시 문서를 분석하고 있습니다...",
        "result_integration": "분석 결과를 통합하고 있습니다...",
        "simple_greeting": "인사에 응답하고 있습니다...",
        "single_agent_analysis": "전문 에이전트가 분석을 진행하고 있습니다...",
        "multi_agent_analysis": "여러 에이전트가 협력하여 분석하고 있습니다...",
    }
    
    def __init__(self):
        # 경량 모델 사용 (google/gemma-3-27b-it, max_tokens=4096)
        self.llm = LLMManager.get_llm(purpose="complex_analysis") if LLMManager else None
        if self.llm:
            log_step("MessageGenerator", "SUCCESS", "경량 LLM 초기화 완료 (google/gemma-3-27b-it)")
        else:
            log_step("MessageGenerator", "WARNING", "LLM 없음, 정적 메시지 사용")
    
    async def generate_progress_message(
        self, 
        action: str,
        context: Dict[str, Any]
    ) -> str:
        """진행 상황 메시지 생성
        
        Args:
            action: 수행 중인 작업 (예: "simple_greeting", "single_agent_analysis", "data_collection")
            context: 컨텍스트 정보 (user_question, corp_name, agents, etc.)
        """
        from langchain_core.messages import HumanMessage
        
        # 컨텍스트 정보 추출
        user_question = context.get("user_question", "")
        corp_name = context.get("corp_name", "")
        agents = context.get("agents", [])
        
        prompt = f"""사용자에게 현재 진행 상황을 자연스럽게 알려주는 짧은 메시지를 한국어로 작성해주세요.

상황: {action}
사용자 질문: "{user_question}"
기업명: {corp_name if corp_name else "미정"}
분석 에이전트: {', '.join(agents) if agents else "선택 중"}

요구사항:
1. 1-2문장으로 간결하게
2. 존댓말 사용
3. 이모지 사용 금지
4. 현재 무엇을 하고 있는지 명확하게
5. 사용자가 안심할 수 있도록

예시:
- "현대자동차의 재무 데이터를 수집하고 있습니다."
- "3개 기업의 분석 결과를 비교하고 있습니다."
- "공시 문서를 분석하여 필요한 정보를 찾고 있습니다."

메시지만 출력하세요 (설명 불필요):"""
        
        # LLM 없으면 정적 메시지 반환
        if not self.llm:
            return self.ACTION_MESSAGES.get(action, "분석을 진행하고 있습니다...")
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            message = response.content.strip() if response.content else None
            
            # LLM 응답이 action 이름을 그대로 포함하면 정적 메시지로 대체
            if message and (action in message or "_start" in message or "_complete" in message):
                message = self.ACTION_MESSAGES.get(action, "분석을 진행하고 있습니다...")
                log_step("MessageGenerator", "WARNING", f"LLM 응답에 기술적 용어 포함, 정적 메시지 사용: {message}")
            elif not message:
                message = self.ACTION_MESSAGES.get(action, "분석을 진행하고 있습니다...")
            else:
                log_step("MessageGenerator", "SUCCESS", f"진행 메시지 생성: {message}")
            
            return message
        except Exception as e:
            log_step("MessageGenerator", "ERROR", f"메시지 생성 실패: {e}")
            return self.ACTION_MESSAGES.get(action, "분석을 진행하고 있습니다...")
    
    async def generate_error_message(
        self,
        error_type: str,
        context: Dict[str, Any]
    ) -> str:
        """오류 메시지 생성"""
        from langchain_core.messages import HumanMessage
        
        error_context = context.get("error_context", "")
        user_question = context.get("user_question", "")
        
        prompt = f"""사용자에게 오류 상황을 자연스럽게 설명하는 메시지를 한국어로 작성해주세요.

오류 유형: {error_type}
오류 상황: {error_context}
사용자 질문: "{user_question}"

요구사항:
1. 2-3문장으로 설명
2. 존댓말 사용
3. 이모지 사용 금지
4. 무엇이 문제인지 명확하게
5. 가능하면 해결 방법 제시

예시:
- "요청하신 기업의 정보를 찾을 수 없습니다. 기업명을 다시 확인해주시겠어요?"
- "분석에 필요한 데이터를 가져오는 중 문제가 발생했습니다. 잠시 후 다시 시도해주세요."

메시지만 출력하세요 (설명 불필요):"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            message = response.content.strip() if response.content else "처리 중 오류가 발생했습니다."
            log_step("MessageGenerator", "SUCCESS", f"오류 메시지 생성: {message}")
            return message
        except Exception as e:
            log_step("MessageGenerator", "ERROR", f"오류 메시지 생성 실패: {e}")
            return "처리 중 오류가 발생했습니다. 다시 시도해주세요."
    
    async def generate_work_plan_message(
        self,
        user_question: str,
        analysis_plan: Dict[str, Any]
    ) -> str:
        """서브 에이전트가 수행할 작업 계획 메시지 생성"""
        from langchain_core.messages import HumanMessage
        
        agent_name = analysis_plan.get("agent_name", "")
        corp_name = analysis_plan.get("corp_name", "")
        intent_reasoning = analysis_plan.get("intent_reasoning", "")
        
        prompt = f"""사용자 질문을 분석하여 어떤 작업을 수행할지 계획을 자연스럽게 설명해주세요.

사용자 질문: "{user_question}"
분석 에이전트: {agent_name}
대상 기업: {corp_name}
분석 의도: {intent_reasoning}

요구사항:
1. 2-3문장으로 설명
2. 존댓말 사용
3. 이모지 사용 금지
4. 어떤 데이터를 수집하고 분석할지 명확하게
5. 사용자가 이해하기 쉽게

예시:
- "{corp_name}의 재무제표와 재무지표를 수집하여 재무 건전성을 분석하겠습니다."
- "최근 공시 문서를 검토하여 지배구조 변경 사항을 확인하겠습니다."

메시지만 출력하세요 (설명 불필요):"""
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            message = response.content.strip() if response.content else f"{corp_name}에 대한 분석을 시작합니다."
            log_step("MessageGenerator", "SUCCESS", f"작업 계획 메시지 생성: {message}")
            return message
        except Exception as e:
            log_step("MessageGenerator", "ERROR", f"작업 계획 메시지 생성 실패: {e}")
            return f"{corp_name}에 대한 분석을 시작합니다."
    
    async def generate_agent_introduction(
        self,
        question_type: str,
        context: Dict[str, Any]
    ) -> str:
        """에이전트 소개 메시지 생성
        
        Args:
            question_type: 질문 유형 ("greeting", "agent_intro")
            context: 컨텍스트 정보 (user_question 등)
        """
        from langchain_core.messages import HumanMessage
        
        user_question = context.get("user_question", "")
        
        # prompt_templates/base_prompt.py와 domain_specific.py 정보 활용
        agent_capabilities = '''DART 공시 데이터 분석 전문가로서 다음 영역을 분석할 수 있습니다:
- 재무 분석 (재무제표, 재무지표)
- 지배구조 분석 (주주구성, 임원현황)
- 자본변동 분석 (증자/감자, 자기주식)
- 부채자금조달 분석 (채권발행, 사채)
- 사업구조 분석 (M&A, 사업재편)
- 해외사업 분석 (해외진출, 글로벌 전략)
- 법적리스크 분석 (소송, 규제 준수)
- 경영진감사 분석 (임원보수, 감사)
- 문서분석 (공시문서 심층 분석)'''
        
        if question_type == "greeting":
            prompt = f'''사용자의 인사에 자연스럽게 응답하고 간단히 자기소개를 해주세요.

사용자 인사: "{user_question}"

요구사항:
1. 1-2문장으로 간결하게
2. 존댓말 사용
3. 이모지 사용 금지
4. "기업 공시 분석 전문가" 소개
5. "무엇을 도와드릴까요?" 마무리

예시:
- "안녕하세요. 저는 기업 공시 데이터 분석 전문가입니다. 무엇을 도와드릴까요?"
- "반갑습니다. DART 공시 데이터 분석을 전문으로 하고 있습니다. 궁금하신 기업 정보가 있으신가요?"

메시지만 출력하세요:'''
        
        else:  # agent_intro
            prompt = f'''사용자가 에이전트의 역할과 기능에 대해 물어보고 있습니다. 간결하게 자기소개를 해주세요.

사용자 질문: "{user_question}"

에이전트 기능:
{agent_capabilities}

요구사항:
1. 2-3문장으로 간결하게
2. 존댓말 사용
3. 이모지 사용 금지
4. 핵심 역할만 언급 (8가지 영역 나열하지 말 것)
5. "무엇을 도와드릴까요?" 마무리

예시:
- "저는 기업 공시 데이터 분석 전문가입니다. DART에 공시된 재무정보, 지배구조, 사업구조 등 다양한 기업 정보를 분석해드립니다. 궁금하신 기업이 있으신가요?"
- "한국 기업들의 공시 데이터를 분석하는 전문가입니다. 재무제표부터 지배구조, 법적 리스크까지 폭넓은 분석이 가능합니다. 무엇을 도와드릴까요?"

메시지만 출력하세요:'''
        
        try:
            response = await self.llm.ainvoke([HumanMessage(content=prompt)])
            message = response.content.strip() if response.content else "기업 공시 분석 전문가입니다. 무엇을 도와드릴까요?"
            log_step("MessageGenerator", "SUCCESS", f"에이전트 소개 메시지 생성: {message}")
            return message
        except Exception as e:
            log_step("MessageGenerator", "ERROR", f"소개 메시지 생성 실패: {e}")
            return "기업 공시 분석 전문가입니다. 무엇을 도와드릴까요?"
