"""
dart_agent.py
DART 멀티에이전트 시스템 - DartMasterAgent.coordinate_analysis_stream() 기반 오케스트레이션
"""

import asyncio
import time
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import BaseTool
from langchain_core.prompts import PromptTemplate

# Agent Portal imports
from .base import DartBaseAgent, LiteLLMAdapter
from .dart_types import (
    AnalysisContext,
    AgentResult,
    RiskLevel,
    AnalysisScope,
    AnalysisDomain,
    AnalysisDepth,
    IntentClassificationResult,
)
from .message_refiner import MessageRefiner
from .mcp_client import MCPTool, get_opendart_mcp_client
from .metrics import observe, record_counter, start_dart_span

logger = logging.getLogger(__name__)

def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수"""
    logger.info(f"[{step_name}] {status}: {message}")

def log_agent_flow(agent_name: str, action: str, step: int, message: str):
    """에이전트 플로우 로깅"""
    logger.info(f"[{agent_name}] Step {step} - {action}: {message}")

# observe 데코레이터는 metrics.py에서 import

# 멀티에이전트 시스템 컴포넌트 (lazy import to avoid circular imports)
from .dart_master_agent import DartMasterAgent
from .intent_classifier_agent import IntentClassifierAgent
from .financial_agent import FinancialAgent
from .governance_agent import GovernanceAgent
from .capital_change_agent import CapitalChangeAgent
from .debt_funding_agent import DebtFundingAgent
from .business_structure_agent import BusinessStructureAgent
from .overseas_business_agent import OverseasBusinessAgent
from .legal_compliance_agent import LegalComplianceAgent
from .executive_audit_agent import ExecutiveAuditAgent
from .document_analysis_agent import DocumentAnalysisAgent


# =============================================================================
# 🔧 DART 에이전트 클래스 (멀티에이전트 오케스트레이션)
# =============================================================================


class DartAgent(DartBaseAgent):
    """DART 멀티에이전트 시스템 - DartMasterAgent.coordinate_analysis_stream() 기반"""

    def __init__(self, model: str = "qwen-235b"):
        """DART 에이전트 초기화 (Agent Portal 구조)"""
        # OTEL 초기화 (DART 에이전트용)
        try:
            from app.telemetry.otel import init_telemetry
            init_telemetry(service_name="agent-dart")
            log_step("DartAgent OTEL 초기화", "SUCCESS", "OpenTelemetry 초기화 완료")
        except Exception as e:
            log_step("DartAgent OTEL 초기화", "WARNING", f"OpenTelemetry 초기화 실패: {e}")
        
        super().__init__(
            agent_name="DartAgent",
            model=model,
            max_iterations=15  # 멀티에이전트 조정에 필요
        )
        
        # LLM 어댑터
        self.llm = LiteLLMAdapter(model)
        self.model = model
        
        # DART 특화 설정
        self.dart_config = {
            "max_search_results": 10,
            "max_content_length": 8000,
            "cache_ttl": 3600,
            "default_year": datetime.now().year,
            "enable_multi_agent": True,
        }

        self.search_history = []
        self.report_cache = {}
        
        # 멀티에이전트 시스템 구성요소
        self.master_agent: Optional[DartMasterAgent] = None
        self.intent_classifier: Optional[IntentClassifierAgent] = None
        self.sub_agents: Dict[str, DartBaseAgent] = {}
        self._multi_agent_initialized = False
        
        # 메시지 정제 시스템
        self.message_refiner = MessageRefiner()

        log_step("DartAgent 초기화", "SUCCESS", "기본 설정 완료")

    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """DartAgent 도구 필터링 - 모든 도구 사용 (멀티에이전트가 개별 필터링)"""
        # 마스터 에이전트가 개별 에이전트에 도구를 배분하므로 여기서는 모든 도구 반환
        return tools
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return """당신은 DART 공시 시스템의 멀티에이전트 분석 시스템입니다.
사용자의 질문을 분석하고, 적절한 전문 에이전트를 선택하여 분석을 수행합니다.
분석 결과를 종합하여 통찰력 있는 보고서를 제공합니다."""

    async def initialize(self):
        """DartAgent 초기화 - DartBaseAgent 초기화 후 멀티에이전트 시스템 초기화"""
        print(f"[DEBUG] DartAgent.initialize() 호출됨: _initialized={self._initialized}, _multi_agent_initialized={self._multi_agent_initialized}")
        logger.info(f"[DEBUG] DartAgent.initialize() 호출됨: _initialized={self._initialized}, _multi_agent_initialized={self._multi_agent_initialized}")
        
        # DartBaseAgent 초기화 (MCP 클라이언트 등) - _initialized가 True여도 재초기화 가능
        if not self._initialized:
            await super().initialize()
        
        # 멀티에이전트 시스템 초기화 - _multi_agent_initialized가 False인 경우 항상 초기화 시도
        enable_multi = self.dart_config.get("enable_multi_agent", True)
        print(f"[DEBUG] 멀티에이전트 조건 체크: enable_multi={enable_multi}, _multi_agent_initialized={self._multi_agent_initialized}")
        logger.info(f"[DEBUG] 멀티에이전트 조건 체크: enable_multi={enable_multi}, _multi_agent_initialized={self._multi_agent_initialized}")
        
        if enable_multi and not self._multi_agent_initialized:
            try:
                await self._initialize_multi_agent_system()
                self._multi_agent_initialized = True
                log_step("DartAgent 초기화", "SUCCESS", "멀티에이전트 시스템 초기화 완료")
            except Exception as e:
                log_step("DartAgent 초기화", "WARNING", f"멀티에이전트 시스템 초기화 실패: {str(e)}")
                # 멀티에이전트 실패해도 기본 에이전트로 동작

    async def _initialize_multi_agent_system(self):
        """멀티에이전트 시스템 초기화 - Agent Portal 구조"""
        try:
            print(f"[DEBUG] _initialize_multi_agent_system() 호출됨")
            logger.info("[DEBUG] _initialize_multi_agent_system() 시작")
            log_step("멀티에이전트 시스템 초기화", "START", "전문 에이전트들 생성 중...")
            
            # MCP 클라이언트 연결 확인
            mcp_client = await get_opendart_mcp_client()
            if not mcp_client.is_connected:
                await mcp_client.connect()
            
            tools = mcp_client.get_tools()
            log_step("MCP 클라이언트", "SUCCESS", f"연결됨: {len(tools)}개 도구")
            
            # 1. 마스터 에이전트 생성 (Agent Portal 구조)
            self.master_agent = DartMasterAgent(model=self.model)
            await self.master_agent.initialize()
            log_step("마스터 에이전트 생성", "SUCCESS", "DartMasterAgent 생성 및 초기화 완료")
            
            # 2. 의도 분류 에이전트 생성
            self.intent_classifier = IntentClassifierAgent(model=self.model)
            await self.intent_classifier.initialize()
            log_step("의도 분류 에이전트", "SUCCESS", "IntentClassifierAgent 생성 및 초기화 완료")
            
            # 3. 마스터 에이전트에 의도 분류기 등록
            self.master_agent.register_intent_classifier(self.intent_classifier)
            
            # 4. 전문 에이전트들 생성
            agent_configs = [
                ("financial", FinancialAgent),
                ("governance", GovernanceAgent),
                ("capital_change", CapitalChangeAgent),
                ("debt_funding", DebtFundingAgent),
                ("business_structure", BusinessStructureAgent),
                ("overseas_business", OverseasBusinessAgent),
                ("legal_risk", LegalComplianceAgent),
                ("executive_audit", ExecutiveAuditAgent),
                ("document_analysis", DocumentAnalysisAgent),
            ]
            
            for agent_name, agent_class in agent_configs:
                try:
                    agent_instance = agent_class(model=self.model)
                    await agent_instance.initialize()
                    self.sub_agents[agent_name] = agent_instance
                    self.master_agent.register_sub_agent(agent_name, agent_instance)
                    log_step(f"{agent_name} 에이전트", "SUCCESS", "생성 및 등록 완료")
                except Exception as e:
                    log_step(f"{agent_name} 에이전트", "WARNING", f"생성 실패: {str(e)}")
            
            log_step("멀티에이전트 시스템 초기화", "SUCCESS", f"마스터 + {len(self.sub_agents)}개 전문 에이전트 준비 완료")
            
        except Exception as e:
            import traceback
            log_step("멀티에이전트 시스템 초기화", "ERROR", f"초기화 실패: {str(e)}")
            log_step("멀티에이전트 시스템 초기화", "ERROR", f"상세 오류: {traceback.format_exc()}")
            raise

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
                prompt=domain_prompt,
                checkpointer=self.checkpointer
            )
            
            log_step(f"{self.agent_name} 에이전트 설정", "SUCCESS", "create_agent 생성 완료")
            
        except Exception as e:
            log_step(f"{self.agent_name} 에이전트 설정", "FAIL", f"에이전트 설정 실패: {e}")
            raise

    async def _filter_tools_for_agent(self, tools: List[BaseTool]) -> List[BaseTool]:
        """DART 에이전트용 도구 필터링 - 81개 모든 도구 활용"""
        if self.dart_config.get("enable_multi_agent", True):
            # 멀티에이전트 모드에서는 모든 DART 도구 허용
            dart_tools = []
            all_tool_names = []

            # 모든 OpenDART 도구 이름 패턴 (81개 전체 포함)
            dart_tool_patterns = [
                "get_accounting_auditor_opinion",
                "get_asset_transfer",
                "get_audit_service_contract",
                "get_bankruptcy",
                "get_bond_with_warrant",
                "get_business_acquisition",
                "get_business_suspension",
                "get_business_transfer",
                "get_capital_reduction",
                "get_commercial_paper_outstanding",
                "get_conditional_capital_securities_outstanding",
                "get_convertible_bond",
                "get_corporate_bond_outstanding",
                "get_corporation_code_by_name",
                "get_corporation_info",
                "get_creditor_management_termination",
                "get_creditor_management",
                "get_debt_securities_issued",
                "get_debt",
                "get_depository_receipt",
                "get_disclosure_list",
                "get_dissolution",
                "get_division_merger",
                "get_division_report",
                "get_division",
                "get_employee_info",
                "get_equity",
                "get_exchangeable_bond",
                "get_executive_compensation_approved",
                "get_executive_compensation_by_type",
                "get_executive_info",
                "get_executive_trading",
                "get_foreign_delisting_decision",
                "get_foreign_delisting",
                "get_foreign_listing_decision",
                "get_foreign_listing",
                "get_free_capital_increase",
                "get_hybrid_securities_outstanding",
                "get_individual_compensation_amount",
                "get_individual_compensation",
                "get_investment_in_other_corp",
                "get_lawsuit",
                "get_major_holder_changes",
                "get_major_shareholder_changes",
                "get_major_shareholder",
                "get_merger_report",
                "get_merger",
                "get_minority_shareholder",
                "get_multi_acnt",
                "get_multi_index",
                "get_non_audit_service_contract",
                "get_other_corp_stock_acquisition",
                "get_other_corp_stock_transfer",
                "get_outside_director_status",
                "get_paid_free_capital_increase",
                "get_paid_in_capital_increase",
                "get_private_capital_usage",
                "get_public_capital_usage",
                "get_rehabilitation",
                "get_short_term_bond_outstanding",
                "get_single_acc",
                "get_single_acnt",
                "get_single_index",
                "get_stock_exchange_report",
                "get_stock_exchange",
                "get_stock_increase_decrease",
                "get_stock_related_bond_acquisition",
                "get_stock_related_bond_transfer",
                "get_stock_total",
                "get_tangible_asset_acquisition",
                "get_tangible_asset_transfer",
                "get_total_compensation",
                "get_treasury_stock_acquisition",
                "get_treasury_stock_disposal",
                "get_treasury_stock_trust_contract",
                "get_treasury_stock_trust_termination",
                "get_treasury_stock",
                "get_unregistered_exec_compensation",
                "get_write_down_bond",
            ]

            for tool in tools:
                tool_name = getattr(tool, "name", "")
                all_tool_names.append(tool_name)

                # 모든 OpenDART 도구 포함 (정확한 이름 매칭)
                if tool_name in dart_tool_patterns:
                    dart_tools.append(tool)

            log_step(
                "DART 멀티에이전트 도구 필터링",
                "INFO",
                f"전체 도구: {len(all_tool_names)}개",
            )
            log_step(
                "DART 멀티에이전트 도구 필터링",
                "SUCCESS",
                f"DART 관련 도구 {len(dart_tools)}개 필터링됨",
            )
            return dart_tools
        else:
            # 기존 단일 에이전트 모드
            dart_tools = []
            for tool in tools:
                tool_name = getattr(tool, "name", "")

                # 기존 제한된 도구들만 필터링
                if any(
                    keyword in tool_name.lower()
                    for keyword in [
                        "get_single_acnt",
                        "get_corporation_code_by_name",
                        "get_disclosure_list",
                        "get_corporation_info",
                        "get_multi_acnt",
                        "get_multi_index",
                        "get_major_holder_changes",
                        "get_executive_trading",
                        "get_executive_info",
                        "get_employee_info",
                    ]
                ):
                    dart_tools.append(tool)

            log_step(
                "DART 단일 에이전트 도구 필터링",
                "SUCCESS",
                f"DART 관련 도구 {len(dart_tools)}개 필터링됨",
            )
            return dart_tools

    async def process_chat_request_stream(self, message: str, thread_id: Optional[str] = None, user_email: Optional[str] = None):
        """스트리밍 채팅 요청 처리 - 멀티에이전트 시스템 우선 사용"""
        try:
            print(
                f"🔥🔥🔥 DartAgent.process_chat_request_stream 호출됨! 메시지: {message[:50] if message else 'None'}"
            )
            log_step(
                "🚀 DartAgent.process_chat_request_stream 호출됨",
                "START",
                f"메시지: {message[:100]}..., thread_id: {thread_id}",
            )

            # 🔍 분석 세션 시작
            analysis_logger = start_analysis_session(message)
            print(f"🔍 분석 세션 시작: {analysis_logger.session_id}")

            # 멀티에이전트 모드 상태 확인
            enable_multi_agent = self.dart_config.get("enable_multi_agent", True)
            multi_agent_initialized = getattr(self, "_multi_agent_initialized", False)

            print(
                f"🔥🔥🔥 멀티에이전트 상태: enable_multi_agent={enable_multi_agent}, _multi_agent_initialized={multi_agent_initialized}"
            )
            log_step(
                "🔍 멀티에이전트 상태 확인",
                "INFO",
                f"enable_multi_agent: {enable_multi_agent}, _multi_agent_initialized: {multi_agent_initialized}",
            )

            # 마스터 에이전트 존재 여부도 확인
            has_master_agent = hasattr(self, "master_agent") and self.master_agent is not None
            print(f"🔥🔥🔥 마스터 에이전트 존재: {has_master_agent}")
            log_step(
                "🔍 마스터 에이전트 확인",
                "INFO",
                f"has_master_agent: {has_master_agent}",
            )

            # 멀티에이전트 시스템이 초기화되지 않은 경우 경고 메시지만 출력
            if enable_multi_agent and not multi_agent_initialized:
                log_step(
                    "멀티에이전트 시스템 미초기화",
                    "WARNING",
                    "멀티에이전트 시스템이 초기화되지 않았습니다. 기본 모드로 동작합니다.",
                )

            # 멀티에이전트 모드가 활성화된 경우
            print(
                f"🔥🔥🔥 DartAgent 멀티에이전트 조건 확인: enable_multi_agent={enable_multi_agent}, multi_agent_initialized={multi_agent_initialized}"
            )
            if enable_multi_agent and multi_agent_initialized:
                print(f"🔥🔥🔥 DartAgent 멀티에이전트 모드 진입!")
                log_step(
                    "DART 멀티에이전트 스트리밍 모드",
                    "START",
                    f"질문: {message[:50]}...",
                )

                try:
                    # 마스터 에이전트 존재 확인
                    print(
                        f"🔥🔥🔥 DartAgent 마스터 에이전트 확인: hasattr={hasattr(self, 'master_agent')}, master_agent={getattr(self, 'master_agent', None)}"
                    )
                    if not hasattr(self, "master_agent") or not self.master_agent:
                        print(f"🔥🔥🔥 DartAgent 마스터 에이전트 없음!")
                        log_step(
                            "마스터 에이전트 없음",
                            "ERROR",
                            "master_agent가 초기화되지 않음",
                        )
                        raise Exception("마스터 에이전트가 초기화되지 않았습니다")

                    print(
                        f"🔥🔥🔥 DartAgent 마스터 에이전트 존재 확인됨: {type(self.master_agent)}"
                    )
                    log_step(
                        "마스터 에이전트 확인",
                        "SUCCESS",
                        f"master_agent 타입: {type(self.master_agent)}",
                    )

                    # DartMasterAgent의 coordinate_analysis 호출하여 멀티에이전트 플로우 실행
                    print(f"🔥🔥🔥 DartAgent 마스터 에이전트 호출 준비!")
                    log_step(
                        "마스터 에이전트 호출",
                        "INFO",
                        "DartMasterAgent.coordinate_analysis 호출 시작 (멀티에이전트 플로우)",
                    )

                    # 🔍 마스터 에이전트 실행 로깅
                    analysis_logger = get_current_logger()
                    if analysis_logger:
                        analysis_logger.log_agent_execution(
                            "DartMasterAgent", {"message": message}, {}
                        )

                    # Phase 1: 마스터 에이전트 전략 표시 + BaseAgent 표준 스트리밍 결합

                    # 1단계: 마스터 에이전트 전략 과정 스트리밍
                    print(f"🔥🔥🔥 DartAgent coordinate_analysis_stream 호출 직전!")
                    log_step(
                        "DartAgent 스트리밍",
                        "INFO",
                        "coordinate_analysis_stream 호출 직전",
                    )

                    async for strategy_chunk in self.master_agent.coordinate_analysis_stream(
                        message, thread_id=thread_id, user_email=user_email
                    ):
                        print(f"🔥🔥🔥 DartAgent strategy_chunk 수신: {strategy_chunk}")
                        log_step(
                            "DartAgent 스트리밍",
                            "INFO",
                            f"strategy_chunk 수신: {strategy_chunk.get('type', 'unknown')}",
                        )
                        yield strategy_chunk

                        # 전략 과정이 완료되면 분석 완료
                        if strategy_chunk.get("type") == "content":
                            print(f"🔥🔥🔥 DartAgent content 청크 감지, 분석 완료")
                            log_step(
                                "마스터 에이전트 완료",
                                "SUCCESS",
                                "통합 분석 완료 - content 청크 수신",
                            )
                            break


                    # 2단계: 마스터 에이전트가 모든 분석을 완료했으므로 BaseAgent 스트리밍은 불필요
                    # (마스터 에이전트에서 이미 통합 분석이 완료됨)

                    # 마스터 에이전트에서 이미 완전한 분석이 완료됨
                    log_step(
                        "멀티에이전트 분석 완료",
                        "SUCCESS", 
                        "마스터 에이전트가 모든 분석을 완료함"
                    )

                    log_step(
                        "마스터 에이전트 스트리밍 완료",
                        "SUCCESS",
                        "전략+도구 스트리밍 완료",
                    )

                except Exception as e:
                    log_step("마스터 에이전트 오류", "ERROR", f"오류 발생: {str(e)}")
                    import traceback

                    log_step(
                        "마스터 에이전트 상세 오류",
                        "ERROR",
                        f"스택 트레이스: {traceback.format_exc()}",
                    )

                    # 마스터 에이전트 실패 시 기본 에이전트로 폴백
                    log_step("폴백 모드", "INFO", "기본 DART 에이전트로 폴백")
                    async for chunk in super().process_chat_request_stream(message, thread_id, user_email):
                        yield chunk
                    return
            else:
                # 멀티에이전트 모드가 비활성화된 경우 기본 모드 사용
                log_step(
                    "DART 기본 스트리밍 모드",
                    "INFO",
                    f"멀티에이전트 비활성화 (enable_multi_agent: {enable_multi_agent}, initialized: {multi_agent_initialized}), 기본 모드 사용",
                )
                async for chunk in super().process_chat_request_stream(message, thread_id, user_email):
                    yield chunk
                return

        except Exception as e:
            log_step("DART 스트리밍 에이전트 오류", "ERROR", f"전체 처리 오류: {str(e)}")
            import traceback

            log_step(
                "DART 스트리밍 에이전트 상세 오류",
                "ERROR",
                f"스택 트레이스: {traceback.format_exc()}",
            )

            # 오류 발생 시 에러 청크 반환
            yield {
                "type": "error",
                "content": f"DART 에이전트 처리 중 오류가 발생했습니다: {str(e)}",
            }

    # =============================================================================
    # 🧠 메모리 관리 메서드 (StateGraph 기반)
    # =============================================================================
    
    def _init_memory_manager(self):
        """메모리 매니저 초기화"""
        try:
            from app.agents.dart_agent.utils.memory_manager import DartMemoryManager
            
            # PostgreSQL Store 대체 - 없으면 None 사용
            try:
                from utils.postgresql_store import PostgreSQLStore
                store = PostgreSQLStore()
            except ImportError:
                log_step("메모리 매니저 초기화", "WARNING", "PostgreSQLStore 사용 불가, None으로 대체")
                store = None
            
            # 메모리 매니저 초기화
            self.memory_manager = DartMemoryManager(
                checkpointer=self.checkpointer,
                store=store
            )
            
            # 스트리밍 메모리 핸들러 초기화
            from app.agents.dart_agent.utils.streaming_memory import StreamingMemoryHandler
            self.streaming_memory_handler = StreamingMemoryHandler(self.memory_manager)
            
            log_step("메모리 매니저 초기화", "SUCCESS", "StateGraph 기반 메모리 시스템 활성화")
            
        except Exception as e:
            log_step("메모리 매니저 초기화", "ERROR", f"초기화 실패: {e}")
            self.memory_manager = None
            self.streaming_memory_handler = None
    
    async def _ensure_ns(self, thread_id: str, checkpoint_ns: str = "mem_main"):
        """메모리 네임스페이스 확인/생성"""
        try:
            if not self.memory_manager:
                self._init_memory_manager()
            
            if not self.memory_manager:
                log_step("메모리 네임스페이스", "WARNING", "메모리 매니저가 없음")
                return
            
            # 네임스페이스 설정
            config = {"configurable": {"thread_id": thread_id, "checkpoint_ns": checkpoint_ns}}
            
            # 체크포인터에서 현재 상태 확인
            checkpoint = self.checkpointer.get(config)
            if not checkpoint:
                log_step("메모리 네임스페이스", "INFO", f"새 네임스페이스 생성: {checkpoint_ns}")
            
        except Exception as e:
            log_step("메모리 네임스페이스", "ERROR", f"네임스페이스 설정 실패: {e}")
    
    async def process_chat_request_stream_with_memory(self, message: str, thread_id: str = None, user_email: str = None):
        """메모리 관리 기능이 포함된 스트리밍 처리"""
        try:
            # 메모리 매니저 초기화 (필요시)
            if not hasattr(self, 'memory_manager') or not self.memory_manager:
                self._init_memory_manager()
            
            # 메모리 네임스페이스 확인
            if hasattr(self, '_ensure_ns'):
                await self._ensure_ns(thread_id=thread_id, checkpoint_ns="mem_main")
            
            # 기존 스트리밍 처리 호출
            async for chunk in self.process_chat_request_stream(message, thread_id, user_email):
                # 스트리밍 메모리 핸들러로 청크 처리
                if hasattr(self, 'streaming_memory_handler') and self.streaming_memory_handler:
                    processed_chunk = await self.streaming_memory_handler.handle_streaming_chunk(
                        chunk, "dart_agent", thread_id or "default"
                    )
                    yield processed_chunk
                else:
                    yield chunk
            
            # 스트리밍 세션 완료 처리
            if hasattr(self, 'streaming_memory_handler') and self.streaming_memory_handler:
                final_result = {
                    "corp_code": "unknown",
                    "analysis_completed": True,
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S")
                }
                await self.streaming_memory_handler.finalize_streaming_session(thread_id or "default", final_result)
            
        except Exception as e:
            log_step("메모리 스트리밍 처리", "ERROR", f"메모리 스트리밍 처리 실패: {e}")
            # 오류 발생 시 기본 스트리밍으로 폴백
            async for chunk in self.process_chat_request_stream(message, thread_id, user_email):
                yield chunk

    # =============================================================================
    # 🌐 routes/dart.py 호환 인터페이스
    # =============================================================================
    
    async def analyze(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DART 분석 실행 (비스트리밍) - routes/dart.py 호환 인터페이스
        
        DartMasterAgent.coordinate_analysis_stream()을 통해 멀티에이전트 오케스트레이션 수행
        스트림 결과를 수집하여 최종 결과 반환
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            
        Returns:
            분석 결과 딕셔너리
        """
        start_time = time.time()
        
        # 초기화 (필요시)
        if not self._initialized:
            await self.initialize()
        
        # 멀티에이전트 시스템 사용 가능 여부 확인
        if not self._multi_agent_initialized or not self.master_agent:
            raise RuntimeError("멀티에이전트 시스템이 초기화되지 않았습니다. master_agent가 없습니다.")
        
        log_step("analyze", "INFO", "멀티에이전트 모드로 실행 (비스트리밍)")
        
        # DartMasterAgent.coordinate_analysis_stream() 호출하여 결과 수집
        final_answer = ""
        intent_result = None
        tool_calls = []
        
        try:
            async for chunk in self.master_agent.coordinate_analysis_stream(
                user_question=question,
                thread_id=session_id,
                user_email=None,
                parent_carrier=None
            ):
                chunk_type = chunk.get("type", "")
                
                if chunk_type == "start":
                    log_step("analyze", "INFO", "분석 시작")
                elif chunk_type == "progress":
                    log_step("analyze", "INFO", f"진행 중: {chunk.get('content', '')[:100]}")
                elif chunk_type == "answer" or chunk_type == "content":
                    # content 타입이 최종 답변일 수 있음
                    content = chunk.get("content", chunk.get("answer", ""))
                    if content and not final_answer:
                        final_answer = content
                elif chunk_type == "complete":
                    # complete 타입에서 최종 답변 추출
                    if "content" in chunk:
                        final_answer = chunk.get("content", final_answer)
                    elif "answer" in chunk:
                        final_answer = chunk.get("answer", final_answer)
                    # intent와 tool_calls는 별도로 수집 필요 (현재는 coordinate_analysis_stream에서 제공하지 않음)
                elif chunk_type == "error":
                    error_msg = chunk.get("content", chunk.get("error", "알 수 없는 오류"))
                    log_step("analyze", "ERROR", f"오류 발생: {error_msg}")
                    raise Exception(error_msg)
        except Exception as e:
            log_step("analyze", "ERROR", f"분석 중 오류: {str(e)}")
            raise
        
        total_latency = (time.time() - start_time) * 1000
        
        result = {
            "answer": final_answer,
            "intent": intent_result or {},
            "tool_calls": tool_calls,
            "tokens": {},  # TODO: 토큰 정보 수집
            "total_latency_ms": total_latency
        }
        
        log_step("analyze", "SUCCESS", f"분석 완료: {len(final_answer)}자, {total_latency:.0f}ms")
        
        return result
    
    async def analyze_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        parent_carrier: Optional[Dict[str, str]] = None
    ):
        """
        DART 분석 실행 (스트리밍) - routes/dart.py 호환 인터페이스
        
        DartMasterAgent.coordinate_analysis_stream()을 통해 멀티에이전트 오케스트레이션 수행
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            parent_carrier: 부모 OTEL context carrier (trace_id 계승용)
            
        Yields:
            SSE 스트림 이벤트
        """
        start_time = time.time()
        
        # OTEL span 생성 (parent_carrier로 trace_id 계승)
        with start_dart_span(
            "dart.analyze_stream",
            {"question_length": len(question), "session_id": session_id or ""},
            parent_carrier
        ) as span:
            # 현재 span의 context를 carrier로 추출
            current_carrier: Dict[str, str] = {}
            try:
                inject_context_to_carrier(current_carrier)
            except Exception:
                pass
            
            def _record_otel_event(event_type: str, payload: Dict[str, Any]):
                """OTEL span에 이벤트 기록"""
                try:
                    if span is None or not hasattr(span, "add_event"):
                        return
                    attrs = {
                        "dart.event_type": event_type,
                        "dart.session_id": session_id or "",
                    }
                    for key, value in payload.items():
                        if key in ("event", "type"):
                            continue
                        try:
                            if isinstance(value, (dict, list)):
                                import json
                                attrs[f"dart.{key}"] = json.dumps(value, ensure_ascii=False, default=str)[:1000]
                            else:
                                attrs[f"dart.{key}"] = str(value)[:500]
                        except Exception:
                            pass
                    span.add_event(f"sse.{event_type}", attributes=attrs)
                    record_counter("dart_stream_events_total", {"event": event_type})
                except Exception:
                    pass
            
            try:
                # 시작 이벤트
                _record_otel_event("analyzing", {"message": "질문을 분석하고 있습니다..."})
                yield {"event": "analyzing", "message": "질문을 분석하고 있습니다..."}
                
                # 초기화 (필요시) - _initialized 또는 _multi_agent_initialized가 False인 경우
                if not self._initialized or not self._multi_agent_initialized:
                    await self.initialize()
                
                # 멀티에이전트 시스템 사용 가능 여부 확인
                if self._multi_agent_initialized and self.master_agent:
                    
                    # DartMasterAgent.coordinate_analysis_stream() 호출
                    async for chunk in self.master_agent.coordinate_analysis_stream(
                        user_question=question,
                        thread_id=session_id,
                        user_email=None,
                        parent_carrier=current_carrier
                    ):
                        # chunk type을 event로 매핑
                        event_type = chunk.get("type", "message")
                        print(f"📍📍📍 DartAgent received chunk: type={event_type}, keys={list(chunk.keys())}")
                        if event_type == "tool_result":
                            print(f"📍📍📍 tool_result chunk details: {chunk}")
                        event_data = {
                            "event": event_type,
                            "session_id": session_id,
                        }
                        
                        # content를 적절한 필드로 매핑
                        if "content" in chunk:
                            if event_type == "error":
                                event_data["error"] = chunk["content"]
                            elif event_type in ("answer", "content", "complete", "start", "progress", "end", "tool_result", "stream_chunk"):
                                event_data["content"] = chunk["content"]
                            else:
                                event_data["message"] = chunk["content"]
                        
                        # agent_results 타입 처리: 각 에이전트의 응답을 표시
                        if event_type == "agent_results":
                            results = chunk.get("results", [])
                            for result in results:
                                # AgentResult 객체 또는 딕셔너리 처리
                                agent_response_content = None
                                agent_name = "알 수 없는 에이전트"
                                
                                if isinstance(result, dict):
                                    agent_name = result.get("agent_name", "알 수 없는 에이전트")
                                    agent_response_content = result.get("response") or result.get("llm_response")
                                    if not agent_response_content and result.get("key_findings"):
                                        agent_response_content = "\n".join(result.get("key_findings", []))
                                elif hasattr(result, "supporting_data") and result.supporting_data:
                                    agent_name = getattr(result, "agent_name", "알 수 없는 에이전트")
                                    agent_response_content = result.supporting_data.get("llm_response")
                                if not agent_response_content and hasattr(result, "key_findings") and result.key_findings:
                                    agent_name = getattr(result, "agent_name", "알 수 없는 에이전트")
                                    agent_response_content = "\n".join(result.key_findings)
                                
                                if agent_response_content:
                                    # 각 에이전트의 응답을 별도 이벤트로 yield
                                    agent_response_event = {
                                        "event": "agent_response",
                                        "agent_name": agent_name,
                                        "content": agent_response_content,
                                        "session_id": session_id,
                                    }
                                    _record_otel_event("agent_response", agent_response_event)
                                    yield agent_response_event
                        
                        # 기타 필드 복사
                        for key, value in chunk.items():
                            if key not in ("type", "content"):
                                event_data[key] = value
                        
                        # 디버깅: tool_result 이벤트 로깅
                        if event_type == "tool_result":
                            print(f"🔧 tool_result event: tool_name={event_data.get('tool_name')}, chunk_keys={list(chunk.keys())}")
                        
                        _record_otel_event(event_type, event_data)
                        yield event_data
                        
                        # 완료 이벤트 감지
                        if event_type in ("end", "complete"):
                            break
                else:
                    # 기본 모드로 폴백
                    log_step("analyze_stream", "WARNING", "멀티에이전트 미초기화, 기본 모드로 실행")
                    
                    # 기본 DartBaseAgent의 run_stream 사용
                    async for event in self.run_stream(question, session_id, current_carrier):
                        event_type = event.get("event", "message")
                        _record_otel_event(event_type, event)
                        yield event
                
                # 완료 이벤트
                total_latency = (time.time() - start_time) * 1000
                complete_event = {
                    "event": "complete",
                    "total_latency_ms": total_latency,
                }
                _record_otel_event("complete", complete_event)
                yield complete_event
                
            except Exception as e:
                logger.error(f"analyze_stream error: {e}", exc_info=True)
                error_event = {"event": "error", "error": str(e)}
                _record_otel_event("error", error_event)
                yield error_event
                
                complete_event = {
                    "event": "complete",
                    "total_latency_ms": (time.time() - start_time) * 1000,
                    "error": str(e)
                }
                _record_otel_event("complete", complete_event)
                yield complete_event


# =============================================================================
# 싱글톤 팩토리 함수
# =============================================================================

_dart_agent: Optional[DartAgent] = None


def get_dart_agent(model: str = "qwen-235b") -> DartAgent:
    """DART 에이전트 싱글톤 반환"""
    global _dart_agent
    if _dart_agent is None:
        _dart_agent = DartAgent(model=model)
    return _dart_agent

