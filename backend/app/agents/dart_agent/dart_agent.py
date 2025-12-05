"""
dart_agent.py
DART 멀티에이전트 시스템 - 기존 단일 에이전트를 멀티에이전트 시스템으로 확장
"""

import asyncio
import time
from typing import Dict, Any, List, Optional
from datetime import datetime
from langchain_core.tools import BaseTool
from langchain.agents import create_agent
from langchain_core.prompts import PromptTemplate
from utils.logger import log_step

from agent.base_agent import BaseAgent

from utils.logger import log_step, log_agent_flow
from utils.analysis_logger import (
    start_analysis_session,
    get_current_logger,
    log_step as analysis_log_step,
)

# Langfuse 로깅 설정
try:
    from langfuse.decorators import observe, langfuse_context

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False

    def observe():
        def decorator(func):
            return func

        return decorator
from agent.dart_agent.dart_master_agent import DartMasterAgent
from agent.dart_agent.intent_classifier_agent import IntentClassifierAgent
from agent.dart_agent.financial_agent import FinancialAgent
from agent.dart_agent.governance_agent import GovernanceAgent
from agent.dart_agent.capital_change_agent import CapitalChangeAgent
from agent.dart_agent.debt_funding_agent import DebtFundingAgent
from agent.dart_agent.business_structure_agent import BusinessStructureAgent
from agent.dart_agent.overseas_business_agent import OverseasBusinessAgent
from agent.dart_agent.legal_compliance_agent import LegalComplianceAgent
from agent.dart_agent.executive_audit_agent import ExecutiveAuditAgent
from agent.dart_agent.document_analysis_agent import DocumentAnalysisAgent



# MessageRefiner는 별도 파일로 분리됨 (순환 import 방지)
from agent.dart_agent.message_refiner import MessageRefiner


# =============================================================================
# 🔧 DART 에이전트 클래스
# =============================================================================


