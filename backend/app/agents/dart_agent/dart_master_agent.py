"""
dart_master_agent.py
DART 멀티에이전트 시스템의 마스터 조정자
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from langchain_core.tools import BaseTool
from langchain_core.messages import SystemMessage, HumanMessage

# Agent Portal imports
from .base import DartBaseAgent, LiteLLMAdapter
from .dart_types import (
    create_analysis_context,
    merge_agent_results,
    AgentResult,
    ToolExecutionResult,
    IntentClassificationResult,
    AnalysisContext,
    RiskLevel,
)
from .message_refiner import MessageRefiner
from .mcp_client import MCPTool, get_opendart_mcp_client
from .metrics import observe, record_counter

logger = logging.getLogger(__name__)

def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수 (agent-platform 호환)"""
    logger.info(f"[{step_name}] {status}: {message}")

def log_performance(operation: str, duration: float, details: str = ""):
    """성능 로깅 (agent-platform 호환)"""
    logger.info(f"[PERF] {operation}: {duration:.2f}ms {details}")

def log_agent_flow(agent_name: str, action: str, step: int, message: str):
    """에이전트 플로우 로깅 (agent-platform 호환)"""
    logger.info(f"[{agent_name}] Step {step} - {action}: {message}")

# Langfuse 데코레이터 (선택적)
# observe 데코레이터는 metrics.py에서 import


# =============================================================================
# 🎯 DART 마스터 에이전트 (Agent Portal 버전)
# =============================================================================


class DartMasterAgent(DartBaseAgent):
    """DART 멀티에이전트 시스템의 마스터 조정자 (Agent Portal 마이그레이션)"""
    
    def __init__(self, model: str = "qwen-235b"):
        """마스터 에이전트 초기화 (Agent Portal 구조)"""
        super().__init__(
            agent_name="DartMasterAgent",
            model=model,
            max_iterations=15  # 멀티에이전트 조정에 필요한 반복 횟수
        )
        
        # LLM 어댑터 (LiteLLM 기반)
        self.llm = LiteLLMAdapter(model)
        
        # 하위 에이전트들 저장소
        self.sub_agents: Dict[str, DartBaseAgent] = {}
        self.intent_classifier = None
        
        # 메시지 생성기 (정적 메시지 사용)
        self.message_generator = self._create_simple_message_generator()
        
        # 마스터 에이전트 설정
    
    def _create_simple_message_generator(self):
        """간단한 메시지 생성기"""
        class SimpleMessageGenerator:
            async def generate_agent_introduction(self, question_type: str, context: dict = None):
                return "안녕하세요! 저는 DART 공시 분석 전문 에이전트입니다. 기업의 재무제표, 지배구조, 자본변동 등 다양한 정보를 분석해드립니다."
            
            async def generate_progress_message(self, action: str, context: dict = None):
                actions = {
                    "single_agent_analysis": f"{context.get('corp_name', '기업')} 분석 진행 중...",
                    "multi_agent_analysis": f"{context.get('corp_name', '기업')}에 대해 다중 분석 진행 중...",
                    "additional_analysis": f"{context.get('corp_name', '기업')}에 대한 추가 분석 진행 중...",
                    "result_integration": "결과 통합 중...",
                }
                return actions.get(action, f"{action} 진행 중...")
            
            async def generate_error_message(self, error_type: str, context: dict = None):
                return f"오류가 발생했습니다: {error_type}"
        
        return SimpleMessageGenerator()
        self.master_config = {
            "max_coordination_time": 1800,  # 30분 - 복잡한 멀티 에이전트 조정 지원
            "max_sub_agents": 4,
            "result_merge_timeout": 600,  # 10분 - 결과 병합 시간
            "retry_failed_agents": True,
        }

        log_step("DartMasterAgent 초기화", "SUCCESS", "마스터 조정자 설정 완료")
    
    def register_sub_agent(self, agent_name: str, agent: DartBaseAgent):
        """하위 에이전트 등록"""
        self.sub_agents[agent_name] = agent
        log_step("하위 에이전트 등록", "INFO", f"{agent_name} 등록 완료")
    
    def register_intent_classifier(self, classifier):
        """의도 분류기 등록"""
        self.intent_classifier = classifier
        log_step("의도 분류기 등록", "SUCCESS", "IntentClassifierAgent 등록 완료")
    
    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """마스터 에이전트용 기본 도구 필터링"""
        # 기본 도구만 사용
        target_tools = {
            "get_corporation_code_by_name",
            "get_corporation_info",
            "get_disclosure_list",
        }
        filtered = [t for t in tools if t.name in target_tools]
        log_step("마스터 에이전트 도구 필터링", "SUCCESS", f"기본 도구 {len(filtered)}개")
        return filtered
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 DART 멀티에이전트 시스템의 마스터 조정자입니다.
사용자의 질문을 분석하고, 적절한 전문 에이전트를 선택하여 분석을 수행합니다."""

    @observe()
    async def _generate_start_response(self, user_question: str) -> str:
        """LLM을 사용하여 사용자 질문에 맞는 간단한 시작 응답 생성"""
        try:
            if hasattr(self, "llm") and self.llm:
                from langchain_core.messages import HumanMessage

                start_prompt = f"""사용자의 질문에 대해 간단하고 친근하게 응답해주세요.

사용자 질문: {user_question}

응답 지침:
1. 친근하고 도움이 되는 톤으로 작성
2. 1-2문장으로 간결하게
3. 이모지 사용 금지
4. 한국어로만 응답
5. 질문을 파악하지 말것!

주의할 점:
1. 절대 사용자의 질문을 추측하거나 당신의 지식으로 답변하지 말것!
2. 사용자의 질문에 대해서만 친근하게 응답하고, 그 외에는 절대 답변하지 말것!

예시:
- "삼성생명의 최근 공시를 분석해줘" → "삼성생명의 최근 공시를 찾아서 분석을 도와드리겠습니다."
- "삼성전자 재무상태를 알려줘" → "삼성전자의 재무상태를 조사해서 알려드리겠습니다."
- "LG화학과 SK이노베이션을 비교해줘" → "LG화학과 SK이노베이션을 비교 분석해드리겠습니다."

응답:"""

                response = await self.llm.ainvoke([HumanMessage(content=start_prompt)])
                return response.content if hasattr(response, "content") else str(response)
            else:
                # LLM이 없는 경우 기본 응답
                return f"'{user_question}'에 대한 분석을 시작하겠습니다."

        except Exception as e:
            log_step("시작 응답 생성 오류", "ERROR", f"오류: {str(e)}")
            return f"'{user_question}'에 대한 분석을 시작하겠습니다."

    async def _classify_question_type(self, user_question: str, thread_id: Optional[str] = None) -> str:
        """질문 유형을 분류 - greeting, agent_intro, analysis"""
        try:
            if hasattr(self, "llm") and self.llm:
                from langchain_core.messages import HumanMessage
                
                prompt = f"""다음 질문의 유형을 분류해주세요.

질문: "{user_question}"

유형:
- "greeting": 단순 인사말 (안녕, 하이, 반가워, 안녕하세요 등)
- "agent_intro": 에이전트 정체성/기능 질문 (뭐하는애야, 무엇을 할 수 있어, 도움 줄 수 있는 것, 어떤 일을 해, 역할이 뭐야 등)
- "analysis": 분석이 필요한 질문 (기업명, 재무, 지배구조 등 구체적 분석 요청)

정확히 하나만 답변하세요: greeting, agent_intro, analysis"""
                
                # thread_id가 있으면 config로 전달하여 대화 히스토리 유지
                config = {}
                if thread_id:
                    config["configurable"] = {"thread_id": thread_id}
                
                response = await self.llm.ainvoke([HumanMessage(content=prompt)], config=config)
                result = response.content.lower().strip()
                
                # 응답 검증
                if result in ["greeting", "agent_intro", "analysis"]:
                    return result
                else:
                    # 기본값: analysis로 처리
                    return "analysis"
        except Exception as e:
            log_step("질문 유형 분류", "ERROR", f"오류: {str(e)}")
        
        # 오류 시 기본값: analysis로 처리
        return "analysis"

    @observe()
    async def coordinate_analysis_stream(
        self,
        user_question: str,
        thread_id: Optional[str] = None,
        user_email: Optional[str] = None,
        parent_carrier: Optional[Dict[str, str]] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        스트리밍 분석 조정 - 진행 과정을 실시간으로 프론트엔드에 전달
        
        Args:
            user_question: 사용자 질문
            thread_id: 세션 ID
            user_email: 사용자 이메일
            parent_carrier: 부모 OTEL context carrier (trace_id 계승용)
        """
        start_time = time.time()
        
        # OTEL 트레이싱 (span 생성)
        try:
            span = start_dart_span(
                "dart_master.coordinate_analysis_stream",
                {"question_length": len(user_question), "thread_id": thread_id or ""},
                parent_carrier
            ).__enter__()
        except Exception:
            span = None
        
        try:
            # LLM을 사용한 시작 알림 생성
            start_response = await self._generate_start_response(user_question)
            yield {"type": "start", "content": start_response}

            # 질문 유형 분류
            question_type = await self._classify_question_type(user_question, thread_id)
            
            # 인사 또는 에이전트 소개 질문
            if question_type in ["greeting", "agent_intro"]:
                if self.message_generator:
                    intro_message = await self.message_generator.generate_agent_introduction(
                        question_type=question_type,
                        context={"user_question": user_question}
                    )
                else:
                    intro_message = "안녕하세요! 저는 DART 공시 분석 전문 에이전트입니다. 기업의 재무제표, 지배구조, 자본변동 등 다양한 정보를 분석해드립니다. 궁금하신 기업이 있으신가요?"
                yield {"type": "complete", "content": intro_message}
                return

            log_step(
                "DartMasterAgent",
                "스트리밍 분석 조정 시작",
                f"질문: {user_question[:100]}...",
            )

            # 정상적인 멀티에이전트 플로우 진행

            # 1단계: 의도 분류 및 에이전트 선택
            # IntentClassifierAgent를 통한 의도 분류 및 에이전트 선택
            if not self.intent_classifier:
                error_msg = "의도 분류기가 초기화되지 않았습니다. 잠시 후 다시 시도해주세요."
                yield {"type": "error", "content": error_msg}
                return

            # IntentClassifierAgent의 스트리밍 응답 처리
            classification_result = None
            async for response in self.intent_classifier.classify_intent_and_select_agents(
                user_question,
                {},  # 빈 corp_info - IntentClassifierAgent가 모든 것을 직접 처리
            ):
                if isinstance(response, IntentClassificationResult):
                    classification_result = response
                else:
                    yield response

            if not classification_result or not hasattr(classification_result, "corp_info"):
                yield {"type": "error", "content": "의도 분류에 실패했습니다."}
                return

            # 분석 대상 정보 추출
            selected_agents = classification_result.required_agents or ["financial"]
            corp_info = classification_result.corp_info or {}

            # corp_info가 복수 기업인 경우 vs 단일 기업인 경우 처리
            if corp_info.get("is_multi_company", False):
                corp_info_list = corp_info.get("corp_info_list", [])
                corp_names = [info.get("corp_name", "N/A") for info in corp_info_list]
                target_display = f"{', '.join(corp_names)} ({len(corp_names)}개 기업)"
            else:
                target_display = corp_info.get("corp_name", "N/A")

            # 2단계: 선택된 에이전트들 실행
            result = None  # result 변수 초기화
            
            print(f"🔥🔥🔥 에이전트/기업 분기 체크:")
            print(f"🔥🔥🔥 - selected_agents: {selected_agents}, len: {len(selected_agents)}")
            print(f"🔥🔥🔥 - corp_info 타입: {type(corp_info)}")
            print(f"🔥🔥🔥 - isinstance(corp_info, list): {isinstance(corp_info, list)}")
            if hasattr(corp_info, 'get'):
                print(f"🔥🔥🔥 - corp_info.get('is_multi_company'): {corp_info.get('is_multi_company', False)}")
                print(f"🔥🔥🔥 - corp_info.get('corp_info_list'): {corp_info.get('corp_info_list', None)}")
            
            if len(selected_agents) == 1:
                agent_name = selected_agents[0]
                agent_display = {
                    "financial": "재무 분석",
                    "governance": "지배구조 분석",
                    "capital_change": "자본변동 분석",
                    "debt_funding": "부채자금조달 분석",
                    "business_structure": "사업구조 분석",
                    "overseas_business": "해외사업 분석",
                    "legal_risk": "법적리스크 분석",
                    "executive_audit": "경영진감사 분석",
                    "document_analysis": "공시 문서 기반 심층 분석",
                }.get(agent_name, agent_name)

                if self.message_generator:
                    progress_msg = await self.message_generator.generate_progress_message(
                        action="single_agent_analysis",
                        context={
                            "user_question": user_question,
                            "corp_name": target_display,
                            "agents": [agent_display]
                        }
                    )
                else:
                    progress_msg = f"{target_display}의 {agent_display}을 진행합니다..."
                yield {"type": "progress", "content": progress_msg}

                # 단일 기업 분석 실행 - corp_info 타입 처리
                if isinstance(corp_info, list) and corp_info:
                    # 리스트인 경우 첫 번째 기업 사용
                    first_corp = corp_info[0]
                    corp_code = first_corp.get("corp_code", "")
                    corp_name = first_corp.get("corp_name", "")
                else:
                    # 딕셔너리인 경우
                    corp_code = corp_info.get("corp_code", "")
                    corp_name = corp_info.get("corp_name", "")

                context = create_analysis_context(
                    corp_code=corp_code,
                    corp_name=corp_name,
                    user_question=user_question,
                    classification=classification_result,
                )

                # 에이전트 이름으로 실제 에이전트 객체 가져오기
                agent_name = selected_agents[0]
                if agent_name in self.sub_agents:
                    agent = self.sub_agents[agent_name]

                    # 각 에이전트의 스트리밍 메서드 직접 호출
                    if agent_name == "financial" and hasattr(agent, "analyze_financial_data"):
                        # FinancialAgent 스트리밍 처리
                        async for response in agent.analyze_financial_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                # 중간 스트리밍 메시지를 사용자에게 전달
                                yield response
                    elif agent_name == "governance" and hasattr(agent, "analyze_governance_data"):
                        # GovernanceAgent 스트리밍 처리
                        async for response in agent.analyze_governance_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "document_analysis" and hasattr(agent, "analyze_document_data"):
                        # DocumentAnalysisAgent 스트리밍 처리
                        async for response in agent.analyze_document_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "capital_change" and hasattr(agent, "analyze_capital_data"):
                        # CapitalChangeAgent 스트리밍 처리
                        async for response in agent.analyze_capital_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "debt_funding" and hasattr(
                        agent, "analyze_debt_funding_data"
                    ):
                        # DebtFundingAgent 스트리밍 처리
                        async for response in agent.analyze_debt_funding_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "business_structure" and hasattr(
                        agent, "analyze_business_structure_data"
                    ):
                        # BusinessStructureAgent 스트리밍 처리
                        async for response in agent.analyze_business_structure_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "overseas_business" and hasattr(
                        agent, "analyze_overseas_business_data"
                    ):
                        # OverseasBusinessAgent 스트리밍 처리
                        async for response in agent.analyze_overseas_business_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "legal_risk" and hasattr(agent, "analyze_legal_risk_data"):
                        # LegalComplianceAgent 스트리밍 처리
                        async for response in agent.analyze_legal_risk_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    elif agent_name == "executive_audit" and hasattr(
                        agent, "analyze_executive_audit_data"
                    ):
                        # ExecutiveAuditAgent 스트리밍 처리
                        async for response in agent.analyze_executive_audit_data(context):
                            if isinstance(response, AgentResult):
                                result = response
                                break
                            else:
                                yield response
                    else:
                        pass
                        log_step(
                            f"{agent_name} 에이전트 없음",
                            "WARNING",
                            f"등록되지 않은 에이전트: {agent_name}",
                        )
                else:
                    yield {
                        "type": "error",
                        "content": f"요청된 에이전트 '{agent_name}'를 찾을 수 없습니다.",
                    }
                    return
                
                # 단일 에이전트 분석 후 깊은 분석이 필요한 경우 추가 분석 실행
                print(f"🔥🔥🔥 추가 분석 분기 체크: needs_deep_analysis={classification_result.needs_deep_analysis}, result={result is not None}")
                if classification_result.needs_deep_analysis and result:
                    print(f"🔥🔥🔥 추가 분석 분기 진입: needs_deep_analysis={classification_result.needs_deep_analysis}")
                    if self.message_generator:
                        progress_msg = await self.message_generator.generate_progress_message(
                            action="additional_analysis",
                            context={
                                "user_question": user_question,
                                "corp_name": target_display,
                                "agents": ["추가 분석"],
                                "reasoning": classification_result.analysis_reasoning
                            }
                        )
                    else:
                        progress_msg = f"{target_display}에 대한 추가 심층 분석을 진행합니다..."
                    yield {"type": "progress", "content": progress_msg}
                    
                    # 2차 분석: LLM이 결과를 보고 추가 에이전트 결정
                    print(f"🔥🔥🔥 _determine_additional_agents 호출 직전")
                    additional_analysis = await self._determine_additional_agents(
                        [result], classification_result, user_question
                    )
                    additional_agents = additional_analysis.get("agents", [])
                    additional_reasoning = additional_analysis.get("reasoning", "")
                    print(f"🔥🔥🔥 _determine_additional_agents 호출 완료: additional_agents={additional_agents}")
                    
                    if additional_agents:
                        yield {
                            "type": "progress",
                            "content": f"추가 에이전트 {additional_agents}를 호출하여 심층 분석을 진행합니다..."
                        }
                        
                        # 추가 에이전트 실행
                        additional_results = []
                        async for response in self._execute_sub_agents_for_data_collection(
                            context, additional_agents, additional_reasoning, thread_id
                        ):
                            if response.get("type") == "agent_results":
                                additional_results = response.get("results", [])
                            else:
                                yield response
                        
                        # 결과 통합 (1차 + 2차) - 스트리밍 방식
                        all_results = [result] + additional_results
                        intent_dict = classification_result.to_dict()
                        intent_dict["additional_reasoning"] = additional_reasoning
                        
                        yield {
                            "type": "progress",
                            "content": f"추가 분석 완료. 총 {len(all_results)}개 에이전트의 결과를 통합합니다."
                        }
                        
                        # 스트리밍 통합 결과 전달
                        integrated_response = ""
                        async for chunk in self._integrate_agent_results_stream(
                            all_results, corp_info, intent_dict, user_question
                        ):
                            if chunk.get("type") == "stream_chunk":
                                integrated_response += chunk.get("content", "")
                                yield {"type": "content", "content": chunk.get("content", "")}
                            elif chunk.get("type") == "final":
                                result = chunk.get("result")
            else:
                # 복수 기업 또는 복합 분석
                agent_display = {
                    "financial": "재무 분석",
                    "governance": "지배구조 분석",
                    "capital_change": "자본변동 분석",
                    "debt_funding": "부채자금조달 분석",
                    "business_structure": "사업구조 분석",
                    "overseas_business": "해외사업 분석",
                    "legal_risk": "법적리스크 분석",
                    "executive_audit": "경영진감사 분석",
                    "document_analysis": "공시 문서 기반 심층 분석",
                }
                agent_names = [agent_display.get(agent, agent) for agent in selected_agents]

                progress_msg = await self.message_generator.generate_progress_message(
                    action="multi_agent_analysis",
                    context={
                        "user_question": user_question,
                        "corp_name": target_display,
                        "agents": agent_names
                    }
                )
                yield {"type": "progress", "content": progress_msg}

                # 복수 기업 또는 복수 에이전트 분석 실행
                print(f"🔥🔥🔥 분기처리 체크 - corp_info 타입: {type(corp_info)}")
                print(f"🔥🔥🔥 분기처리 체크 - corp_info.get('is_multi_company'): {corp_info.get('is_multi_company', False)}")
                print(f"🔥🔥🔥 분기처리 체크 - corp_info.get('corp_info_list'): {corp_info.get('corp_info_list', None)}")
                
                if corp_info.get("is_multi_company", False):
                    corp_info_list = corp_info.get("corp_info_list", [])
                    print(f"🔥🔥🔥 복수 기업 분석 경로 진입 - 기업 수: {len(corp_info_list)}")
                    # 복수 기업 분석 처리
                    result = await self._handle_multi_company_analysis(
                        user_question, corp_info_list, selected_agents, classification_result, thread_id
                    )
                else:
                    # 단일 기업, 복수 에이전트 (이미 위에서 메시지 yield함)

                    context = create_analysis_context(
                        corp_code=corp_info.get("corp_code", ""),
                        corp_name=corp_info.get("corp_name", ""),
                        user_question=user_question,
                        classification=classification_result,
                    )

                    # 1차 분석: 복수 에이전트 협업 실행 (스트리밍 지원)
                    results = []
                    additional_reasoning = ""  # 추가 에이전트 분석 추론 (없으면 빈 문자열)
                    async for response in self._execute_sub_agents_for_data_collection(
                        context, selected_agents, thread_id=thread_id
                    ):
                        if response.get("type") == "agent_results":
                            # 최종 결과 수집
                            results = response.get("results", [])
                        else:
                            # 중간 스트리밍 메시지 전달
                            yield response

                    # 깊은 분석이 필요한 경우 추가 분석 실행
                    if classification_result.needs_deep_analysis and results:
                        yield {
                            "type": "progress",
                            "content": f"추가 분석이 필요합니다. {classification_result.analysis_reasoning}"
                        }
                        
                        # 2차 분석: LLM이 결과를 보고 추가 에이전트 결정
                        additional_analysis = await self._determine_additional_agents(
                            results, classification_result, user_question
                        )
                        additional_agents = additional_analysis.get("agents", [])
                        additional_reasoning = additional_analysis.get("reasoning", "")
                        
                        if additional_agents:
                            yield {
                                "type": "progress",
                                "content": f"추가 에이전트 {additional_agents}를 호출하여 심층 분석을 진행합니다..."
                            }
                            
                            # 추가 에이전트 실행
                            additional_results = []
                            async for response in self._execute_sub_agents_for_data_collection(
                                context, additional_agents, additional_reasoning, thread_id
                            ):
                                if response.get("type") == "agent_results":
                                    additional_results = response.get("results", [])
                                else:
                                    yield response
                            
                            # 결과 통합 (1차 + 2차)
                            results.extend(additional_results)
                            
                            progress_msg = await self.message_generator.generate_progress_message(
                                action="result_integration",
                                context={
                                    "user_question": user_question,
                                    "corp_name": target_display,
                                    "agents": [f"{len(results)}개 에이전트"],
                                    "reasoning": "결과 통합 중"
                                }
                            )
                            yield {"type": "progress", "content": progress_msg}

                    # 결과 통합 - 스트리밍 방식
                    if results:
                        intent_dict = classification_result.to_dict()
                        intent_dict["additional_reasoning"] = additional_reasoning
                        
                        yield {
                            "type": "progress",
                            "content": "분석 결과를 통합하고 최종 보고서를 작성하고 있습니다...",
                        }
                        
                        # 스트리밍 통합 결과 전달
                        integrated_response = ""
                        async for chunk in self._integrate_agent_results_stream(
                            results, corp_info, intent_dict, user_question
                        ):
                            if chunk.get("type") == "stream_chunk":
                                integrated_response += chunk.get("content", "")
                                yield {"type": "content", "content": chunk.get("content", "")}
                            elif chunk.get("type") == "final":
                                result = chunk.get("result")
                    else:
                        yield {
                            "type": "error",
                            "content": "선택된 에이전트들에서 분석 결과를 얻을 수 없습니다.",
                        }
                        return

            # 3단계: 결과 통합 및 최종 응답
            print(f"🔥🔥🔥 3단계 진입: result type={type(result)}, has key_findings={hasattr(result, 'key_findings')}")
            if result:
                # 결과 타입에 따른 처리
                if isinstance(result, dict) and "response" in result:
                    # _integrate_agent_results_stream에서 이미 스트리밍으로 전달됨
                    response_content = result["response"]
                    # 스트리밍으로 이미 전달되었으므로 중복 출력하지 않음
                elif hasattr(result, "key_findings"):
                    # AgentResult 객체 - 스트리밍 통합 필요
                    yield {
                        "type": "progress",
                        "content": "분석 결과를 통합하고 있습니다...",
                    }
                    
                    # 단일 결과도 스트리밍 통합으로 처리
                    intent_dict = classification_result.to_dict() if hasattr(classification_result, 'to_dict') else {}
                    integrated_response = ""
                    async for chunk in self._integrate_agent_results_stream(
                        [result], corp_info, intent_dict, user_question
                    ):
                        if chunk.get("type") == "stream_chunk":
                            integrated_response += chunk.get("content", "")
                            yield {"type": "content", "content": chunk.get("content", "")}
                        elif chunk.get("type") == "final":
                            result = chunk.get("result")
                else:
                    # 기타 경우
                    response_content = str(result)
                    yield {"type": "content", "content": response_content}

                # 완료 알림
                execution_time = time.time() - start_time
                yield {
                    "type": "end",
                    "content": f"✅ 멀티에이전트 분석이 완료되었습니다. (소요시간: {execution_time:.1f}초)",
                }
            else:
                # result가 None인 경우 기본 응답
                yield {
                    "type": "content",
                    "content": "분석을 완료했으나 결과를 생성할 수 없습니다.",
                }
                yield {
                    "type": "end",
                    "content": "✅ 분석이 완료되었습니다.",
                }
            
        except Exception as e:
            log_step("DartMasterAgent 스트리밍 오류", "ERROR", str(e))
            yield {"type": "error", "content": f"분석 중 오류가 발생했습니다: {str(e)}"}

    @observe()
    async def _handle_multi_company_analysis(
        self,
        user_question: str,
        corp_info_list: List[Dict],
        selected_agents: List[str],
        classification: Any,
        thread_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """복수 기업 분석 처리"""
        try:
            log_step("복수 기업 분석 시작", "INFO", f"{len(corp_info_list)}개 기업 분석 시작")

            all_results = []
            company_results = {}

            # 각 기업별로 순차 분석
            for i, corp_info in enumerate(corp_info_list):
                company_name = corp_info.get("corp_name", f"기업{i+1}")
                log_step(f"기업 {i+1} 분석", "INFO", f"{company_name} 분석 시작")

                try:
                    # 개별 기업 컨텍스트 생성
                    context = create_analysis_context(
                        corp_code=corp_info.get("corp_code", ""),
                        corp_name=company_name,
                        user_question=user_question,
                        classification=classification,
                    )

                    # 개별 기업 에이전트 실행
                    agent_results = await self._execute_sub_agents_for_data_collection(
                        context, selected_agents, thread_id=thread_id
                    )

                    # 개별 기업 결과 저장
                    company_results[company_name] = {
                        "corp_info": corp_info,
                        "agent_results": agent_results,
                        "context": context,
                    }

                    all_results.extend(agent_results)
                    log_step(f"기업 {i+1} 완료", "SUCCESS", f"{company_name} 분석 완료")

                except Exception as e:
                    log_step(
                        f"기업 {i+1} 오류",
                        "ERROR",
                        f"{company_name} 분석 실패: {str(e)}",
                    )
                    company_results[company_name] = {
                        "corp_info": corp_info,
                        "error": str(e),
                    }

            # 복수 기업 통합 분석
            log_step("복수 기업 통합 분석", "INFO", "모든 기업 결과 통합 분석 시작")
            final_result = await self._integrate_multi_company_results(
                user_question, company_results, classification
            )

            log_step(
                "복수 기업 분석 완료",
                "SUCCESS",
                f"{len(corp_info_list)}개 기업 분석 완료",
            )
            return final_result

        except Exception as e:
            log_step("복수 기업 분석 오류", "ERROR", f"복수 기업 분석 중 오류: {str(e)}")
            return {"error": f"복수 기업 분석 중 오류가 발생했습니다: {str(e)}"}

    @observe()
    async def _integrate_multi_company_results(
        self, user_question: str, company_results: Dict, classification: Any
    ) -> Dict[str, Any]:
        """복수 기업 결과 통합 분석"""
        try:
            # 복수 기업 비교 분석을 위한 프롬프트 구성
            comparison_data = []

            for company_name, result_data in company_results.items():
                if "error" in result_data:
                    comparison_data.append(
                        f"**{company_name}**: 분석 실패 - {result_data['error']}"
                    )
                else:
                    agent_results = result_data.get("agent_results", [])
                    if agent_results:
                        # 🔥 FinancialAgent의 LLM 직접 분석 결과 추출 (개선된 로직)
                        llm_analysis_found = False

                        for result in agent_results:
                            print(f"🔥🔥🔥 {company_name} - AgentResult 확인:")
                            print(
                                f"🔥🔥🔥 key_findings 개수: {len(result.key_findings) if result.key_findings else 0}"
                            )
                            print(
                                f"🔥🔥🔥 supporting_data 키: {list(result.supporting_data.keys()) if result.supporting_data else []}"
                            )

                            # 1순위: key_findings에서 LLM 응답 추출
                            if result.key_findings and len(result.key_findings) > 0:
                                llm_analysis = result.key_findings[0]
                                if (
                                    llm_analysis and len(llm_analysis.strip()) > 50
                                ):  # 의미있는 응답인지 확인
                                    print(
                                        f"🔥🔥🔥 {company_name} - key_findings에서 LLM 응답 추출 성공: {len(llm_analysis)}자"
                                    )
                                    # LLM 분석 결과 전체 표시 (잘림 제거)
                                    comparison_data.append(
                                        f"**{company_name} 재무 분석 결과**:\n{llm_analysis}"
                                    )
                                    llm_analysis_found = True
                                    break

                            # 2순위: supporting_data에서 llm_response 추출
                            if result.supporting_data and "llm_response" in result.supporting_data:
                                llm_response = result.supporting_data["llm_response"]
                                if llm_response and len(llm_response.strip()) > 50:
                                    print(
                                        f"🔥🔥🔥 {company_name} - supporting_data에서 LLM 응답 추출 성공: {len(llm_response)}자"
                                    )
                                    # LLM 응답 전체 표시 (잘림 제거)
                                    comparison_data.append(
                                        f"**{company_name} 재무 분석 결과**:\n{llm_response}"
                                    )
                                    llm_analysis_found = True
                                    break

                        if not llm_analysis_found:
                            print(f"🔥🔥🔥 {company_name} - LLM 분석 결과 추출 실패")
                            comparison_data.append(
                                f"**{company_name}**: 재무 분석 결과 추출 실패 - 데이터 수집은 완료되었으나 LLM 응답을 찾을 수 없음"
                            )
                        else:
                            comparison_data.append(f"**{company_name}**: 에이전트 결과 없음")

            # IntentClassifierAgent의 분석 결과 추출
            user_intent = classification.get('reasoning', '') if hasattr(classification, 'get') else ''
            analysis_direction = classification.get('analysis_reasoning', '') if hasattr(classification, 'get') else ''
            
            # additional_reasoning이 있으면 user_intent 덮어쓰기
            additional_reasoning = classification.get('additional_reasoning', '') if hasattr(classification, 'get') else ''
            if additional_reasoning:
                user_intent = additional_reasoning
            
            # LLM을 통한 복수 기업 비교 분석
            comparison_prompt = f"""
사용자의 질문에 대해 수집된 모든 기업의 분석 결과를 종합하여 분석해주세요.

## 사용자 질문
"{user_question}"

## 질문 의도 분석
{user_intent}

## 분석 방향
{analysis_direction}

## 수집된 기업별 데이터
{chr(10).join(comparison_data)}

## 통합 지침
1. **질문 의도 중심**: 사용자가 묻는 내용에 집중하여 답변
2. **모든 기업 활용**: 각 기업의 핵심 내용을 모두 반영
3. **데이터 기반**: 구체적인 수치와 사실을 바탕으로 비교 분석
4. **자연스러운 흐름**: 질문 → 분석 과정 → 기업별 특징 → 비교 결과 → 시사점
5. **사용자 친화적**: 기술적 용어는 자연스러운 표현으로 변환
6. **한국어 응답**: 반드시 한국어로 응답

### 응답 형식
- **한국어 존댓말**: 정중하고 전문적인 톤으로 작성
- **반드시 한국어로 응답해야하며 중국어는 절대 사용하지 마세요.**
- **구조화된 형식**: 제목, 소제목, 목록을 활용한 명확한 구조
- **이모지 활용**: 가독성을 위해 적절한 이모지만 사용
- **완전한 응답**: 사용자 질문에 대한 완전하고 구체적인 답변 제공

위 정보를 바탕으로 사용자 질문에 대한 종합적이고 유용한 비교 분석을 작성해주세요.
"""

            # LLM 호출 (올바른 메시지 형태로)
            if hasattr(self, "llm") and self.llm:
                from langchain_core.messages import HumanMessage

                messages = [HumanMessage(content=comparison_prompt)]
                response = await self.llm.ainvoke(messages)
                analysis_content = (
                    response.content if hasattr(response, "content") else str(response)
                )
            else:
                analysis_content = (
                    "LLM을 사용할 수 없어 기본 비교 분석을 제공합니다.\n\n"
                    + "\n".join(comparison_data)
                )

            return {
                "response": analysis_content,  # 🔥 'analysis' → 'response'로 키 이름 수정
                "company_count": len(company_results),
                "companies": list(company_results.keys()),
                "analysis_type": "multi_company_comparison",
                "user_question": user_question,
                "metadata": {
                    "companies_analyzed": len(company_results),
                    "analysis_timestamp": datetime.now().isoformat(),
                },
            }
            
        except Exception as e:
            log_step("복수 기업 통합 분석 오류", "ERROR", f"오류: {str(e)}")
            return {
                "error": f"복수 기업 통합 분석 중 오류: {str(e)}",
                "company_results": company_results,
            }

    @observe()
    async def _integrate_agent_results(
        self,
        agent_results: List[AgentResult],
        corporation_info: Dict[str, Any],
        intent_result: Dict[str, Any],
        user_question: str,
    ) -> Dict[str, Any]:
        """각 에이전트의 결과를 통합하여 최종 응답 생성 (비스트리밍 버전)"""
        # 스트리밍 버전을 호출하고 전체 응답을 수집
        integrated_response = ""
        final_result = None
        
        async for chunk in self._integrate_agent_results_stream(
            agent_results, corporation_info, intent_result, user_question
        ):
            if chunk.get("type") == "stream_chunk":
                integrated_response += chunk.get("content", "")
            elif chunk.get("type") == "final":
                final_result = chunk.get("result")
        
        if final_result:
            final_result["response"] = integrated_response
            return final_result
        
        return {"response": integrated_response, "analysis_type": "multi_agent_coordinated"}
    
    async def _integrate_agent_results_stream(
        self,
        agent_results: List[AgentResult],
        corporation_info: Dict[str, Any],
        intent_result: Dict[str, Any],
        user_question: str,
    ):
        """각 에이전트의 결과를 통합하여 최종 응답 스트리밍"""
        try:
            log_step(
                "결과 통합 시작",
                "INFO",
                f"통합할 에이전트 결과: {len(agent_results)}개",
            )
            
            # 기업 기본 정보
            corp_name = corporation_info.get("corp_name", "해당 기업")
            corp_code = corporation_info.get("corp_code", "N/A")
            
            # 업종 정보 추출
            industry = corporation_info.get("industry_classification", "")
            industry_guidance = ""
            if industry:
                industry_guidance = f"\n## 🏭 업종별 분석 지침\n- 분석 대상 업종: {industry}\n- 업종 특성을 고려한 분석 수행\n"
                log_step("업종 정보 확인", "SUCCESS", f"업종: {industry}")
            else:
                industry_guidance = "\n## 🏭 업종별 분석 지침\n- 업종 정보를 확인할 수 없습니다.\n- 일반적인 재무 분석 기준을 적용합니다.\n"
                log_step("업종 정보 없음", "WARNING", "업종 정보를 확인할 수 없음")
            
            # IntentClassifierAgent의 분석 결과 추출
            user_intent = intent_result.get('reasoning', '')
            analysis_direction = intent_result.get('analysis_reasoning', '')
            needs_deep_analysis = intent_result.get('needs_deep_analysis', False)
            
            # additional_reasoning이 있으면 user_intent 덮어쓰기
            additional_reasoning = intent_result.get('additional_reasoning', '')
            if additional_reasoning:
                user_intent = additional_reasoning

            # 에이전트명을 사용자 친화적으로 매핑
            agent_display_names = {
                "FinancialAgent": "재무 분석",
                "GovernanceAgent": "지배구조 분석", 
                "DebtFundingAgent": "부채 및 자금조달 분석",
                "LegalComplianceAgent": "법적 리스크 분석",
                "ExecutiveAuditAgent": "경영진 및 감사 분석",
                "BusinessStructureAgent": "사업구조 분석",
                "CapitalChangeAgent": "자본변동 분석",
                "OverseasBusinessAgent": "해외사업 분석",
                "DocumentAnalysisAgent": "문서 기반 심층 분석"
            }

            # 각 에이전트의 결과를 구조화
            agent_insights = []
            successful_agents = 0
            
            for i, agent_result in enumerate(agent_results):
                if not hasattr(agent_result, "agent_name"):
                    log_step(
                        "잘못된 결과 타입",
                        "ERROR",
                        f"인덱스 {i}: AgentResult가 아닌 객체 - 타입: {type(agent_result)}",
                    )
                    continue

                agent_name = getattr(agent_result, "agent_name", "Unknown Agent")
                display_name = agent_display_names.get(agent_name, agent_name)
                has_error = hasattr(agent_result, "error_message") and agent_result.error_message

                if not has_error:
                    # 에이전트 결과 구조화
                    insight = {
                        "agent_name": display_name,
                        "key_findings": agent_result.key_findings if hasattr(agent_result, "key_findings") else [],
                        "supporting_data": agent_result.supporting_data if hasattr(agent_result, "supporting_data") else {},
                        "recommendations": agent_result.recommendations if hasattr(agent_result, "recommendations") else []
                    }
                    agent_insights.append(insight)
                    successful_agents += 1
                else:
                    error_msg = getattr(agent_result, "error_message", "알 수 없는 오류")
                    insight = {
                        "agent_name": display_name,
                        "error": error_msg
                    }
                    agent_insights.append(insight)

            # LLM을 통한 통합 분석
            integration_prompt = f"""
사용자의 질문에 대해 수집된 모든 에이전트의 분석 결과를 종합하여 답변해주세요.

## 사용자 질문
"{user_question}"

## 질문 의도 분석
{user_intent}

## 분석 방향
{analysis_direction}

## 기업 정보
- 기업명: {corp_name}
- 기업코드: {corp_code}

{industry_guidance}

## 각 에이전트 분석 결과
{self._format_agent_insights(agent_insights)}

## 통합 지침
1. **질문 의도 중심**: 사용자가 묻는 내용에 집중하여 답변
2. **모든 에이전트 활용**: 각 에이전트의 핵심 내용을 모두 반영
3. **데이터 기반**: 구체적인 수치와 사실을 바탕으로 분석
4. **자연스러운 흐름**: 질문 → 분석 과정 → 발견 내용 → 시사점 → 결론
5. **추측 금지**: 각 에이전트의 내용에 없는 내용은 절대 추가하지 마세요
6. **투자 관점 배제**: 투자 조언, 투자 판단, 수익성 평가를 배제하세요
7. **업종 특성 반영**: {industry if industry else '해당'}업종의 특성을 고려한 분석 수행
7. **사용자 친화적**: 기술적 용어는 자연스러운 표현으로 변환
8. **한국어 응답**: 반드시 한국어로 응답

위 정보를 바탕으로 사용자 질문에 대한 종합적이고 유용한 답변을 최대한 길게 작성해주세요.
"""

            # LLM 호출 (스트리밍 또는 비스트리밍)
            integrated_response = ""
            if hasattr(self, "llm") and self.llm:
                try:
                    from langchain_core.messages import HumanMessage
                    
                    # astream이 있으면 스트리밍, 없으면 ainvoke 사용
                    if hasattr(self.llm, "astream"):
                        log_step("LLM 스트리밍 호출", "INFO", "결과 통합을 위한 LLM 스트리밍 시작")
                        
                        # 스트리밍 응답 전송
                        async for chunk in self.llm.astream([HumanMessage(content=integration_prompt)]):
                            chunk_content = chunk.content if hasattr(chunk, "content") else str(chunk)
                            if chunk_content:
                                integrated_response += chunk_content
                                yield {"type": "stream_chunk", "content": chunk_content}
                        
                        log_step("LLM 스트리밍 완료", "SUCCESS", f"통합 응답 길이: {len(integrated_response)}자")
                    else:
                        # LiteLLMAdapter 등 astream이 없는 경우 ainvoke 사용
                        log_step("LLM 호출 (비스트리밍)", "INFO", "결과 통합을 위한 LLM 호출 시작 (ainvoke)")
                        
                        response = await self.llm.ainvoke([HumanMessage(content=integration_prompt)])
                        integrated_response = response.content if hasattr(response, "content") else str(response)
                        
                        # 청크 단위로 나눠서 스트리밍처럼 전달 (사용자 경험 개선)
                        chunk_size = 100
                        for i in range(0, len(integrated_response), chunk_size):
                            yield {"type": "stream_chunk", "content": integrated_response[i:i+chunk_size]}
                        
                        log_step("LLM 호출 완료", "SUCCESS", f"통합 응답 길이: {len(integrated_response)}자")
                    
                except Exception as llm_error:
                    log_step("LLM 호출 오류", "ERROR", f"LLM 호출 중 오류: {str(llm_error)}")
                    import traceback
                    traceback.print_exc()
                    integrated_response = f"{corp_name}에 대한 분석이 완료되었습니다. (LLM 호출 중 오류가 발생했습니다: {str(llm_error)})"
                    yield {"type": "stream_chunk", "content": integrated_response}
            else:
                log_step("LLM 없음", "WARNING", "LLM이 초기화되지 않았습니다.")
                integrated_response = f"{corp_name}에 대한 분석이 완료되었습니다. (LLM을 사용할 수 없어 기본 응답을 제공합니다.)"
                yield {"type": "stream_chunk", "content": integrated_response}

            log_step(
                "결과 통합 완료",
                "SUCCESS",
                f"통합된 응답 길이: {len(integrated_response)}자",
            )
            
            # 최종 결과 반환
            yield {
                "type": "final",
                "result": {
                    "response": integrated_response,
                    "analysis_type": "multi_agent_coordinated",
                    "agents_involved": [
                        getattr(result, "agent_name", "Unknown")
                        for result in agent_results
                        if hasattr(result, "agent_name")
                    ],
                    "successful_agents": successful_agents,
                    "total_agents": len(agent_results),
                    "corporation_info": corporation_info,
                    "intent_result": intent_result,
                }
            }
            
        except Exception as e:
            log_step("결과 통합 오류", "ERROR", f"결과 통합 중 오류: {str(e)}")
            corp_name = corporation_info.get("corp_name", "해당 기업")
            yield {
                "type": "final",
                "result": {
                    "response": f"{corp_name} 분석이 완료되었습니다. (결과 통합 중 일부 오류가 발생했습니다)",
                    "error": True,
                    "analysis_type": "integration_error",
                }
            }

    def _format_agent_insights(self, agent_insights: List[Dict[str, Any]]) -> str:
        """에이전트 인사이트를 LLM이 이해할 수 있는 형태로 포맷팅
        
        핵심: key_findings + supporting_data(도구 호출 결과)를 모두 포함하여 
        LLM이 실제 데이터를 기반으로 분석할 수 있도록 함
        """
        formatted_insights = []
        
        for insight in agent_insights:
            agent_name = insight.get("agent_name", "Unknown Agent")
            
            if "error" in insight:
                formatted_insights.append(f"### {agent_name}\n오류: {insight['error']}\n")
            else:
                formatted_insights.append(f"### {agent_name}")
                
                # 1. key_findings (LLM의 분석 결과)
                if insight.get("key_findings"):
                    findings = insight["key_findings"]
                    if isinstance(findings, list):
                        findings_text = "\n".join([f"- {finding}" for finding in findings])
                    else:
                        findings_text = str(findings)
                    formatted_insights.append(f"주요 발견사항:\n{findings_text}")
                
                # 2. supporting_data (도구 호출 결과) - 핵심 데이터 추출
                supporting_data = insight.get("supporting_data", {})
                if supporting_data:
                    # llm_response가 있으면 우선 사용 (이미 분석된 결과)
                    llm_response = supporting_data.get("llm_response", "")
                    if llm_response and len(str(llm_response).strip()) > 50:
                        formatted_insights.append(f"분석 상세:\n{llm_response}")
                    
                    # raw_financial_data (도구 호출 원시 결과) 요약
                    raw_data = supporting_data.get("raw_financial_data", {})
                    if raw_data and isinstance(raw_data, dict):
                        data_summary = self._summarize_raw_data(raw_data)
                        if data_summary:
                            formatted_insights.append(f"수집된 데이터:\n{data_summary}")
                
                # 3. recommendations
                if insight.get("recommendations"):
                    recommendations = insight["recommendations"]
                    if isinstance(recommendations, list):
                        rec_text = "\n".join([f"- {rec}" for rec in recommendations])
                    else:
                        rec_text = str(recommendations)
                    formatted_insights.append(f"권고사항:\n{rec_text}")
                
                formatted_insights.append("")  # 빈 줄 추가
        
        return "\n".join(formatted_insights)
    
    def _summarize_raw_data(self, raw_data: Dict[str, Any], max_items: int = 5) -> str:
        """도구 호출 원시 데이터를 LLM이 이해할 수 있도록 포맷팅
        
        Args:
            raw_data: 도구별 원시 결과 딕셔너리
            max_items: 사용하지 않음 (하위 호환성 유지)
            
        Returns:
            전체 데이터를 JSON 형식으로 포맷팅한 문자열
        """
        if not raw_data:
            return ""
        
        import json
        
        formatted_data = []
        for tool_name, result in raw_data.items():
            if not result:
                continue
            
            try:
                # JSON 문자열인 경우 파싱
                if isinstance(result, str):
                    try:
                        result = json.loads(result)
                    except json.JSONDecodeError:
                        formatted_data.append(f"### {tool_name}\n{result}")
                        continue
                
                # 전체 데이터를 JSON으로 포맷팅
                result_json = json.dumps(result, ensure_ascii=False, indent=2)
                formatted_data.append(f"### {tool_name}\n```json\n{result_json}\n```")
            except Exception as e:
                log_step("데이터 포맷팅 오류", "WARNING", f"도구 {tool_name} 데이터 포맷팅 중 오류: {str(e)}")
                continue
        
        return "\n\n".join(formatted_data) if formatted_data else ""
    
    def _format_sample_items(self, items: List[Any], max_fields: int = 8) -> str:
        """샘플 항목들을 포맷팅
        
        Args:
            items: 샘플 항목 리스트
            max_fields: 각 항목당 최대 표시 필드 수
            
        Returns:
            포맷된 문자열
        """
        if not items:
            return ""
        
        formatted = []
        for i, item in enumerate(items, 1):
            if isinstance(item, dict):
                # 중요 필드 우선 표시
                priority_fields = ["corp_name", "acnt_nm", "thstrm_amount", "thstrm_dt", 
                                   "stock_knd", "csm", "iscrtm_sctn_nm", "rcept_no"]
                fields = []
                
                # 우선 필드 먼저 추가
                for field in priority_fields:
                    if field in item:
                        value = item[field]
                        if value:
                            fields.append(f"{field}: {value}")
                
                # 나머지 필드 추가 (max_fields 제한)
                remaining = max_fields - len(fields)
                for k, v in item.items():
                    if k not in priority_fields and remaining > 0 and v:
                        fields.append(f"{k}: {v}")
                        remaining -= 1
                
                if fields:
                    formatted.append(f"  [{i}] {', '.join(fields)}")
            else:
                formatted.append(f"  [{i}] {str(item)[:100]}")
        
        return "\n".join(formatted)

    @observe()
    async def _execute_sub_agents_for_data_collection(
        self, context: Dict[str, Any], selected_agents: List[str], additional_reasoning: str = "", thread_id: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        # 결과 저장
        results: List[AgentResult] = []
        log_step("데이터 수집 에이전트 실행", "INFO", f"선택된 에이전트: {selected_agents}")
        log_step("사용 가능한 에이전트", "INFO", f"등록된 에이전트: {list(self.sub_agents.keys())}")
        
        # additional_reasoning이 있으면 context의 intent_reasoning 덮어쓰기
        if additional_reasoning:
            context.intent_reasoning = additional_reasoning

        # 1. 단일 에이전트는 기존 방식 그대로 스트리밍
        if len(selected_agents) == 1:
            agent_key = selected_agents[0]
            if agent_key not in self.sub_agents:
                log_step(f"{agent_key} 에이전트 없음", "WARNING", f"등록되지 않은 에이전트: {agent_key}")
                yield {"type": "agent_results", "results": []}
                return

            agent = self.sub_agents[agent_key]
            # 호출할 메서드를 정해 바로 스트리밍. 중간 메시지는 즉시 yield.
            async def sequential_stream(async_gen):
                async for response in async_gen:
                    if isinstance(response, AgentResult):
                        results.append(response)
                        log_step(f"{agent_key} 데이터 수집 완료", "SUCCESS", f"수집 결과: {response.analysis_type}")
                        # 각 에이전트의 응답을 즉시 yield
                        agent_response_content = None
                        if hasattr(response, "supporting_data") and response.supporting_data:
                            # supporting_data에서 llm_response 추출
                            agent_response_content = response.supporting_data.get("llm_response")
                        if not agent_response_content and hasattr(response, "key_findings") and response.key_findings:
                            # key_findings를 응답으로 사용
                            agent_response_content = "\n".join(response.key_findings)
                        if agent_response_content:
                            yield {
                                "type": "agent_response",
                                "agent_name": getattr(response, "agent_name", agent_key),
                                "content": agent_response_content
                            }
                        break
                    else:
                        yield response

            # 재무/지배구조 등 해당 메서드 호출
            if agent_key == "financial" and hasattr(agent, "analyze_financial_data"):
                async for msg in sequential_stream(agent.analyze_financial_data(context)):
                    yield msg
            elif agent_key == "governance" and hasattr(agent, "analyze_governance_data"):
                async for msg in sequential_stream(agent.analyze_governance_data(context)):
                    yield msg
            elif agent_key == "capital_change" and hasattr(agent, "analyze_capital_data"):
                async for msg in sequential_stream(agent.analyze_capital_data(context)):
                    yield msg
            elif agent_key == "debt_funding" and hasattr(agent, "analyze_debt_funding_data"):
                async for msg in sequential_stream(agent.analyze_debt_funding_data(context)):
                    yield msg
            elif agent_key == "business_structure" and hasattr(agent, "analyze_business_structure_data"):
                async for msg in sequential_stream(agent.analyze_business_structure_data(context)):
                    yield msg
            elif agent_key == "overseas_business" and hasattr(agent, "analyze_overseas_business_data"):
                async for msg in sequential_stream(agent.analyze_overseas_business_data(context)):
                    yield msg
            elif agent_key == "legal_risk" and hasattr(agent, "analyze_legal_risk_data"):
                async for msg in sequential_stream(agent.analyze_legal_risk_data(context)):
                    yield msg
            elif agent_key == "executive_audit" and hasattr(agent, "analyze_executive_audit_data"):
                async for msg in sequential_stream(agent.analyze_executive_audit_data(context)):
                    yield msg
            elif agent_key == "document_analysis" and hasattr(agent, "analyze_document_data"):
                async for msg in sequential_stream(agent.analyze_document_data(context)):
                    yield msg
            # 마지막에 결과 전달
            yield {"type": "agent_results", "results": results}
            return

        # 2. 복수 에이전트는 병렬로 실행 후 스트리밍
        import asyncio

        async def run_agent_with_queue(agent_key: str, queue: asyncio.Queue):
            if agent_key not in self.sub_agents:
                log_step(f"{agent_key} 에이전트 없음", "WARNING", f"등록되지 않은 에이전트: {agent_key}")
                await queue.put(("done", None))
                return

            agent = self.sub_agents[agent_key]

            async def forward_stream(async_gen):
                async for response in async_gen:
                    if isinstance(response, AgentResult):
                        await queue.put(("result", response))
                        log_step(f"{agent_key} 데이터 수집 완료", "SUCCESS",
                                 f"수집 결과: {response.analysis_type}")
                        # 각 에이전트의 응답을 즉시 yield
                        agent_response_content = None
                        if hasattr(response, "supporting_data") and response.supporting_data:
                            # supporting_data에서 llm_response 추출
                            agent_response_content = response.supporting_data.get("llm_response")
                        if not agent_response_content and hasattr(response, "key_findings") and response.key_findings:
                            # key_findings를 응답으로 사용
                            agent_response_content = "\n".join(response.key_findings)
                        if agent_response_content:
                            await queue.put(("message", {
                                "type": "agent_response",
                                "agent_name": getattr(response, "agent_name", agent_key),
                                "content": agent_response_content
                            }))
                        break
                    else:
                        await queue.put(("message", response))

            # 적절한 분석 메서드 호출
            try:
                if agent_key == "financial" and hasattr(agent, "analyze_financial_data"):
                    await forward_stream(agent.analyze_financial_data(context))
                elif agent_key == "governance" and hasattr(agent, "analyze_governance_data"):
                    await forward_stream(agent.analyze_governance_data(context))
                elif agent_key == "capital_change" and hasattr(agent, "analyze_capital_data"):
                    await forward_stream(agent.analyze_capital_data(context))
                elif agent_key == "debt_funding" and hasattr(agent, "analyze_debt_funding_data"):
                    await forward_stream(agent.analyze_debt_funding_data(context))
                elif agent_key == "business_structure" and hasattr(agent, "analyze_business_structure_data"):
                    await forward_stream(agent.analyze_business_structure_data(context))
                elif agent_key == "overseas_business" and hasattr(agent, "analyze_overseas_business_data"):
                    await forward_stream(agent.analyze_overseas_business_data(context))
                elif agent_key == "legal_risk" and hasattr(agent, "analyze_legal_risk_data"):
                    await forward_stream(agent.analyze_legal_risk_data(context))
                elif agent_key == "executive_audit" and hasattr(agent, "analyze_executive_audit_data"):
                    await forward_stream(agent.analyze_executive_audit_data(context))
                elif agent_key == "document_analysis" and hasattr(agent, "analyze_document_data"):
                    await forward_stream(agent.analyze_document_data(context))
            except Exception as e:
                log_step(f"{agent_key} 데이터 수집 오류", "ERROR", f"병렬 실행 중 오류: {str(e)}")
            finally:
                # 에이전트 작업이 끝났음을 알림
                await queue.put(("done", None))

        # 큐 및 task 설정
        queues: Dict[str, asyncio.Queue] = {}
        tasks = []
        for agent_name in selected_agents:
            q = asyncio.Queue()
            queues[agent_name] = q
            tasks.append(asyncio.create_task(run_agent_with_queue(agent_name, q)))

        # 에이전트 순서대로 큐에서 메시지를 읽어 스트리밍
        for agent_name in selected_agents:
            q = queues.get(agent_name)
            if not q:
                continue
            while True:
                msg_type, data = await q.get()
                if msg_type == "message":
                    yield data            # 도중 메시지를 즉시 출력
                elif msg_type == "result":
                    results.append(data)  # 최종 결과 저장
                elif msg_type == "done":
                    break                # 해당 에이전트 스트림 종료

        # 병렬 작업 종료 대기
        await asyncio.gather(*tasks, return_exceptions=True)
        log_step("데이터 수집 완료", "SUCCESS",
                 f"총 {len(results)}개 에이전트에서 데이터 수집")
        yield {"type": "agent_results", "results": results}

    @observe()
    async def _determine_additional_agents(
        self, 
        initial_results: List[AgentResult], 
        classification_result: IntentClassificationResult, 
        user_question: str
    ) -> Dict[str, Any]:
        """LLM이 초기 결과를 보고 추가 에이전트 필요성 판단"""
        try:
            print(f"🔥🔥🔥 _determine_additional_agents 시작")
            print(f"🔥🔥🔥 initial_results 개수: {len(initial_results)}")
            print(f"🔥🔥🔥 classification_result.required_agents: {classification_result.required_agents}")
            print(f"🔥🔥🔥 classification_result.recommended_agents: {classification_result.recommended_agents}")
            print(f"🔥🔥🔥 classification_result.needs_deep_analysis: {classification_result.needs_deep_analysis}")
            
            log_step("추가 분석 필요성 판단 시작", "INFO", f"초기 결과: {len(initial_results)}개")
            
            # 초기 결과 요약 및 호출된 에이전트 추출
            results_summary = []
            called_agents = []
            for result in initial_results:
                if hasattr(result, "agent_name") and hasattr(result, "key_findings"):
                    agent_name = result.agent_name.lower().replace("agent", "")
                    called_agents.append(agent_name)
                    findings = result.key_findings if result.key_findings else ["분석 결과 없음"]
                    results_summary.append(f"- {result.agent_name}: {findings[0] if findings else '분석 결과 없음'}")
                elif hasattr(result, "agent_name"):
                    # key_findings가 없는 경우 로깅
                    agent_name = result.agent_name.lower().replace("agent", "")
                    called_agents.append(agent_name)
                    log_step(f"{result.agent_name} key_findings 누락", "WARNING", f"result type: {type(result)}, attrs: {dir(result)}")
                    # supporting_data에서 llm_response 시도
                    llm_response = ""
                    if hasattr(result, "supporting_data") and result.supporting_data:
                        llm_response = result.supporting_data.get("llm_response", "")
                    results_summary.append(f"- {result.agent_name}: {llm_response if llm_response else '분석 결과 없음'}")
            
            print(f"🔥🔥🔥 called_agents: {called_agents}")
            print(f"🔥🔥🔥 results_summary: {results_summary}")
            
            # 최근 공시 정보 - 전체 표시
            disclosure_summary = ""
            if classification_result.recent_disclosures:
                disclosure_summary = "\n최근 공시 정보:\n"
                
                # recent_disclosures 타입에 따라 처리
                if isinstance(classification_result.recent_disclosures, dict):
                    # 복수 기업: 딕셔너리 형태 - 모든 공시 표시
                    for company_name, disclosures in classification_result.recent_disclosures.items():
                        if isinstance(disclosures, list) and disclosures:
                            for disclosure in disclosures:  # 모든 공시 표시
                                title = disclosure.get("report_nm", "제목 없음")
                                date = disclosure.get("rcept_dt", "날짜 없음")
                                rcp_no = disclosure.get("rcept_no", "")
                                disclosure_summary += f"- {company_name}: {date} - {title} (접수번호: {rcp_no})\n"
                elif isinstance(classification_result.recent_disclosures, list):
                    # 단일 기업: 리스트 형태 - 모든 공시 표시
                    for disclosure in classification_result.recent_disclosures:  # 모든 공시 표시
                        title = disclosure.get("report_nm", disclosure.get("title", "제목 없음"))
                        date = disclosure.get("rcept_dt", disclosure.get("date", "날짜 없음"))
                        rcp_no = disclosure.get("rcept_no", "")
                        disclosure_summary += f"- {date}: {title} (접수번호: {rcp_no})\n"
            else:
                disclosure_summary = "\n최근 공시 정보: 없음"
            
            # 질문 의도 파악 정보 추출
            intent_info = f"""
## 질문 의도 분석
- 분석 범위: {classification_result.scope.value if hasattr(classification_result.scope, 'value') else str(classification_result.scope)}
- 분석 영역: {classification_result.domain.value if hasattr(classification_result.domain, 'value') else str(classification_result.domain)}
- 분석 깊이: {classification_result.depth.value if hasattr(classification_result.depth, 'value') else str(classification_result.depth)}
- 깊은 분석 필요: {classification_result.needs_deep_analysis}
- 분석 깊이 판단 근거: {classification_result.analysis_reasoning}
- 초기 추천 에이전트: {', '.join(classification_result.recommended_agents) if classification_result.recommended_agents else '없음'}
"""

            # LLM 분석 프롬프트
            analysis_prompt = f"""
초기 분석 결과를 검토하여 추가 분석이 필요한지 판단해주세요.

## 사용자 질문
{user_question}

{intent_info}

## 초기 분석 결과
{chr(10).join(results_summary) if results_summary else "분석 결과 없음"}

{disclosure_summary}

## 이미 호출된 에이전트
이미 호출된 에이전트: {', '.join(called_agents) if called_agents else '없음'}

## 판단 기준
다음 경우에 추가 분석이 필요합니다:
1. **질문의 의도가 완전히 충족되지 않은 경우**: 사용자가 원하는 분석 범위나 깊이가 초기 결과로는 부족한 경우
2. **특이점이나 리스크 신호가 발견된 경우**: 초기 분석에서 위험 신호나 특이사항이 발견되어 추가 조사가 필요한 경우
3. **최근 공시와 연관된 내용이 누락된 경우**: 최근 공시 정보와 연관된 분석이 부족한 경우
4. **추가적인 맥락이나 배경 정보가 필요한 경우**: 질문의 맥락을 완전히 이해하기 위해 추가 정보가 필요한 경우
5. **분석 깊이가 부족한 경우**: '깊은 분석 필요'로 분류되었지만 초기 에이전트만으로는 충분하지 않은 경우

## 사용 가능한 추가 에이전트
- financial: 재무 분석
- governance: 지배구조 분석
- business_structure: 사업구조 분석
- capital_change: 자본변동 분석
- debt_funding: 부채 및 자금조달 분석
- overseas_business: 해외사업 분석
- legal_risk: 법적 리스크 분석
- executive_audit: 경영진 및 감사 분석
- document_analysis: 공시 문서 기반 심층 분석

**중요**: 
1. 사용자 질문의 의도와 초기 분석 결과와 분석 깊이 판단 근거를 종합적으로 고려하여, **사용자 질문에 실질적인 답변이 완성되었는지** 판단하고 추가 분석이 필요한지 신중하게 판단해주세요.
2. 불필요한 추가 분석은 피하고, 질문에 대한 답변이 완성되기 위해 반드시 필요한 경우에만 추가 에이전트를 호출해주세요.
3. 이미 호출된 에이전트 결과가 충분하여 추가 분석이 필요없으면 제외하세요.

다음 JSON 형식으로 응답해주세요:
{{
    "needs_additional": true/false,
    "additional_agents": ["agent1", "agent2"],
    "reasoning": "판단 근거"
}}
"""

            # LLM 호출
            if hasattr(self, "llm") and self.llm:
                print(f"🔥🔥🔥 LLM 호출 시작")
                from langchain_core.messages import HumanMessage
                
                response = await self.llm.ainvoke([HumanMessage(content=analysis_prompt)])
                print(f"🔥🔥🔥 LLM 응답 수신: {response.content[:200] if response and hasattr(response, 'content') else 'None'}...")
                
                if response and hasattr(response, "content"):
                    import json
                    import re
                    
                    # JSON 파싱
                    json_match = re.search(r"\{.*\}", response.content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        print(f"🔥🔥🔥 JSON 추출: {json_str}")
                        llm_response = json.loads(json_str)
                        
                        needs_additional = llm_response.get("needs_additional", False)
                        additional_agents = llm_response.get("additional_agents", [])
                        reasoning = llm_response.get("reasoning", "")
                        
                        print(f"🔥🔥🔥 LLM 판단 결과: needs_additional={needs_additional}, additional_agents={additional_agents}")
                        print(f"🔥🔥🔥 LLM 판단 근거: {reasoning}")
                        
                        log_step(
                            "추가 분석 판단 완료",
                            "SUCCESS" if needs_additional else "INFO",
                            f"추가 필요: {needs_additional}, 에이전트: {additional_agents}, 이유: {reasoning}"
                        )
                        
                        return {
                            "agents": additional_agents if needs_additional else [],
                            "reasoning": reasoning
                        }
                    else:
                        print(f"🔥🔥🔥 JSON 파싱 실패")
                        log_step("추가 분석 판단 JSON 파싱 실패", "WARNING", "JSON 형식을 찾을 수 없음")
                        return {"agents": [], "reasoning": ""}
                else:
                    print(f"🔥🔥🔥 LLM 응답 없음")
                    log_step("추가 분석 판단 LLM 응답 없음", "WARNING", "LLM 응답이 비어있음")
                    return {"agents": [], "reasoning": ""}
            else:
                print(f"🔥🔥🔥 LLM 없음")
                log_step("추가 분석 판단 LLM 없음", "ERROR", "self.llm이 없음")
                return {"agents": [], "reasoning": ""}
                
        except Exception as e:
            log_step("추가 분석 판단 오류", "ERROR", f"오류: {str(e)}")
            return {"agents": [], "reasoning": ""}

    def _setup_agent(self):
        """에이전트 설정"""
        try:
            log_step(f"{self.agent_name} 에이전트 설정", "START", "create_agent 생성 중...")
                        
            # 도메인별 프롬프트를 문자열로 직접 전달
            domain_prompt = self._create_domain_prompt()
            
            # create_agent로 에이전트 생성 (prompt에 문자열 직접 전달)
            self.agent = create_agent(
                model=self.llm_with_tools,
                tools=self.filtered_tools,
                prompt=SystemMessage(content=domain_prompt),
                checkpointer=self.checkpointer
            )
            
            log_step(f"{self.agent_name} 에이전트 설정", "SUCCESS", "create_agent 생성 완료")
            
        except Exception as e:
            log_step(f"{self.agent_name} 에이전트 설정", "FAIL", f"에이전트 설정 실패: {e}")
            raise