class DartAgent(BaseAgent):
    """DART 멀티에이전트 시스템 - 기존 호환성 유지하면서 멀티에이전트 기능 제공"""

    def __init__(self, llm, mcp_servers: Dict[str, Any]):
        """DART 에이전트 초기화"""
        
        
        # DART 특화 설정

        """DART 멀티에이전트 시스템 초기화"""
        # mcp_servers를 List[Dict[str, Any]] 형식으로 변환
        if isinstance(mcp_servers, dict):
            # Dict[str, Any]를 List[Dict[str, Any]]로 변환
            mcp_servers_list = []
            for server_name, server_config in mcp_servers.items():
                if isinstance(server_config, dict):
                    # 이미 올바른 형식인 경우
                    server_config["name"] = server_name
                    mcp_servers_list.append(server_config)
                else:
                    # 단순 값인 경우 기본 형식으로 변환
                    mcp_servers_list.append(
                        {
                            "name": server_name,
                            "command": "python",
                            "args": ["-m", f"mcp_{server_name}"],
                            "env": {},
                        }
                    )
            mcp_servers = mcp_servers_list

        super().__init__(llm, mcp_servers, "DartAgent")

        # 기존 설정 유지 (호환성)
        self.dart_config = {
            "max_search_results": 10,
            "max_content_length": 8000,
            "cache_ttl": 3600,  # 1시간
            "default_year": datetime.now().year,
            "enable_multi_agent": True,  # 멀티에이전트 모드 활성화 (기존 구조 활용)
        }

        self.search_history = []
        self.report_cache = {}
        # 멀티에이전트 시스템 구성요소
        self.master_agent = None
        self.intent_classifier = None
        self.sub_agents = {}
        self._multi_agent_initialized = False
        
        # 메시지 정제 시스템 초기화
        self.message_refiner = MessageRefiner()

        # 멀티에이전트 시스템은 initialize() 메서드에서 초기화

        log_step("DartAgent 초기화", "SUCCESS", "기본 설정 완료")

    async def initialize(self):
        """DartAgent 초기화 - BaseAgent 초기화 후 멀티에이전트 시스템 초기화"""
        # BaseAgent 초기화 (MCP 매니저 등)
        await super().initialize()
        
        # 멀티에이전트 시스템 초기화 (서버 시작 시에만)
        if self.dart_config.get("enable_multi_agent", True) and not self._multi_agent_initialized:
            try:
                await self._initialize_multi_agent_system()
                log_step("DartAgent 초기화", "SUCCESS", "멀티에이전트 시스템 초기화 완료")
            except Exception as e:
                log_step("DartAgent 초기화", "WARNING", f"멀티에이전트 시스템 초기화 실패: {str(e)}")
                # 멀티에이전트 실패해도 기본 에이전트로 동작

    async def _initialize_multi_agent_system(self):
        """멀티에이전트 시스템 초기화 - agent_registry의 MCP 매니저 사용"""
        try:
            log_step("멀티에이전트 시스템 초기화", "START", "전문 에이전트들 생성 중...")

            # agent_registry에서 DART MCP 매니저 가져오기
            from agent.agent_registry import agent_registry
            
            dart_mcp_manager = agent_registry.get_mcp_manager("dart")
            if not dart_mcp_manager:
                log_step("DART MCP 매니저 없음", "ERROR", "agent_registry에서 DART MCP 매니저를 찾을 수 없음")
                raise Exception("DART MCP 매니저가 agent_registry에서 초기화되지 않았습니다")

            # agent_registry에서 초기화된 MCP 서버 설정을 사용
            mcp_servers = dart_mcp_manager.server_configs
            log_step(
                "DART MCP 매니저 확인 완료",
                "SUCCESS",
                f"agent_registry에서 초기화된 DART MCP 서버 사용: {len(mcp_servers)}개",
            )

            # 1. 마스터 에이전트 생성
            self.master_agent = DartMasterAgent(self.llm, mcp_servers)
            log_step("마스터 에이전트 생성", "SUCCESS", "DartMasterAgent 생성 완료")

            # 2. 의도 분류 에이전트 생성
            intent_classifier_db_path = None  # PostgreSQL 사용
            # 다른 에이전트들과 동일한 mcp_servers 사용 (OpenDART 서버 정보 포함)
            # 올바른 파라미터 순서: llm, checkpoint_db_path, mcp_servers
            self.intent_classifier = IntentClassifierAgent(
                llm=self.llm,
                checkpoint_db_path=intent_classifier_db_path,
                mcp_servers=mcp_servers,  # agent_registry에서 가져온 MCP 서버 사용
            )

            # IntentClassifierAgent도 다른 에이전트들과 동일하게 초기화
            try:
                await self.intent_classifier.initialize()
                log_step(
                    "IntentClassifierAgent 초기화",
                    "SUCCESS",
                    "IntentClassifierAgent MCP 연결 완료",
                )
            except Exception as init_error:
                log_step(
                    "IntentClassifierAgent 초기화",
                    "WARNING",
                    f"IntentClassifierAgent MCP 연결 실패: {str(init_error)}",
                )

            log_step(
                "의도 분류 에이전트 생성",
                "SUCCESS",
                "IntentClassifierAgent 생성 완료 (MCP 서버 포함)",
            )

            # 3. 전문 에이전트들 생성 (모든 구현된 에이전트 포함)
            self.sub_agents = {}
            successful_agents = 0
            failed_agents = 0

            # 각 에이전트를 개별적으로 생성하여 오류 추적
            agent_creation_configs = [
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

            for agent_name, agent_class in agent_creation_configs:
                try:
                    log_step(
                        "전문 에이전트 생성",
                        "START",
                        f"{agent_name} 에이전트 생성 시작",
                    )
                    agent_instance = agent_class(self.llm, mcp_servers)

                    # 각 에이전트의 BaseAgent.initialize() 호출하여 MCP 연결 설정
                    try:
                        await agent_instance.initialize()
                        log_step(
                            f"{agent_name} 에이전트 초기화",
                            "SUCCESS",
                            f"{agent_name} MCP 연결 완료",
                        )
                    except Exception as init_error:
                        log_step(
                            f"{agent_name} 에이전트 초기화",
                            "WARNING",
                            f"{agent_name} MCP 연결 실패: {str(init_error)}",
                        )
                        # 초기화 실패해도 에이전트는 생성됨

                    self.sub_agents[agent_name] = agent_instance
                    log_step(
                        "전문 에이전트 생성",
                        "SUCCESS",
                        f"{agent_name} 에이전트 생성 완료",
                    )
                    successful_agents += 1
                except Exception as e:
                    log_step(
                        "전문 에이전트 생성",
                        "ERROR",
                        f"{agent_name} 에이전트 생성 실패: {str(e)}",
                    )
                    import traceback

                    log_step(
                        "전문 에이전트 생성",
                        "ERROR",
                        f"{agent_name} 상세 오류: {traceback.format_exc()}",
                    )
                    failed_agents += 1

            log_step(
                "전문 에이전트 생성",
                "SUCCESS",
                f"생성된 에이전트: {list(self.sub_agents.keys())} (성공: {successful_agents}개, 실패: {failed_agents}개)",
            )

            # 최소 2개 이상의 에이전트가 생성되어야 시스템 작동 가능
            if successful_agents < 2:
                log_step(
                    "전문 에이전트 생성",
                    "ERROR",
                    f"성공한 에이전트가 부족합니다: {successful_agents}개 (최소 2개 필요)",
                )
                raise Exception(f"에이전트 생성 실패: {successful_agents}개만 성공 (최소 2개 필요)")

            # 4. 마스터 에이전트에 하위 에이전트들 등록
            registered_agents = 0
            for name, agent in self.sub_agents.items():
                try:
                    self.master_agent.register_sub_agent(name, agent)
                    log_step(f"{name} 에이전트 등록", "SUCCESS", f"{name} 등록 완료")
                    registered_agents += 1
                except Exception as e:
                    log_step(f"{name} 에이전트 등록", "ERROR", f"{name} 등록 실패: {str(e)}")
                    import traceback

                    log_step(
                        f"{name} 에이전트 등록",
                        "ERROR",
                        f"{name} 상세 오류: {traceback.format_exc()}",
                    )

            log_step(
                "하위 에이전트 등록",
                "SUCCESS",
                f"등록된 에이전트: {registered_agents}개 / {len(self.sub_agents)}개",
            )

            # 5. 의도 분류기를 마스터 에이전트에 등록
            try:
                self.master_agent.register_intent_classifier(self.intent_classifier)
                log_step("의도 분류기 등록", "SUCCESS", "IntentClassifierAgent 등록 완료")
            except Exception as e:
                log_step(
                    "의도 분류기 등록",
                    "ERROR",
                    f"IntentClassifierAgent 등록 실패: {str(e)}",
                )
                import traceback

                log_step("의도 분류기 등록", "ERROR", f"상세 오류: {traceback.format_exc()}")

            # 6. 멀티에이전트 시스템 초기화 완료
            log_step(
                "멀티에이전트 시스템 초기화",
                "SUCCESS",
                f"총 {len(self.sub_agents)}개 전문 에이전트 등록 완료",
            )
            self._multi_agent_initialized = True

        except Exception as e:
            log_step("멀티에이전트 시스템 초기화", "ERROR", f"초기화 실패: {str(e)}")
            import traceback

            log_step(
                "멀티에이전트 시스템 초기화",
                "ERROR",
                f"상세 오류: {traceback.format_exc()}",
            )
            self._multi_agent_initialized = False
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
            from agent.dart_agent.utils.memory_manager import DartMemoryManager
            from utils.postgresql_store import PostgreSQLStore
            
            # PostgreSQL Store 초기화
            store = PostgreSQLStore()
            
            # 메모리 매니저 초기화
            self.memory_manager = DartMemoryManager(
                checkpointer=self.checkpointer,
                store=store
            )
            
            # 스트리밍 메모리 핸들러 초기화
            from agent.dart_agent.utils.streaming_memory import StreamingMemoryHandler
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

