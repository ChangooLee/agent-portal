"""
intent_classifier_agent.py
사용자 질문의 의도를 분류하여 적절한 전문 에이전트를 선택하는 분류기
"""

import re
import logging
from typing import Dict, Any, List, AsyncGenerator, Optional
from datetime import datetime
from langchain_core.messages import SystemMessage, HumanMessage

# Agent Portal imports
from .base import DartBaseAgent, LiteLLMAdapter
from .dart_types import (
    IntentClassificationResult,
    AnalysisScope,
    AnalysisDomain,
    AnalysisDepth,
)
from .message_refiner import MessageRefiner
from .mcp_client import MCPTool, get_opendart_mcp_client
from .metrics import start_dart_span, record_counter, inject_context_to_carrier

logger = logging.getLogger(__name__)

def log_step(step_name: str, status: str, message: str):
    """로깅 헬퍼 함수 (agent-platform 호환)"""
    logger.info(f"[{step_name}] {status}: {message}")

def log_agent_flow(agent_name: str, action: str, step: int, message: str):
    """에이전트 플로우 로깅 (agent-platform 호환)"""
    logger.info(f"[{agent_name}] Step {step} - {action}: {message}")

# Langfuse 데코레이터 (선택적)
def observe():
    def decorator(func):
        return func
    return decorator


# =============================================================================
# 🧠 의도 분류 에이전트 (Agent Portal 버전)
# =============================================================================


class IntentClassifierAgent(DartBaseAgent):
    """사용자 질문 의도 분류 전문 에이전트 (Agent Portal 마이그레이션)"""
    
    def __init__(self, model: str = "qwen-235b"):
        """분류기 초기화 (Agent Portal 구조)"""
        super().__init__(
            agent_name="IntentClassifierAgent",
            model=model,
            max_iterations=3  # 의도 분류는 간단한 작업
        )
        
        # LLM 어댑터 (LiteLLM 기반)
        self.llm = LiteLLMAdapter(model)
        
        # 분류 패턴 정의
        self._init_classification_patterns()
        
        # 메시지 정제 시스템 초기화
        self.message_refiner = MessageRefiner()
        
        # 메시지 생성기는 간소화 (정적 메시지 사용)
        self.message_generator = self._create_simple_message_generator()
        
        log_step("IntentClassifierAgent 초기화", "SUCCESS", "의도 분류 패턴 로드 완료")
    
    def _create_simple_message_generator(self):
        """간단한 메시지 생성기 생성"""
        class SimpleMessageGenerator:
            async def generate_error_message(self, error_type: str, context: dict = None):
                error_messages = {
                    "company_name_extraction_failed": "기업명을 추출하지 못했습니다. 기업명을 명확하게 입력해주세요.",
                    "multi_company_lookup_failed": "일부 기업 정보를 찾지 못했습니다.",
                    "corp_code_lookup_failed": "기업 코드를 찾지 못했습니다. 기업명을 확인해주세요.",
                    "corp_code_extraction_failed": "기업 코드 추출에 실패했습니다.",
                    "intent_classification_error": "의도 분류 중 오류가 발생했습니다. 다시 시도해주세요.",
                }
                return error_messages.get(error_type, f"오류가 발생했습니다: {error_type}")
            
            async def generate_progress_message(self, action: str, context: dict = None):
                return f"{action} 진행 중..."
        
        return SimpleMessageGenerator()
    
    async def initialize(self):
        """IntentClassifierAgent 초기화 (Agent Portal 구조)"""
        if self._initialized:
            return
            
        logger.info("IntentClassifierAgent 초기화 시작")
        
        # DartBaseAgent의 initialize() 호출
        await super().initialize()
        
        logger.info(f"IntentClassifierAgent 초기화 완료: {len(self.filtered_tools)}개 도구")

    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """IntentClassifierAgent에서 사용할 도구 필터링 - 기업 정보 수집 도구들"""
        # 기업 정보 수집을 위한 도구들
        target_tools = {
            "get_corporation_code_by_name",  # 기업명으로 기업코드 찾기
            "get_corporation_info",  # 기업 기본정보 조회
            "get_disclosure_list",  # 공시 목록 조회
        }

        filtered = [t for t in tools if t.name in target_tools]
        log_step("도구 필터링 완료", "SUCCESS", f"IntentClassifier 도구: {len(filtered)}개")
        return filtered
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        return "당신은 DART 공시 시스템의 질문 의도 분류 전문가입니다."

    def _get_agent_tools_mapping(self) -> str:
        """각 에이전트별 전문 도구 매핑 정보를 동적으로 생성"""
        try:
            # README.md 기반 에이전트별 도구 매핑 (하드코딩 최소화)
            agent_tools = {
                "FinancialAgent": [
                    "get_single_acnt (단일회사 재무제표)",
                    "get_multi_acnt (다중회사 재무제표)",
                    "get_single_acc (단일회사 계정과목)",
                    "get_single_index (단일회사 재무지표)",
                    "get_multi_index (다중회사 재무지표)",
                ],
                "GovernanceAgent": [
                    "get_major_shareholder (최대주주 및 특수관계인 지분)",
                    "get_major_shareholder_changes (최대주주 지분 변동)",
                    "get_minority_shareholder (소액주주 현황)",
                    "get_major_holder_changes (5% 이상 주주 지분 변동)",
                    "get_executive_trading (임원 및 주요주주 주식 거래)",
                    "get_executive_info (임원 현황)",
                    "get_employee_info (직원 현황)",
                    "get_outside_director_status (사외이사 현황)",
                ],
                "CapitalChangeAgent": [
                    "get_stock_increase_decrease (증자/감자 현황)",
                    "get_stock_total (주식 총수 현황)",
                    "get_treasury_stock (자기주식 현황)",
                    "get_treasury_stock_acquisition (자기주식 취득 결정)",
                    "get_treasury_stock_disposal (자기주식 처분 결정)",
                    "get_treasury_stock_trust_contract (자기주식 신탁계약 체결)",
                    "get_treasury_stock_trust_termination (자기주식 신탁계약 해지)",
                    "get_paid_in_capital_increase (유상증자 결정)",
                    "get_free_capital_increase (무상증자 결정)",
                    "get_paid_free_capital_increase (유무상증자 결정)",
                    "get_capital_reduction (감자 결정)",
                ],
                "DebtFundingAgent": [
                    "get_debt (채무증권 발행 및 매출 내역)",
                    "get_debt_securities_issued (채무증권 발행 실적)",
                    "get_convertible_bond (전환사채 발행 결정)",
                    "get_bond_with_warrant (신주인수권부사채 발행 결정)",
                    "get_exchangeable_bond (교환사채 발행 결정)",
                    "get_write_down_bond (상각형 조건부자본증권 발행 결정)",
                    "get_commercial_paper_outstanding (기업어음 미상환 잔액)",
                    "get_short_term_bond_outstanding (단기사채 미상환 잔액)",
                    "get_corporate_bond_outstanding (회사채 미상환 잔액)",
                    "get_hybrid_securities_outstanding (신종자본증권 미상환 잔액)",
                    "get_conditional_capital_securities_outstanding (조건부자본증권 미상환 잔액)",
                    "get_public_capital_usage (공모자금 사용내역)",
                    "get_private_capital_usage (사모자금 사용내역)",
                    "get_equity (지분증권 발행 및 매출 내역)",
                    "get_depository_receipt (예탁증권 발행 내역)",
                ],
                "BusinessStructureAgent": [
                    "get_merger_acquisition (M&A 정보)",
                    "get_business_division (사업 분할)",
                    "get_asset_transfer (자산 양수도)",
                ],
                "OverseasBusinessAgent": [
                    "get_overseas_investment (해외 투자)",
                    "get_foreign_subsidiary (해외 자회사)",
                    "get_export_import (수출입 현황)",
                ],
                "LegalComplianceAgent": [
                    "get_litigation (소송 정보)",
                    "get_regulatory_compliance (규제 준수)",
                    "get_audit_opinion (감사 의견)",
                ],
                "ExecutiveAuditAgent": [
                    "get_executive_compensation (임원 보수)",
                    "get_audit_committee (감사위원회)",
                    "get_internal_control (내부 통제)",
                ],
                "DocumentAnalysisAgent": [
                    "get_disclosure_list (공시 목록 조회)",
                    "get_disclosure_document (공시서류 원본 다운로드)",
                    "extract_financial_notes_document (재무제표 주석 추출)",
                    "search_financial_notes (공시문서 상세내용 키워드 기반 검색)",
                ],
            }

            # 포맷팅된 문자열 생성
            formatted_info = []
            for agent_name, tools in agent_tools.items():
                tools_str = "\n  - ".join(tools)
                formatted_info.append(f"### {agent_name}\n  - {tools_str}")

            return "\n\n".join(formatted_info)

        except Exception as e:
            log_step("도구 매핑 생성 실패", "ERROR", str(e))
            return "도구 매핑 정보를 생성할 수 없습니다."
    
    def _init_classification_patterns(self):
        """분류 패턴 초기화"""
        
        # 분석 범위 패턴
        self.scope_patterns = {
            AnalysisScope.SINGLE_COMPANY: [
                r"(\w+)의\s*(재무|부채|수익|리스크|지배구조|경영)",
                r"(\w+)\s*(분석|조회|현황|상태)",
            ],
            AnalysisScope.MULTI_COMPANY: [
                r"(\w+)\s*(vs|대비|비교)\s*(\w+)",
                r"(3사|여러|복수|다수)\s*(기업|회사)",
                r"(순위|랭킹|상위|하위)\s*(\d+)",
                r"업계\s*(3사|5사|10사)",
            ],
            AnalysisScope.INDUSTRY_ANALYSIS: [
                r"(반도체|자동차|금융|보험|제약|화학|철강|건설|통신|게임|바이오)\s*업계",
                r"(산업|업종|섹터)\s*(분석|현황|전망)",
                r"동종업계|같은\s*업종",
            ],
            AnalysisScope.COMPREHENSIVE_RISK: [
                r"종합\s*(리스크|위험|분석)",
                r"전체적인\s*(위험|리스크)",
                r"다각도\s*(분석|검토)",
                r"포괄적\s*(분석|리스크)",
            ],
        }
        
        # 분석 영역 패턴
        self.domain_patterns = {
            AnalysisDomain.FINANCIAL: [
                r"(재무|수익|매출|영업이익|당기순이익|자산|부채비율|유동비율)",
                r"(ROE|ROA|현금흐름|유동성|재무건전성)",
                r"(재무제표|손익계표|재무상태표)",
                # 자본변동 관련 패턴 추가
                r"(자본변동|자본구조|자본금|주식총수)",
                r"(유상증자|무상증자|유무상증자|자본감소)",
                r"(자기주식|자기주식취득|자기주식처분)",
                r"(신탁계약|신탁해지|주식소각)",
                r"(자본정책|자본전략|자본조정)",
            ],
            AnalysisDomain.DEBT_FUNDING: [
                r"(부채|채무|채권|사채|회사채|전환사채)",
                r"(자금조달|자금|조달|발행|미상환)",
                r"(기업어음|단기사채|신주인수권부사채|교환사채)",
                r"(상각형|조건부자본증권|신종자본증권)",
                r"(공모자금|사모자금|지분증권|예탁증권)",
                r"(채무증권|미상환잔액|자금사용|자금용도)",
                r"(이자율|만기|보장비율|발행조건)",
                r"(부채구조|자금전략|채무관리)",
            ],
            AnalysisDomain.GOVERNANCE: [
                r"(지배구조|주주|대주주|경영진|임원|사외이사)",
                r"(지분|주식|경영권|내부거래)",
                r"(임원보수|보상|스톡옵션)",
                r"(주주총회|이사회|감사)",
            ],
            AnalysisDomain.BUSINESS: [
                r"(M&A|인수합병|사업재편|분할|합병)",
                r"(해외진출|해외사업|글로벌)",
                r"(사업구조|사업포트폴리오|다각화)",
                r"(자산양수도|영업양수도)",
            ],
            AnalysisDomain.LEGAL_RISK: [
                r"(소송|법적|규제|컴플라이언스)",
                r"(부도|파산|회생절차|관리절차)",
                r"(감사의견|감사인|회계감사)",
                r"(영업정지|제재|처벌)",
            ],
        }
        
        # 분석 깊이 패턴
        self.depth_patterns = {
            AnalysisDepth.BASIC: [
                r"(조회|확인|알려줘|보여줘)",
                r"(현황|상태|정보|데이터)",
                r"간단히|기본적인",
            ],
            AnalysisDepth.INTERMEDIATE: [
                r"(비교|대비|차이|변화|추세)",
                r"(분석|평가|검토)",
                r"(위험한지|문제없는지|어떤지)",
            ],
            AnalysisDepth.ADVANCED: [
                r"(리스크|위험|전망|예측)",
                r"(종합|심층|상세|포괄)",
                r"(시나리오|대응방안|전략)",
                r"(패턴|상관관계|인과관계)",
            ],
        }

    @observe()
    async def classify_intent_and_select_agents(
        self, question: str, corp_info: Dict[str, Any]
    ) -> AsyncGenerator[Dict[str, str], IntentClassificationResult]:
        """
        기업 식별 + 질문 의도 분류 + 에이전트 선택 (통합 처리)
        README.md 흐름에 따라 IntentClassifierAgent가 모든 책임을 담당합니다.
        """
        try:
            # 1번 yield: 시작 알림
            start_msg = await self.message_generator.generate_progress_message(
                action="intent_classification_start",
                context={
                    "user_question": question,
                    "corp_name": "",
                    "agents": []
                }
            )
            yield {"type": "progress", "content": start_msg}
            
            log_agent_flow(
                "IntentClassifierAgent",
                "기업 식별 + 의도 분류 + 에이전트 선택 시작",
                0,
                f"question: {question}",
            )

            # 1. 기업명 추출 및 기업코드 찾기 (LLM이 반드시 답변하도록 강화됨)
            company_names_str = await self._extract_company_name(question)
            if not company_names_str or len(company_names_str.strip()) < 2:
                log_step(
                    "LLM 기업명 추출 실패",
                    "ERROR",
                    f"LLM이 적절한 기업명을 제공하지 못함: '{company_names_str}'",
                )
                error_msg = await self.message_generator.generate_error_message(
                    error_type="company_name_extraction_failed",
                    context={
                        "user_question": question,
                        "error_context": "질문에서 기업명을 찾을 수 없습니다"
                    }
                )
                yield {"type": "error", "content": error_msg}
                return

            # 복수 기업명 처리 (쉼표로 구분된 경우)
            company_names = [
                name.strip() for name in company_names_str.split(",") if name.strip()
            ]
            log_step("기업명 추출 성공", "SUCCESS", f"추출된 기업명: {company_names}")

            # 복수 기업인 경우
            if len(company_names) > 1:
                log_step(
                    "복수 기업 처리", "INFO", f"{len(company_names)}개 기업 처리 시작"
                )
                corp_info_list = []

                for company_name in company_names:
                    # 각 기업별로 기업코드 조회
                    corp_lookup_result = await self._find_corporation_code(company_name)
                    if corp_lookup_result and "error" not in corp_lookup_result:
                        extracted_corp_code = self._extract_corp_code_from_result(
                            corp_lookup_result
                        )
                        if extracted_corp_code and extracted_corp_code.strip():
                            corp_info_list.append(
                                {
                                    "corp_name": company_name,
                                    "corp_code": extracted_corp_code,
                                    "corp_code_verified": True,
                                    "lookup_result": corp_lookup_result,
                                    "identified_from": question,
                                }
                            )
                            log_step(
                                "기업 정보 구성",
                                "SUCCESS",
                                f"기업: {company_name}, 코드: {extracted_corp_code}",
                            )
                        else:
                            log_step(
                                "기업코드 추출 실패",
                                "WARNING",
                                f"'{company_name}' 기업코드 추출 실패",
                            )
                    else:
                        log_step(
                            "기업코드 조회 실패",
                            "WARNING",
                            f"'{company_name}' 기업코드 조회 실패",
                        )

                if not corp_info_list:
                    log_step(
                        "모든 기업 조회 실패",
                        "ERROR",
                        "모든 기업의 기업코드를 찾을 수 없습니다",
                    )
                    error_msg = await self.message_generator.generate_error_message(
                        error_type="multi_company_lookup_failed",
                        context={
                            "user_question": question,
                            "error_context": f"{len(company_names)}개 기업의 정보를 찾을 수 없습니다"
                        }
                    )
                    yield {"type": "error", "content": error_msg}
                    return

                # 복수 기업 분류 결과 생성
                all_corp_info = {
                    "corp_name": ",".join([corp["corp_name"] for corp in corp_info_list]),
                    "corp_code": ",".join([corp["corp_code"] for corp in corp_info_list]),
                    "corp_info_list": corp_info_list,
                    "is_multi_company": True
                }
                basic_classification = await self._classify_standard(
                    question, all_corp_info
                )
                
                # 2번 yield: 선택된 에이전트 안내 (복수 기업)
                selected_agents = basic_classification.required_agents or ["financial"]
                agent_names = {
                    "financial": "재무 분석",
                    "governance": "지배구조 분석", 
                    "capital_change": "자본변동 분석",
                    "debt_funding": "부채자금조달 분석",
                    "business_structure": "사업구조 분석",
                    "overseas_business": "해외사업 분석",
                    "legal_risk": "법적리스크 분석",
                    "executive_audit": "경영진감사 분석",
                    "document_analysis": "문서 기반 심층 분석"
                }
                agent_display_list = [agent_names.get(agent, agent) for agent in selected_agents]
                selection_msg = await self.message_generator.generate_progress_message(
                    action="agent_selection_complete",
                    context={
                        "user_question": question,
                        "corp_name": "복수 기업",
                        "agents": agent_display_list
                    }
                )
                yield {"type": "progress", "content": selection_msg}
                
                # corp_info는 딕셔너리로 유지하되, corp_info_list와 is_multi_company 정보 포함
                basic_classification.corp_info = all_corp_info  # 딕셔너리로 설정
                basic_classification.scope = (
                    AnalysisScope.MULTI_COMPANY
                )  # 복수 기업으로 설정
                log_step(
                    "복수 기업 분류 완료",
                    "SUCCESS",
                    f"{len(corp_info_list)}개 기업 분류 완료",
                )
                yield basic_classification
                return

            else:
                # 단일 기업 처리 (기존 로직)
                company_name = company_names[0]

                # 2. 기업코드 조회 (필수)
                corp_lookup_result = await self._find_corporation_code(company_name)
                if not corp_lookup_result or "error" in corp_lookup_result:
                    log_step(
                        "기업코드 조회 실패",
                        "ERROR",
                        f"'{company_name}' 기업코드를 찾을 수 없습니다",
                    )
                    error_msg = await self.message_generator.generate_error_message(
                        error_type="corp_code_lookup_failed",
                        context={
                            "user_question": question,
                            "error_context": f"'{company_name}' 기업의 정보를 찾을 수 없습니다"
                        }
                    )
                    yield {"type": "error", "content": error_msg}
                    return

                # 3. 기업 정보 구성
                extracted_corp_code = self._extract_corp_code_from_result(
                    corp_lookup_result
                )
                if not extracted_corp_code or not extracted_corp_code.strip():
                    log_step(
                        "기업코드 추출 실패",
                        "ERROR",
                        f"'{company_name}' 기업코드 추출에 실패했습니다",
                    )
                    error_msg = await self.message_generator.generate_error_message(
                        error_type="corp_code_extraction_failed",
                        context={
                            "user_question": question,
                            "error_context": f"'{company_name}' 기업의 코드를 확인할 수 없습니다"
                        }
                    )
                    yield {"type": "error", "content": error_msg}
                    return

                verified_corp_info = {
                    "corp_name": company_name,
                    "corp_code": extracted_corp_code,
                    "corp_code_verified": True,
                    "lookup_result": corp_lookup_result,
                    "identified_from": question,
                }
                log_step(
                    "기업 정보 구성 완료",
                    "SUCCESS",
                    f"기업: {company_name}, 코드: {verified_corp_info.get('corp_code', 'N/A')}",
                )

                # 4. LLM 기반 질문 의도 분류 (패턴 기반 제거) - 확인된 기업 정보 사용
                log_step("🔍 _llm_based_agent_selection 직접 호출 시작", "INFO", f"기업: {company_name}")
                llm_result = await self._llm_based_agent_selection(question, verified_corp_info)
                
                # IntentClassificationResult 생성
                basic_classification = IntentClassificationResult(
                    scope=llm_result["scope"],
                    domain=llm_result["domain"], 
                    depth=llm_result["depth"],
                    required_agents=llm_result["required_agents"],
                    recommended_agents=llm_result["required_agents"],
                    reasoning=llm_result.get("reasoning", "LLM 기반 분류"),
                    corp_info=verified_corp_info,
                    needs_deep_analysis=llm_result.get("needs_deep_analysis", False),
                    analysis_reasoning=llm_result.get("analysis_reasoning", ""),
                    recent_disclosures=llm_result.get("recent_disclosures", [])
                )
                
                # 업종 정보를 corp_info에 추가
                if llm_result.get("corp_basic_info"):
                    corp_basic_info = llm_result["corp_basic_info"]
                    if corp_basic_info.get("industry_classification"):
                        basic_classification.corp_info["industry_classification"] = corp_basic_info["industry_classification"]
                        log_step("업종 정보 추가", "SUCCESS", f"업종: {corp_basic_info['industry_classification']}")
                log_step("🔍 LLM 기반 분류 완료", "INFO", f"선택된 에이전트: {basic_classification.required_agents}")

                # 2번 yield: 선택된 에이전트 안내
                selected_agents = basic_classification.required_agents or ["financial"]
                agent_names = {
                    "financial": "재무 분석",
                    "governance": "지배구조 분석", 
                    "capital_change": "자본변동 분석",
                    "debt_funding": "부채자금조달 분석",
                    "business_structure": "사업구조 분석",
                    "overseas_business": "해외사업 분석",
                    "legal_risk": "법적리스크 분석",
                    "executive_audit": "경영진감사 분석",
                    "document_analysis": "문서 기반 심층 분석"
                }
                agent_display_list = [agent_names.get(agent, agent) for agent in selected_agents]
                selection_msg = await self.message_generator.generate_progress_message(
                    action="agent_selection_complete",
                    context={
                        "user_question": question,
                        "corp_name": corp_info.get("corp_name", ""),
                        "agents": agent_display_list
                    }
                )
                yield {"type": "progress", "content": selection_msg}

                # 5. 기본 분류 결과 반환
                basic_classification.corp_info = verified_corp_info
                yield basic_classification
                return
            
        except Exception as e:
            log_step("의도 분류 오류", "ERROR", str(e))
            # 기본값 반환
            error_msg = await self.message_generator.generate_error_message(
                error_type="intent_classification_error",
                context={
                    "user_question": question,
                    "error_context": "질문 분석 중 문제가 발생했습니다"
                }
            )
            yield {"type": "error", "content": error_msg}
            return

    async def _extract_company_name(self, question: str) -> str:
        """LLM을 활용한 기업명 추출 - 복수 기업 지원"""
        try:
            print(f"🔥🔥🔥 LLM 기업명 추출 시작: '{question}'")
            log_step("LLM 기업명 추출 시작", "INFO", f"질문: '{question}'")

            # 기업 데이터베이스 기반 집합어 처리 프롬프트
            extraction_prompt = f"""당신은 한국 기업명 추출 전문가입니다. 질문에서 기업명을 정확히 추출하세요.

질문: "{question}"

**참고 기업 데이터베이스 (업종별 시가총액 순):**
전기·전자: 삼성전자, SK하이닉스, LG에너지솔루션, 삼성전자우, 삼성SDI, 포스코퓨처엠, LG전자, HD현대일렉트릭, 삼성전기, 에코프로머티, LG디스플레이, LS ELECTRIC, LG이노텍, 효성중공업, 엘앤에프, 한화시스템, 이수페타시스, SK아이이테크놀로지, 대한전선, 롯데에너지머티리얼즈, DB하이텍, 산일전기, 경동나비엔, 일진전기, 두산퓨얼셀, LS머트리얼즈, DN오토모티브
기타금융: KB금융, 신한지주, 메리츠금융지주, 하나금융지주, HD한국조선해양, LG, 우리금융지주, SK스퀘어, SK, HD현대, 한진칼, 맥쿼리인프라, 삼성카드, 한국금융지주, GS, LS, 두산, JB금융지주, 카카오페이, CJ
운송장비·부품: 현대차, 기아, 현대모비스, 한화에어로스페이스, HD현대중공업, 한화오션, 삼성중공업, 현대로템, 현대차2우B, 한국항공우주, HD현대미포, 현대차우, HL만도, 에스엘, 현대위아, KG모빌리티, SNT다이내믹스, 일진하이솔루스, SNT모티브, 명신산업
일반서비스: NAVER, 카카오, 크래프톤, 삼성에스디에스, SK바이오팜, 하이브, HD현대마린솔루션, 넷마블, 코웨이, 포스코DX, 엔씨소프트, 삼성E&A, 현대오토에버, 강원랜드, 시프트업, 한전기술, 에스원, 제일기획, 더존비즈온, CJ ENM
제약: 삼성바이오로직스, 셀트리온, 유한양행, HLB, SK바이오사이언스, 한미약품, 한올바이오파마, 녹십자, 대웅제약, 대웅, 종근당, HK이노엔, HLB생명과학, 보령, 동아에스티, JW중외제약, 신풍제약, 바이오노트, 영진약품, 일동제약
화학: LG화학, SK이노베이션, 아모레퍼시픽, S-Oil, SKC, LG생활건강, 한국타이어앤테크놀로지, 롯데케미칼, 금호석유화학, 한화솔루션, 코스모신소재, 금양, KCC, 한화, 에이피알, 아모레퍼시픽홀딩스, LG화학우, 한국콜마, 코스맥스, 동원시스템즈
유통: 삼성물산, 포스코인터내셔널, 미스토홀딩스, GS리테일, 동서, BGF리테일, 영원무역, 롯데쇼핑, 호텔신라, 이마트, SK가스, 신세계, ISC, 한샘, LX인터내셔널, SK네트웍스, 현대백화점, DI동일, HLB테라퓨틱스, 케이카
금속: POSCO홀딩스, 고려아연, 현대제철, 풍산, TCC스틸, SK오션플랜트, 삼아알미늄, 세아베스틸지주, 영풍, KG스틸, 고려제강, 동국제강, 세아홀딩스, 한국철강, 대한제강, 세아제강, KISCO홀딩스, SIMPAC, 알루코, 휴스틸
기계·장비: 두산에너빌리티, 한미반도체, LIG넥스원, 두산밥캣, 두산로보틱스, HPSP, 씨에스윈드, 한온시스템, 현대엘리베이터, HD현대인프라코어, 한화엔진, HD현대건설기계, HD현대마린엔진, 고영, 한국카본, 기가비스, STX엔진, KZ정밀, 에이프로젠, HB솔루션
보험: 삼성생명, 삼성화재, DB손해보험, 현대해상, 한화생명, 코리안리, 미래에셋생명, 동양생명, 삼성화재우, 롯데손해보험, 한화손해보험, 흥국화재, 흥국화재우

**주요 기업 (시가총액 상위 100개):**
삼성전자, SK하이닉스, LG에너지솔루션, 삼성바이오로직스, 현대차, 삼성전자우, 셀트리온, 기아, KB금융, 신한지주, POSCO홀딩스, NAVER, 삼성물산, LG화학, 삼성SDI, 현대모비스, 삼성생명, 메리츠금융지주, 하나금융지주, 포스코퓨처엠, 한화에어로스페이스, HD현대중공업, 카카오, 삼성화재, 고려아연, 크래프톤, LG전자, KT&G, HD한국조선해양, 두산에너빌리티, 한국전력, HMM, 유한양행, LG, 우리금융지주, SK텔레콤, SK스퀘어, 삼성에스디에스, 기업은행, 한미반도체, HD현대일렉트릭, KT, SK이노베이션, 카카오뱅크, SK, SK바이오팜, 한화오션, 삼성전기, 포스코인터내셔널, HLB, 삼성중공업, 현대글로비스, 대한항공, DB손해보험, 하이브, 에코프로머티, 현대로템, 아모레퍼시픽, S-Oil, HD현대, 한진칼, 현대차2우B, SKC, LIG넥스원, LG생활건강, HD현대마린솔루션, 미래에셋증권, LG디스플레이, 한국항공우주, 맥쿼리인프라, 넷마블, 코웨이, LS ELECTRIC, LG이노텍, 삼성카드, 한국타이어앤테크놀로지, NH투자증권, SK바이오사이언스, HD현대미포, LG유플러스, 한국금융지주, 포스코DX, CJ제일제당, 삼양식품, 삼성증권, 엔씨소프트, 한미약품, 두산밥캣, 삼성E&A, 두산로보틱스, 현대차우, 현대오토에버, 오리온, GS, LS, 롯데케미칼, 효성중공업, 금호석유화학, 한국가스공사, 엘앤에프

추출 규칙:
1. **명시적 기업명 우선**: 질문에 직접 언급된 기업명이 있으면 그것만 추출
2. **집합어 지능적 확장**: 명시적 기업명이 없으면 집합어를 위 데이터베이스의 해당 업종/그룹 기업명으로 확장
   - "N대", "빅N", "톱N" 등의 표현을 인식
   - 위 데이터베이스의 업종별/시가총액 순 기업들을 참조하여 정확한 기업명 나열
   - 숫자에 맞는 정확한 개수만 반환

3. **출력 형식**: 기업명만 쉼표(,)로 구분, 설명/접두어/따옴표 금지
4. **정규화**: (주), (유), (합) 등 법인 표기 제거, 공백 정리
5. **불확실시**: 모호하거나 특정할 수 없으면 빈 문자열

중요: 집합어 확장 시 위 데이터베이스의 업종별/시가총액 순 기업들을 참조하여 정확한 기업명을 나열하세요.

기업명:"""

            # LLM 호출 (메시지 형식으로)
            if hasattr(self, "llm") and self.llm:
                try:
                    print(f"🔥🔥🔥 LLM 메시지 형식 호출 시작")
                    from langchain_core.messages import HumanMessage

                    response = await self.llm.ainvoke(
                        [HumanMessage(content=extraction_prompt)]
                    )
                    extracted_name = (
                        response.content
                        if hasattr(response, "content")
                        else str(response)
                    )
                    extracted_name = extracted_name.strip()

                    # "기업명:" 또는 "답:" 부분 제거 처리
                    if extracted_name.startswith("기업명:"):
                        extracted_name = extracted_name[3:].strip()
                    elif extracted_name.startswith("답:"):
                        extracted_name = extracted_name[2:].strip()
                    elif extracted_name.startswith("답 :"):
                        extracted_name = extracted_name[3:].strip()

                    # 기업명 정리: (주), (유), (합) 등 제거
                    import re

                    extracted_name = re.sub(r"\([^)]*\)", "", extracted_name).strip()

                    print(
                        f"🔥🔥🔥 LLM 메시지 형식 호출 성공 (정리 후): '{extracted_name}'"
                    )
                except Exception as e:
                    print(f"🔥🔥🔥 LLM 메시지 형식 호출 실패: {str(e)}")
                    log_step("LLM 메시지 형식 호출 실패", "ERROR", f"오류: {str(e)}")
                    return ""
            else:
                print(f"🔥🔥🔥 LLM이 없음")
                log_step("LLM 없음", "ERROR", "LLM이 설정되지 않음")
                return ""

            print(f"🔥🔥🔥 LLM 추출 결과 (정리 후): '{extracted_name}'")
            print(f"🔥🔥🔥 LLM 결과 타입: {type(extracted_name)}")
            print(
                f"🔥🔥🔥 LLM 결과 길이: {len(extracted_name) if extracted_name else 0}"
            )
            log_step("LLM 기업명 추출", "INFO", f"추출된 기업명: '{extracted_name}'")

            # LLM 응답을 그대로 반환 (검증이나 필터링 없이)
            print(f"🔥🔥🔥 LLM 기업명 추출 완료: '{extracted_name}'")
            log_step("LLM 기업명 추출 완료", "SUCCESS", f"기업명: '{extracted_name}'")
            return extracted_name

        except Exception as e:
            print(f"🔥🔥🔥 LLM 기업명 추출 오류: {str(e)}")
            log_step("LLM 기업명 추출 오류", "ERROR", f"오류: {str(e)}")
            return ""

    async def _search_local_corpcode(self, company_name: str) -> Dict[str, Any]:
        """로컬 CORPCODE.xml에서 기업코드 검색 - 다양한 매칭 방법 적용"""
        try:
            import xml.etree.ElementTree as ET
            from difflib import SequenceMatcher

            import os

            corpcode_path = os.path.join(
                os.getcwd(), "mcp/mcp-opendart/src/mcp_opendart/utils/data/CORPCODE.xml"
            )

            print(f"🔥🔥🔥 로컬 CORPCODE.xml 검색 시작: '{company_name}'")
            log_step("로컬 CORPCODE 검색", "INFO", f"파일: {corpcode_path}")

            # XML 파일 파싱
            tree = ET.parse(corpcode_path)
            root = tree.getroot()

            exact_matches = []
            contains_matches = []
            similar_matches = []

            # 검색어 정규화 (공백 제거, 소문자 변환)
            normalized_search = company_name.replace(" ", "").lower()

            # 모든 기업 정보 검색
            for corp in root.findall(".//list"):
                corp_cls = corp.find("corp_cls")
                corp_name = corp.find("corp_name")
                corp_code = corp.find("corp_code")

                if (
                    corp_cls is not None
                    and corp_name is not None
                    and corp_code is not None
                ):
                    # 상장법인만 대상 (Y: 유가증권시장, K: 코스닥, N: 코넥스, E: 기타)
                    if corp_cls.text in ["Y", "K", "N", "E"]:
                        current_corp_name = corp_name.text.strip()
                        current_corp_code = corp_code.text.strip()
                        normalized_corp = current_corp_name.replace(" ", "").lower()

                        # 1. Exact match 검사
                        if (
                            company_name == current_corp_name
                            or normalized_search == normalized_corp
                        ):
                            exact_matches.append(
                                {
                                    "corp_name": current_corp_name,
                                    "corp_code": current_corp_code,
                                    "corp_cls": corp_cls.text,
                                    "match_type": "exact",
                                }
                            )

                        # 2. Contains match 검사 (기업명이 포함되거나 포함하는 경우)
                        elif (
                            company_name in current_corp_name
                            or current_corp_name in company_name
                            or normalized_search in normalized_corp
                            or normalized_corp in normalized_search
                        ):
                            contains_matches.append(
                                {
                                    "corp_name": current_corp_name,
                                    "corp_code": current_corp_code,
                                    "corp_cls": corp_cls.text,
                                    "match_type": "contains",
                                }
                            )

                        # 3. 유사도 매칭 (0.6 이상으로 임계값 낮춤)
                        similarity = SequenceMatcher(
                            None, normalized_search, normalized_corp
                        ).ratio()
                        if similarity >= 0.6:
                            similar_matches.append(
                                {
                                    "corp_name": current_corp_name,
                                    "corp_code": current_corp_code,
                                    "corp_cls": corp_cls.text,
                                    "similarity": similarity,
                                    "match_type": "similar",
                                }
                            )

            # 결과 처리 (우선순위: exact > contains > similar)
            if exact_matches:
                result = exact_matches[0]  # 첫 번째 exact match 사용
                print(f"🔥🔥🔥 Exact match 발견: {result}")
                log_step(
                    "Exact match 성공",
                    "SUCCESS",
                    f"기업: {result['corp_name']}, 코드: {result['corp_code']}",
                )
                return result

            if contains_matches:
                result = contains_matches[0]  # 첫 번째 contains match 사용
                print(f"🔥🔥🔥 Contains match 발견: {result}")
                log_step(
                    "Contains match 성공",
                    "SUCCESS",
                    f"기업: {result['corp_name']}, 코드: {result['corp_code']}",
                )
                return result

            if similar_matches:
                # 유사도 높은 순으로 정렬
                similar_matches.sort(key=lambda x: x["similarity"], reverse=True)
                result = similar_matches[0]
                print(f"🔥🔥🔥 유사도 매칭 발견: {result}")
                log_step(
                    "유사도 매칭 성공",
                    "SUCCESS",
                    f"기업: {result['corp_name']}, 코드: {result['corp_code']}, 유사도: {result['similarity']:.2f}",
                )
                return result

            print(f"🔥🔥🔥 로컬 CORPCODE.xml에서 '{company_name}' 미발견")
            log_step(
                "로컬 검색 실패", "WARNING", f"'{company_name}' 기업을 찾을 수 없음"
            )
            return {}

        except Exception as e:
            print(f"🔥🔥🔥 로컬 CORPCODE.xml 검색 오류: {str(e)}")
            log_step("로컬 검색 오류", "ERROR", f"오류: {str(e)}")
            return {}

    def _normalize_company_name(self, company_name: str) -> List[str]:
        """기업명 정규화 - 조사 제거 및 다양한 형태 생성"""
        if not company_name:
            return []

        # 기본 정리
        normalized = company_name.strip()

        # 조사 및 불필요한 부분 제거
        particles_to_remove = [
            "의",
            "는",
            "은",
            "이",
            "가",
            "을",
            "를",
            "에",
            "에서",
            "로",
            "으로",
            "와",
            "과",
            "도",
            "만",
            "부터",
            "까지",
            "에게",
            "한테",
        ]

        variations = [normalized]  # 원본 포함

        # 조사 제거 버전들 생성
        for particle in particles_to_remove:
            if normalized.endswith(particle):
                cleaned = normalized[: -len(particle)].strip()
                if cleaned and cleaned not in variations:
                    variations.append(cleaned)

        # 공통 접미사 처리
        suffixes_to_try = ["주식회사", "(주)", "㈜", "그룹", "홀딩스", "코퍼레이션"]
        base_name = normalized

        # 접미사 제거 시도
        for suffix in suffixes_to_try:
            if base_name.endswith(suffix):
                without_suffix = base_name[: -len(suffix)].strip()
                if without_suffix and without_suffix not in variations:
                    variations.append(without_suffix)
            elif base_name.startswith(suffix):
                without_prefix = base_name[len(suffix) :].strip()
                if without_prefix and without_prefix not in variations:
                    variations.append(without_prefix)

        # 접미사 추가 시도 제거 - 하드코딩으로 패턴을 붙이지 않음
        # LLM이 추출한 기업명을 그대로 사용하고, 로컬 검색에서 찾지 못하면 MCP 도구로 fallback

        print(f"🔥🔥🔥 기업명 정규화: '{company_name}' → {variations}")
        return variations

    async def _find_corporation_code(self, company_name: str) -> Dict[str, Any]:
        """기업명으로 기업코드 찾기 - 로컬 CORPCODE.xml 우선, MCP 도구 fallback"""
        if not company_name:
            return {"error": "기업명이 제공되지 않음"}

        print(f"🔥🔥🔥 기업코드 조회 시작: '{company_name}'")
        log_step("기업코드 조회 시작", "INFO", f"기업명: '{company_name}'")

        # 기업명 정규화 - 다양한 형태로 시도
        company_variations = self._normalize_company_name(company_name)

        # 1단계: 로컬 CORPCODE.xml에서 검색 (모든 변형에 대해)
        for variation in company_variations:
            local_result = await self._search_local_corpcode(variation)
            if local_result and "corp_code" in local_result:
                print(
                    f"🔥🔥🔥 로컬 CORPCODE.xml에서 기업코드 발견: {local_result} (변형: '{variation}')"
                )
                log_step(
                    "로컬 기업코드 조회 성공",
                    "SUCCESS",
                    f"기업: {variation}, 코드: {local_result['corp_code']}",
                )
                return local_result

        print(f"🔥🔥🔥 로컬 CORPCODE.xml에서 기업코드 미발견, MCP 도구 호출")
        log_step("로컬 조회 실패", "INFO", "MCP 도구로 fallback")

        # 2단계: MCP 도구 호출 (fallback) - 모든 변형에 대해 시도

        try:
            # BaseAgent 초기화 확인 - 재초기화하지 않음
            print(
                f"🔥🔥🔥 _initialized 상태: {getattr(self, '_initialized', 'UNDEFINED')}"
            )
            if not self._initialized:
                print(
                    f"🔥🔥🔥 IntentClassifierAgent가 초기화되지 않음 - MCP 도구 호출 불가"
                )
                log_step(
                    "기업코드 조회", "ERROR", "IntentClassifierAgent가 초기화되지 않음"
                )
                return {"error": "IntentClassifierAgent가 초기화되지 않았습니다"}
            else:
                print(f"🔥🔥🔥 IntentClassifierAgent 이미 초기화됨 (정상)")

            # MCP 클라이언트를 통해 직접 도구 호출 (모든 변형에 대해)
            # Agent Portal에서는 mcp_client 사용
            mcp_client = getattr(self, 'mcp_client', None)
            if mcp_client is None:
                # mcp_client가 없으면 가져오기
                from .mcp_client import get_opendart_mcp_client
                mcp_client = await get_opendart_mcp_client()
            
            if mcp_client and mcp_client.is_connected:
                print(f"🔥🔥🔥 MCP 클라이언트 연결 확인 완료")

                # 모든 기업명 변형에 대해 MCP 도구 호출 시도
                for variation in company_variations:
                    print(f"🔥🔥🔥 MCP 도구로 기업코드 조회 시도: '{variation}'")

                    try:
                        tool_result = await mcp_client.call_tool(
                            "get_corporation_code_by_name", {"corp_name": variation}
                        )

                        print(
                            f"🔥🔥🔥 MCP 도구 호출 결과 ('{variation}'): {type(tool_result)}"
                        )
                        print(f"🔥🔥🔥 MCP 도구 실제 응답 내용: {repr(tool_result)}")

                        if tool_result:
                            # 결과 파싱하여 실제 데이터가 있는지 확인
                            parsed_result = self._parse_mcp_result(tool_result)
                            if (
                                parsed_result
                                and parsed_result.get("items")
                                and len(parsed_result["items"]) > 0
                            ):
                                print(
                                    f"🔥🔥🔥 기업코드 조회 성공! (변형: '{variation}')"
                                )
                                log_step(
                                    "기업코드 조회",
                                    "SUCCESS",
                                    f"'{variation}' 기업코드 조회 완료",
                                )
                                return {
                                    "result": tool_result,
                                    "company_name": variation,
                                }
                            else:
                                print(
                                    f"🔥🔥🔥 '{variation}' 검색 결과 없음, 다음 변형 시도"
                                )
                        else:
                            print(f"🔥🔥🔥 '{variation}' MCP 도구 결과 없음")

                    except Exception as e:
                        print(f"🔥🔥🔥 '{variation}' MCP 도구 호출 오류: {str(e)}")
                        continue

                # 모든 변형 시도 후에도 결과 없음
                print(
                    f"🔥🔥🔥 모든 기업명 변형 시도 완료, 결과 없음: {company_variations}"
                )
                log_step(
                    "기업코드 조회",
                    "WARNING",
                    f"모든 변형 시도 후 결과 없음: {company_variations}",
                )
                return {
                    "error": f"'{company_name}' 기업을 찾을 수 없습니다 (시도한 변형: {len(company_variations)}개)"
                }
            else:
                print(f"🔥🔥🔥 MCP 클라이언트 연결 안됨!")
                log_step("기업코드 조회", "ERROR", "MCP 클라이언트가 연결되지 않음")
                return {"error": "MCP 클라이언트에 연결할 수 없습니다"}

        except Exception as e:
            log_step("기업코드 조회", "ERROR", f"기업코드 조회 실패: {e}")
            return {"error": f"기업코드 조회 실패: {e}"}

    def _parse_mcp_result(self, tool_result) -> Dict[str, Any]:
        """MCP 도구 결과 파싱 - common_transformer 로직 사용"""
        try:
            print(f"🔥🔥🔥 MCP 결과 파싱 시작: {type(tool_result)}")

            import json
            import re

            # TextContent 객체인 경우 직접 접근
            if hasattr(tool_result, "text"):
                result_text = tool_result.text
                print(f"🔥🔥🔥 TextContent.text 추출: {result_text}")
            # TextContent 형태의 문자열인 경우 정규식으로 추출
            elif "TextContent" in str(tool_result):
                text_match = re.search(r'text="([^"]*)"', str(tool_result))
                if text_match:
                    result_text = text_match.group(1)
                    print(f"🔥🔥🔥 정규식으로 추출 (큰따옴표): {result_text}")
                else:
                    text_match = re.search(r"text='([^']*)'", str(tool_result))
                    if text_match:
                        result_text = text_match.group(1)
                        print(f"🔥🔥🔥 정규식으로 추출 (작은따옴표): {result_text}")
                    else:
                        # fallback: 그냥 전체 문자열 사용
                        result_text = str(tool_result)
                        print(f"🔥🔥🔥 fallback 전체 문자열: {result_text}")
            else:
                result_text = str(tool_result)
                print(f"🔥🔥🔥 일반 문자열: {result_text}")

            # JSON 파싱 시도
            try:
                data = json.loads(result_text)
                print(f"🔥🔥🔥 JSON 파싱 성공: {type(data)}")
                return data
            except json.JSONDecodeError:
                # 작은따옴표를 큰따옴표로 변환 시도
                try:
                    json_text = result_text.replace("'", '"')
                    data = json.loads(json_text)
                    print(f"🔥🔥🔥 따옴표 변환 후 JSON 파싱 성공: {type(data)}")
                    return data
                except json.JSONDecodeError as e:
                    print(f"🔥🔥🔥 JSON 파싱 실패: {str(e)}")
                    return {
                        "error": f"JSON 파싱 실패: {str(e)}",
                        "raw_text": result_text,
                    }

        except Exception as e:
            print(f"🔥🔥🔥 MCP 결과 파싱 오류: {str(e)}")
            print(f"🔥🔥🔥 파싱 실패한 원본 데이터: {repr(tool_result)}")
            return {"error": f"파싱 오류: {str(e)}"}

    async def _classify_standard(
        self, question: str, corp_info: Dict[str, Any]
    ) -> IntentClassificationResult:
        """LLM 기반 의도 분류 (패턴 매칭 제거)"""
        # LLM을 통한 직접적인 에이전트 선택
        llm_result = await self._llm_based_agent_selection(question, corp_info)

        # 최종 결과 구성
        final_result = IntentClassificationResult(
            scope=llm_result["scope"],
            domain=llm_result["domain"],
            depth=llm_result["depth"],
            required_agents=llm_result["required_agents"],
            recommended_agents=llm_result[
                "required_agents"
            ],  # DartMasterAgent에서 사용하는 필드
            reasoning=llm_result.get("reasoning", "LLM 기반 분류"),
            corp_info=corp_info,
            needs_deep_analysis=llm_result.get("needs_deep_analysis", False),
            analysis_reasoning=llm_result.get("analysis_reasoning", ""),
            recent_disclosures=llm_result.get("recent_disclosures", [])
        )

        log_step(
            "LLM 기반 의도 분류 완료",
            "SUCCESS",
            f"선택된 에이전트: {final_result.required_agents}",
        )

        return final_result

    async def _get_recent_disclosures(self, corp_code: str) -> List[Dict[str, Any]]:
        """최근 공시 정보 조회 - 올바른 MCP 호출 방식 사용"""
        try:
            if not corp_code:
                log_step("최근 공시 조회", "WARNING", "기업코드가 없습니다")
                return []
            
            # 최근 30일 공시 조회
            from datetime import datetime, timedelta
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            
            log_step("최근 공시 조회 시작", "INFO", f"기업코드: {corp_code}, 기간: {start_date.strftime('%Y%m%d')} ~ {end_date.strftime('%Y%m%d')}")
            
            # MCP 매니저를 통한 올바른 도구 호출
            if hasattr(self, 'mcp_manager') and self.mcp_manager:
                try:
                    # 올바른 MCP 호출 방식 (다른 에이전트와 동일)
                    tool_result = await self.mcp_manager.call_tool(
                        "get_disclosure_list",
                        {
                            "corp_code": corp_code,
                            "bgn_de": start_date.strftime("%Y%m%d"),
                            "end_de": end_date.strftime("%Y%m%d")
                        }
                    )
                    
                    log_step("최근 공시 MCP 호출 결과", "INFO", f"결과 타입: {type(tool_result)}")
                    
                    if tool_result:
                        # 결과 파싱
                        parsed_result = self._parse_mcp_result(tool_result)
                        log_step("최근 공시 파싱 결과", "INFO", f"파싱 타입: {type(parsed_result)}")
                        
                        if isinstance(parsed_result, dict):
                            # DART API 응답 구조 확인
                            if "list" in parsed_result and isinstance(parsed_result["list"], list):
                                disclosures = parsed_result["list"]
                                log_step("최근 공시 조회 성공", "SUCCESS", f"공시 {len(disclosures)}건 발견")
                                return disclosures
                            elif "items" in parsed_result and isinstance(parsed_result["items"], list):
                                disclosures = parsed_result["items"]
                                log_step("최근 공시 조회 성공", "SUCCESS", f"공시 {len(disclosures)}건 발견")
                                return disclosures
                            else:
                                log_step("최근 공시 구조 확인", "WARNING", f"알 수 없는 응답 구조: {list(parsed_result.keys())}")
                        else:
                            log_step("최근 공시 파싱 실패", "WARNING", f"파싱 결과가 dict가 아님: {type(parsed_result)}")
                    else:
                        log_step("최근 공시 조회 결과 없음", "WARNING", "MCP 도구에서 결과를 반환하지 않음")
                        
                except Exception as e:
                    log_step("최근 공시 MCP 호출 오류", "ERROR", f"오류: {str(e)}")
                    import traceback
                    log_step("최근 공시 MCP 호출 스택", "ERROR", f"스택: {traceback.format_exc()}")
            else:
                log_step("최근 공시 조회 실패", "ERROR", "MCP 매니저가 초기화되지 않음")
            
            log_step("최근 공시 조회 완료", "INFO", "결과 없음으로 빈 배열 반환")
            return []
            
        except Exception as e:
            log_step("최근 공시 조회 전체 오류", "ERROR", f"오류: {str(e)}")
            return []

    async def _get_corporation_basic_info(self, corp_code: str) -> Dict[str, Any]:
        """기업 기본정보 조회 (업종 정보 포함)"""
        try:
            if not corp_code:
                log_step("기업 기본정보 조회", "WARNING", "기업코드가 없습니다")
                return {}
            
            log_step("기업 기본정보 조회 시작", "INFO", f"기업코드: {corp_code}")
            
            # MCP 매니저를 통한 도구 호출
            if hasattr(self, 'mcp_manager') and self.mcp_manager:
                try:
                    tool_result = await self.mcp_manager.call_tool(
                        "get_corporation_info",
                        {"corp_code": corp_code}
                    )
                    
                    log_step("기업 기본정보 MCP 호출 결과", "INFO", f"결과 타입: {type(tool_result)}")
                    
                    if tool_result:
                        # 결과 파싱
                        parsed_result = self._parse_mcp_result(tool_result)
                        log_step("기업 기본정보 파싱 결과", "INFO", f"파싱 타입: {type(parsed_result)}")
                        
                        if isinstance(parsed_result, dict):
                            # DART API 응답 구조 확인
                            if "list" in parsed_result and isinstance(parsed_result["list"], list):
                                corp_list = parsed_result["list"]
                                if corp_list and len(corp_list) > 0:
                                    corp_info = corp_list[0]
                                    industry = corp_info.get("industry_classification", "")
                                    log_step("기업 기본정보 조회 성공", "SUCCESS", f"업종: {industry}")
                                    return corp_info
                            elif "items" in parsed_result and isinstance(parsed_result["items"], list):
                                corp_list = parsed_result["items"]
                                if corp_list and len(corp_list) > 0:
                                    corp_info = corp_list[0]
                                    industry = corp_info.get("industry_classification", "")
                                    log_step("기업 기본정보 조회 성공", "SUCCESS", f"업종: {industry}")
                                    return corp_info
                            elif "industry_classification" in parsed_result:
                                # 직접적인 응답 구조 (list 없이 바로 객체)
                                industry = parsed_result.get("industry_classification", "")
                                log_step("기업 기본정보 조회 성공", "SUCCESS", f"업종: {industry}")
                                return parsed_result
                            else:
                                log_step("기업 기본정보 구조 확인", "WARNING", f"알 수 없는 응답 구조: {list(parsed_result.keys())}")
                        else:
                            log_step("기업 기본정보 파싱 실패", "WARNING", f"파싱 결과가 dict가 아님: {type(parsed_result)}")
                    else:
                        log_step("기업 기본정보 조회 결과 없음", "WARNING", "MCP 도구에서 결과를 반환하지 않음")
                        
                except Exception as e:
                    log_step("기업 기본정보 MCP 호출 오류", "ERROR", f"오류: {str(e)}")
                    import traceback
                    log_step("기업 기본정보 MCP 호출 스택", "ERROR", f"스택: {traceback.format_exc()}")
            else:
                log_step("기업 기본정보 조회 실패", "ERROR", "MCP 매니저가 초기화되지 않음")
            
            log_step("기업 기본정보 조회 완료", "INFO", "결과 없음으로 빈 dict 반환")
            return {}
            
        except Exception as e:
            log_step("기업 기본정보 조회 전체 오류", "ERROR", f"오류: {str(e)}")
            return {}

    async def _llm_based_agent_selection(
        self, question: str, corp_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """LLM을 통한 직접적인 에이전트 선택 - 패턴 매칭 완전 제거"""

        # 복수 기업 처리 추가
        if corp_info.get("is_multi_company", False):
            # 모든 기업의 공시 조회
            recent_disclosures = {}
            for corp in corp_info["corp_info_list"]:
                corp_code = corp["corp_code"]
                corp_name = corp["corp_name"]
                log_step("🔍 LLM 에이전트 선택 시작", "INFO", f"기업: {corp_name}, 코드: {corp_code}")
                recent_disclosures[corp_name] = await self._get_recent_disclosures(corp_code)
                log_step("🔍 LLM 에이전트 선택 공시 조회 완료", "INFO", f"{corp_name} 공시 {len(recent_disclosures[corp_name])}건 발견")
        else:
            # 단일 기업일 때는 기존 로직
            corp_code = corp_info.get("corp_code", "")
            log_step("🔍 LLM 에이전트 선택 시작", "INFO", f"기업코드: {corp_code}")
            recent_disclosures = await self._get_recent_disclosures(corp_code)
            log_step("🔍 LLM 에이전트 선택 공시 조회 완료", "INFO", f"공시 {len(recent_disclosures)}건 발견")
        
        # 기업 기본정보 조회 (업종 정보 포함)
        corp_basic_info = await self._get_corporation_basic_info(corp_info.get("corp_code", ""))
        log_step("🔍 LLM 에이전트 선택 기업정보 조회 완료", "INFO", f"업종: {corp_basic_info.get('industry_classification', 'N/A')}")
        
        # 공시 정보를 문자열로 포맷팅
        disclosure_summary = ""
        if corp_info.get("is_multi_company", False):
            # 복수 기업일 때
            disclosure_summary = "\n## 📰 최근 공시 정보 (최근 30일)\n"
            for corp_name, disclosures in recent_disclosures.items():
                disclosure_summary += f"\n### {corp_name}\n"
                if disclosures:
                    for disclosure in disclosures[:10]:  # 기업당 최근 10개만 표시
                        title = disclosure.get("report_nm", "제목 없음")
                        date = disclosure.get("rcept_dt", "날짜 없음")
                        disclosure_summary += f"- {date}: {title}\n"
                else:
                    disclosure_summary += "최근 30일간 공시 정보가 없습니다.\n"
        else:
            # 단일 기업일 때는 기존 로직
            if recent_disclosures:
                disclosure_summary = "\n## 📰 최근 공시 정보 (최근 30일)\n"
                for disclosure in recent_disclosures[:20]:  # 최근 20개만 표시
                    title = disclosure.get("report_nm", "제목 없음")
                    date = disclosure.get("rcept_dt", "날짜 없음")
                    disclosure_summary += f"- {date}: {title}\n"
            else:
                disclosure_summary = "\n## 📰 최근 공시 정보\n최근 30일간 공시 정보가 없습니다.\n"
        
        # 기업 정보 섹션 생성
        corp_info_section = ""
        if corp_info.get("is_multi_company", False):
            # 복수 기업일 때
            corp_info_section = "### 복수 기업 분석\n"
            for corp in corp_info["corp_info_list"]:
                corp_info_section += f"- **{corp['corp_name']}**: {corp['corp_code']}\n"
        else:
            # 단일 기업일 때
            corp_info_section = f"- 기업명: {corp_info.get('corp_name', 'N/A')}\n- 기업코드: {corp_info.get('corp_code', 'N/A')}\n"
        
        # 업종 정보를 문자열로 포맷팅
        industry_info = ""
        if corp_info.get("is_multi_company", False):
            # 복수 기업일 때
            industry_info = "\n## 🏭 업종 정보\n"
            for corp in corp_info["corp_info_list"]:
                corp_code = corp["corp_code"]
                corp_name = corp["corp_name"]
                # 각 기업의 업종 정보 조회
                corp_basic_info = await self._get_corporation_basic_info(corp_code)
                if corp_basic_info and corp_basic_info.get("industry_classification"):
                    industry = corp_basic_info["industry_classification"]
                    industry_info += f"- **{corp_name}**: {industry}\n"
                else:
                    industry_info += f"- **{corp_name}**: 업종 정보 없음\n"
            industry_info += "- 업종 특성을 고려한 분석이 필요합니다.\n"
        else:
            # 단일 기업일 때는 기존 로직
            if corp_basic_info and corp_basic_info.get("industry_classification"):
                industry = corp_basic_info["industry_classification"]
                industry_info = f"\n## 🏭 업종 정보\n- 업종: {industry}\n- 업종 특성을 고려한 분석이 필요합니다.\n"
            else:
                industry_info = "\n## 🏭 업종 정보\n업종 정보를 확인할 수 없습니다.\n"

        # 현재 날짜 동적 삽입
        from datetime import datetime
        current_date = datetime.now().strftime("%Y년 %m월 %d일")
        
        # 상세한 에이전트 설명 포함 프롬프트
        agent_selection_prompt = f"""당신은 기업 공시 데이터 분석을 위한 전문 에이전트 선택 전문가입니다.

## 🚨 최우선 원칙: 사용자 명시적 에이전트 지정 절대 무시 금지
사용자가 질문에서 특정 에이전트를 명시적으로 지정한 경우, 반드시 해당 에이전트만 선택하세요.
예: "문서 기반 심층 분석 에이전트로" → document_analysis만 선택

## 핵심 원칙
1. **데이터 기반 분석**: 도구로 얻은 데이터를 분석하고 설명하여 유용한 정보 제공
2. **투자 관점 금지**: 투자 조언, 투자 권유, 매수/매도 추천, 투자 판단 절대 금지
3. **객관적 분석**: 재무 데이터의 의미와 특징을 객관적으로 분석하고 설명
4. **재호출 허용**: 데이터가 이상하거나 불완전하면 필요에 따라 도구를 재호출하여 정확한 데이터 확보
5. **데이터 없으면**: 수집된 데이터를 기반으로 "해당 정보가 없습니다"라고 구체적으로 설명
6. **한국어 필수**: 반드시 한국어로만 응답

## 📅 현재 날짜
**현재 날짜: {current_date}**

## 사용자 질문
"{question}"

## 기업 정보
{corp_info_section}
{industry_info}

{disclosure_summary}

## 🔗 공시-질문 연계 분석 요청

위 공시 정보와 사용자 질문을 연결하여 분석하세요:
- 공시에서 나타난 사건/변화가 질문과 어떤 관련이 있는지
- 공시 내용을 고려할 때 어떤 추가 분석이 필요한지
- 공시에서 발견된 패턴이나 트렌드가 무엇인지

이 분석을 바탕으로 적절한 에이전트를 선택하고, 
analysis_reasoning에 연계 분석 결과를 포함시키세요.

## 🎯 에이전트 선택 가이드라인

**중요: 기계적 매칭이 아닌 의미 기반 선택**

사용자 질문의 본질적 의도와 공시에서 발견된 정보를 고려하여 에이전트를 선택하세요.
단순히 키워드 매칭이 아닌, 실제로 필요한 분석을 수행할 수 있는 에이전트를 선택하세요.

**🚨 최우선 규칙: 사용자가 명시적으로 에이전트를 지정한 경우 (절대 무시 금지)**
사용자가 질문에서 특정 에이전트를 명시적으로 지정한 경우, 반드시 해당 에이전트만 선택하세요.

**명시적 에이전트 지정 패턴:**
- **"document_analysis로", "문서 기반 심층 분석 에이전트로", "document_analysis (문서 기반 심층 분석 에이전트)로"** → document_analysis만 선택 (domain: "document_analysis")
- **"financial로", "재무 분석 에이전트로", "financial (재무 분석 에이전트)로"** → financial만 선택 (domain: "financial")
- **"governance로", "지배구조 분석 에이전트로", "governance (지배구조 분석 에이전트)로"** → governance만 선택 (domain: "governance")
- **기타 명시적 에이전트 지정** → 해당 에이전트만 선택

**중요**: 사용자가 명시적으로 에이전트를 지정했으면 다른 에이전트를 추가로 선택하지 마세요. 오직 지정된 에이전트만 선택하세요.

**일반적인 선택 규칙(키워드 금지, 의도 중심):**
- **정량 사실 조회/비교**: 재무제표에 등재되거나 표준화된 수치·비율을 확인/비교하려는 의도 → financial만 선택 (domain: "financial")
- **지배구조/주주·임원 구도 파악**: 최대·소액주주, 이사회·사외이사 구성, 임원 변동 등 지배구조의 현재 상태 파악 → governance만 선택 (domain: "governance")
- **자본 구조의 공식적 변경 사건**: 증자/감자, 주식수 변동, 자사주 취득·처분 등 자본 변동 의사결정/현황 → capital_change만 선택 (domain: "capital_change")
- **부채성 자금조달 구조/현황**: 회사채/단기사채/CP/조건부자본증권 등 발행·미상환·조달 내역 → debt_funding만 선택 (domain: "debt_funding")
- **해외 상장·상폐 등 대외 상장 사건**: 해외 상장(예정/결정/변경/폐지) 사건의 유무·상태 → overseas_business만 선택 (domain: "overseas_business")
- **법적·규제 리스크 사건**: 소송, 회생·부도, 영업정지 등 법적 절차/제재의 개시·종료 사실 → legal_risk만 선택 (domain: "legal_risk")
- **임원 보수·감사 관련 사항**: 임원 보수(총액/개별/유형), 감사 의견·계약 등 보수·감사 체계의 구체 → executive_audit만 선택 (domain: "executive_audit")
- **문서 원문 맥락·정의·주석·표 위치가 필요하거나, 구조화 도구에서 해당 정보가 부재/미조회로 확인된 경우에만** → document_analysis 선택 (domain: "document_analysis")

**보조 원칙:**
- 단일 의도면 단일 도메인을 우선. 복합 의도(명확히 다영역 포함)일 때만 다중 선택.
- "업종이 복잡할 수 있다/주석일 수도 있다" 같은 추정만으로 문서 분석을 선택하지 말 것.
- 원문 근거(정의·주석·표 위치) 제시 요청이 명시되지 않았다면, 정량 조회는 기본적으로 financial 단독으로 처리.
- 복합 질문이 아닌 이상 domain을 "mixed"로 설정하지 않는다.

## 🔧 사용 가능한 전문 에이전트들

### 1️⃣ financial (재무 분석 에이전트)
**역할**: 기업의 재무 데이터 수집 및 분석
**전문 도구**:
- get_corporation_info: 기업 기본정보 조회 (기업명, 대표자, 업종, 주소 등)
- get_single_acnt: 단일회사 재무제표 조회 (손익계산서, 재무상태표, 현금흐름표)
- get_multi_acnt: 다중회사 재무제표 비교 조회
- get_single_acc: 단일회사 계정과목 상세 조회 (매출액, 영업이익, 당기순이익 등)
- get_single_index: 단일회사 재무지표 조회 (ROE, ROA, 부채비율, 유동비율 등)
- get_multi_index: 다중회사 재무지표 비교 조회
**사용 시기**: 기업 기본정보, 매출, 수익성, 재무상태, 재무비율, 재무제표, 재무지표 관련 질문

### 2️⃣ governance (지배구조 분석 에이전트)
**역할**: 기업의 지배구조, 주주 현황, 경영진 정보 분석
**전문 도구**:
- get_major_shareholder: 최대주주 및 특수관계인 지분 현황
- get_major_shareholder_changes: 최대주주 지분 변동 내역
- get_minority_shareholder: 소액주주 현황
- get_major_holder_changes: 5% 이상 주주 지분 변동
- get_executive_trading: 임원 및 주요주주 주식 거래 내역
- get_executive_info: 임원 현황 및 보수
- get_employee_info: 직원 현황
- get_outside_director_status: 사외이사 현황
**사용 시기**: 주주구성, 지배구조, 경영진, 임원거래, 사외이사 관련 질문

### 3️⃣ capital_change (자본변동 분석 에이전트)
**역할**: 기업의 자본 구조 변화, 증자/감자, 자기주식 관련 분석
**전문 도구**:
- get_stock_total: 주식 총수 현황
- get_stock_increase_decrease: 증자/감자 현황
- get_treasury_stock: 자기주식 현황
- get_treasury_stock_acquisition: 자기주식 취득 결정
- get_treasury_stock_disposal: 자기주식 처분 결정
- get_treasury_stock_trust_contract: 자기주식 신탁계약 체결
- get_treasury_stock_trust_termination: 자기주식 신탁계약 해지
- get_paid_in_capital_increase: 유상증자 결정
- get_free_capital_increase: 무상증자 결정
- get_paid_free_capital_increase: 유무상증자 결정
- get_capital_reduction: 감자 결정
**사용 시기**: 증자, 감자, 자기주식, 주식총수, 자본변동 관련 질문

### 4️⃣ debt_funding (부채 및 자금조달 분석 에이전트)
**역할**: 기업의 부채 구조, 자금조달, 채권 발행 관련 분석
**전문 도구**:
- get_debt: 채무증권 발행 및 매출 내역
- get_debt_securities_issued: 채무증권 발행 실적
- get_convertible_bond: 전환사채 발행 결정
- get_bond_with_warrant: 신주인수권부사채 발행 결정
- get_exchangeable_bond: 교환사채 발행 결정
- get_write_down_bond: 상각형 조건부자본증권 발행 결정
- get_commercial_paper_outstanding: 기업어음 미상환 잔액
- get_short_term_bond_outstanding: 단기사채 미상환 잔액
- get_corporate_bond_outstanding: 회사채 미상환 잔액
- get_hybrid_securities_outstanding: 신종자본증권 미상환 잔액
- get_conditional_capital_securities_outstanding: 조건부자본증권 미상환 잔액
- get_public_capital_usage: 공모자금 사용내역
- get_private_capital_usage: 사모자금 사용내역
- get_equity: 지분증권 발행 및 매출 내역
- get_depository_receipt: 예탁증권 발행 내역
**사용 시기**: 부채, 채무, 자금조달, 사채발행, 회사채, 전환사채, 자금사용 관련 질문

### 5️⃣ business_structure (사업구조 분석 에이전트)
**역할**: 기업의 사업 구조 변화, M&A, 사업 분할, 타법인 투자 관련 분석
**전문 도구**:
- get_business_acquisition: 영업양수 결정
- get_business_transfer: 영업양도 결정
- get_merger: 회사합병 결정
- get_division: 회사분할 결정
- get_division_merger: 분할합병 결정
- get_stock_exchange: 주식교환/이전 결정
- get_merger_report: 합병 증권신고서
- get_stock_exchange_report: 주식교환/이전 증권신고서
- get_division_report: 분할 증권신고서
- get_other_corp_stock_acquisition: 타법인 주식 양수 결정
- get_other_corp_stock_transfer: 타법인 주식 양도 결정
- get_stock_related_bond_acquisition: 주권 관련 사채권 양수 결정
- get_stock_related_bond_transfer: 주권 관련 사채권 양도 결정
- get_tangible_asset_acquisition: 유형자산 양수 결정
- get_tangible_asset_transfer: 유형자산 양도 결정
- get_asset_transfer: 자산양수도 및 풋백옵션 계약
- get_investment_in_other_corp: 타법인 출자 현황
**사용 시기**: M&A, 합병, 인수, 사업분할, 자산양수도, 타법인투자, 타법인출자, 투자현황, 사업구조변화 관련 질문

### 6️⃣ overseas_business (해외사업 분석 에이전트)
**역할**: 기업의 해외 진출, 해외 상장, 글로벌 사업 관련 분석
**전문 도구**:
- get_foreign_listing_decision: 해외상장 결정 조회
- get_foreign_delisting_decision: 해외상장폐지 결정 조회
- get_foreign_listing: 해외상장 조회
- get_foreign_delisting: 해외상장폐지 조회
**사용 시기**: 해외상장, 해외진출, 글로벌사업 관련 질문

### 7️⃣ legal_compliance (법적 리스크 분석 에이전트)
**역할**: 기업의 법적 리스크, 소송, 경영위기 관련 분석
**전문 도구**:
- get_lawsuit: 소송 제기 사실 조회
- get_bankruptcy: 부도 발생 사실 조회
- get_business_suspension: 영업정지 사실 조회
- get_rehabilitation: 회생절차 개시신청 사실 조회
- get_dissolution: 해산사유 발생 사실 조회
- get_creditor_management: 채권은행 관리절차 개시 사실 조회
- get_creditor_management_termination: 채권은행 관리절차 종료 사실 조회
**사용 시기**: 소송, 법적리스크, 부도, 경영위기, 회생절차 관련 질문

### 8️⃣ executive_audit (경영진 및 감사 분석 에이전트)
**역할**: 경영진 보수, 감사 의견, 감사 계약 관련 분석
**전문 도구**:
- get_individual_compensation: 개별임원보수 조회
- get_total_compensation: 총임원보수 조회
- get_individual_compensation_amount: 개별임원보수금액 조회
- get_unregistered_exec_compensation: 미등기임원보수 조회
- get_executive_compensation_approved: 임원보수승인 조회
- get_executive_compensation_by_type: 임원보수유형별 조회
- get_accounting_auditor_opinion: 회계감사인의견 조회
- get_audit_service_contract: 감사서비스계약 조회
- get_non_audit_service_contract: 비감사서비스계약 조회
**사용 시기**: 임원보수, 감사의견, 감사계약, 경영진평가 관련 질문

### 9️⃣ document_analysis (문서 기반 심층 분석 에이전트)
**역할**: 사업보고서, 반기보고서 원본 공시문서를 상세 내용 검색하는 심층 분석
**전문 도구**:
- get_disclosure_list: 공시 목록 조회 (적절한 보고서 찾기)
- get_disclosure_document: 공시문서 원본 다운로드 (XML 형태)
- search_financial_notes: 공시문서 상세내용 키워드 기반 검색 (반복 호출 가능)
**사용 시기**: 사업보고서 내용, 재무제표 주석, 사업의 내용, 회사의 개요, 문서 내 상세 정보 관련 질문

## 📋 에이전트 선택 가이드라인
0. **원천 우선 규칙(Source-of-Truth)**: 질문의 내용이 표준 재무 지표나 수치로 안정적으로 제공된다고 확신할 수 있을 때만 `financial`을 우선 선택
    그 외(불확실·신규·도메인 특수·약어/업종 전문화 지표·정의/가정/방법·기간 보고서 언급)는 **`document_analysis` 단독으로 선택**
1. **특정 도구명 언급**: 질문에 특정 도구명이 언급되면 해당 에이전트를 반드시 선택
2. **복합 분석**: 여러 분야가 관련된 경우 관련 에이전트들을 모두 선택
3. **종합 분석**: "전반적", "종합적", "전체적" 분석 요청 시 3-5개 에이전트 선택
4. **연관성 고려**: 재무-자본변동, 지배구조-경영진, 사업구조-해외사업 등 연관 에이전트 함께 선택
5. **정보 복잡성 고려**: 단순 수치는 해당 전문 에이전트, 설명이나 해석이 필요한 내용은 document_analysis 선택

다음 JSON 형식으로 응답해주세요:
{{
    "scope": "single_company|multi_company|industry_analysis|comprehensive_risk",
    "domain": "financial|governance|business_structure|capital_change|debt_funding|overseas_business|legal_risk|executive_audit|document_analysis|mixed",
    "depth": "basic|intermediate|advanced",
    "required_agents": ["financial", "governance", "debt_funding", "document_analysis", ...],
    "reasoning": "에이전트 선택 이유와 근거",
    "needs_deep_analysis": true/false,
    "analysis_reasoning": "깊은 분석이 필요한 이유 또는 불필요한 이유"
}}

## 🧠 LLM 분석 깊이 판단 가이드

사용자 질문의 본질적 복잡성을 평가하여 needs_deep_analysis: true/false로 응답하세요:

1. **질문의 본질적 복잡성 평가**
   - 질문이 단순한 정보 확인인지, 복잡한 분석을 요구하는지
   - 현재 상태 조회인지, 원인과 영향의 깊은 이해를 원하는지
   - 질문자가 기대하는 답변의 깊이와 범위는 어느 정도인지

2. **공시 목록에서 발견된 특이점과 질문 연관성 확인**
   - 공시 목록에서 질문과 직접 관련된 특이한 이벤트가 있는지
   - 발견된 특이점이 사용자 질문과 얼마나 관련성이 있는지
   - 단순한 정기 공시인지, 특별한 변화를 알리는 공시인지

3. **분석의 필요성과 적절성 평가**
   - 질문의 복잡성에 비해 과도한 분석이 요구되는지
   - 사용자가 원하는 답변의 깊이와 제공할 수 있는 분석의 깊이가 일치하는지
   - 빠른 정보 제공이 더 적절한지, 깊은 분석이 더 가치 있는지

**reasoning과 analysis_reasoning에 판단 근거를 구체적으로 서술하세요.**

**중요**: 응답에 한자 사용 절대 금지. 한글, 영어, 숫자만 사용하세요.
"""

        try:
            # 직접 LLM 호출
            if hasattr(self, "llm") and self.llm:
                from langchain_core.messages import HumanMessage
                
                response = await self.llm.ainvoke(
                    [HumanMessage(content=agent_selection_prompt)]
                )
                    
                if response and hasattr(response, "content"):
                    response_content = response.content
                        
                    # JSON 파싱
                    import json
                    import re
                            
                    json_match = re.search(r"\{.*\}", response_content, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                        llm_response = json.loads(json_str)
                                
                        log_step(
                            "LLM 에이전트 선택 성공",
                            "SUCCESS",
                            f"선택된 에이전트: {llm_response.get('required_agents', [])}",
                        )

                        # Enum 변환
                        from agent.dart_agent.dart_types import (
                            AnalysisScope,
                            AnalysisDomain,
                            AnalysisDepth,
                        )

                        return {
                            "scope": AnalysisScope(llm_response["scope"]),
                            "domain": AnalysisDomain(llm_response["domain"]),
                            "depth": AnalysisDepth(llm_response["depth"]),
                            "required_agents": llm_response["required_agents"],
                            "reasoning": llm_response.get("reasoning", "LLM 기반 선택"),
                            "needs_deep_analysis": llm_response.get("needs_deep_analysis", False),
                            "analysis_reasoning": llm_response.get("analysis_reasoning", ""),
                            "recent_disclosures": recent_disclosures,
                            "corp_basic_info": corp_basic_info  # 업종 정보 포함
                        }
                    else:
                        log_step(
                            "LLM JSON 파싱 실패", "WARNING", "JSON 형식을 찾을 수 없음"
                        )
                        return self._get_fallback_agent_selection()
                else:
                    log_step("LLM 응답 없음", "ERROR", "LLM 응답이 비어있음")
                    return self._get_fallback_agent_selection()
            else:
                log_step("LLM 없음", "ERROR", "self.llm이 없음")
                return self._get_fallback_agent_selection()
            
        except Exception as e:
            log_step("LLM 에이전트 선택 오류", "ERROR", f"오류: {str(e)}")
            return self._get_fallback_agent_selection()

    def _get_fallback_agent_selection(self) -> Dict[str, Any]:
        """LLM 에이전트 선택 실패 시 기본값"""
        from agent.dart_agent.dart_types import (
            AnalysisScope,
            AnalysisDomain,
            AnalysisDepth,
        )

        return {
            "scope": AnalysisScope.SINGLE_COMPANY,
            "domain": AnalysisDomain.FINANCIAL,
            "depth": AnalysisDepth.INTERMEDIATE,
            "required_agents": ["financial"],
            "reasoning": "LLM 선택 실패로 기본 에이전트 사용",
            "needs_deep_analysis": False,
            "analysis_reasoning": "기본 분석으로 충분",
            "recent_disclosures": []
        }

    def _extract_corp_code_from_result(self, corp_lookup_result: Dict[str, Any]) -> str:
        """기업코드 조회 결과에서 기업코드 추출 - MCP 도구의 새로운 응답 형식 처리"""
        try:
            log_step(
                "🔍 기업코드 추출 시작", "INFO", f"조회 결과 구조: {corp_lookup_result}"
            )

            # MCP 도구 응답 형식 처리
            if "result" in corp_lookup_result and corp_lookup_result["result"]:
                result_data = corp_lookup_result["result"]
                log_step(
                    "🔍 result 필드 확인", "INFO", f"result 타입: {type(result_data)}"
                )

                # 1. 직접 dict/list 형태인 경우 (기존 방식)
                if isinstance(result_data, dict) and "corp_code" in result_data:
                    corp_code = result_data["corp_code"]
                    print(f"🔥🔥🔥 직접 dict에서 기업코드 추출 성공: {corp_code}")
                    log_step(
                        "🔍 기업코드 추출 성공",
                        "SUCCESS",
                        f"추출된 기업코드: {corp_code}",
                    )
                    return corp_code

                elif isinstance(result_data, list) and len(result_data) > 0:
                    first_result = result_data[0]
                    if isinstance(first_result, dict) and "corp_code" in first_result:
                        corp_code = first_result["corp_code"]
                        print(
                            f"🔥🔥🔥 리스트 첫 번째 결과에서 기업코드 추출: {corp_code}"
                        )
                        log_step(
                            "🔍 기업코드 추출 성공",
                            "SUCCESS",
                            f"추출된 기업코드: {corp_code}",
                        )
                        return corp_code

                # 2. 새로운 MCP 응답 형식: "[TextContent(...)]" 문자열 처리
                elif isinstance(result_data, str):
                    print(f"🔥🔥🔥 MCP TextContent 문자열 형태 감지, 파싱 시도")
                    import re
                    import json

                    # TextContent의 text 부분 추출 (정규식 개선)
                    text_match = re.search(
                        r"text=\'([^\']*(?:\\.[^\']*)*)\'", result_data
                    )
                    if not text_match:
                        # 큰따옴표로도 시도
                        text_match = re.search(
                            r'text="([^"]*(?:\\.[^"]*)*)"', result_data
                        )

                    if text_match:
                        json_str = text_match.group(1)
                        print(f"🔥🔥🔥 추출된 JSON 문자열: {json_str[:200]}...")

                        try:
                            # JSON 파싱 시도
                            parsed_data = json.loads(json_str)
                            print(
                                f"🔥🔥🔥 JSON 파싱 성공! 파싱된 데이터 타입: {type(parsed_data)}"
                            )
                            log_step(
                                "🔍 JSON 파싱 성공",
                                "SUCCESS",
                                f"파싱된 데이터: {type(parsed_data)}",
                            )

                            # items 배열에서 정확한 기업명 매칭으로 corp_code 추출
                            if isinstance(parsed_data, dict) and "items" in parsed_data:
                                items = parsed_data["items"]
                                if isinstance(items, list) and len(items) > 0:
                                    # 1. 정확한 기업명 매칭 우선 (대소문자 구분 없이)
                                    search_name = corp_lookup_result.get(
                                        "company_name", ""
                                    ).lower()
                                    for item in items:
                                        if (
                                            isinstance(item, dict)
                                            and "corp_name" in item
                                            and "corp_code" in item
                                        ):
                                            item_name = item["corp_name"].lower()
                                            if item_name == search_name:
                                                corp_code = item["corp_code"]
                                                print(
                                                    f"🔥🔥🔥 정확한 기업명 매칭 성공: {item['corp_name']} → {corp_code}"
                                                )
                                                log_step(
                                                    "🔍 정확한 기업명 매칭",
                                                    "SUCCESS",
                                                    f"기업: {item['corp_name']}, 코드: {corp_code}",
                                                )
                                                return corp_code

                                    # 2. 정확한 매칭이 없으면 부분 매칭 (기업명이 포함된 경우)
                                    for item in items:
                                        if (
                                            isinstance(item, dict)
                                            and "corp_name" in item
                                            and "corp_code" in item
                                        ):
                                            item_name = item["corp_name"].lower()
                                            if (
                                                search_name in item_name
                                                or item_name in search_name
                                            ):
                                                corp_code = item["corp_code"]
                                                print(
                                                    f"🔥🔥🔥 부분 매칭 성공: {item['corp_name']} → {corp_code}"
                                                )
                                                log_step(
                                                    "🔍 부분 매칭",
                                                    "SUCCESS",
                                                    f"기업: {item['corp_name']}, 코드: {corp_code}",
                                                )
                                                return corp_code

                                    # 3. 모든 매칭 실패 시 첫 번째 항목 사용 (기존 로직)
                                    first_item = items[0]
                                    if (
                                        isinstance(first_item, dict)
                                        and "corp_code" in first_item
                                    ):
                                        corp_code = first_item["corp_code"]
                                        print(
                                            f"🔥🔥🔥 첫 번째 항목 사용: {first_item.get('corp_name', 'N/A')} → {corp_code}"
                                        )
                                        log_step(
                                            "🔍 첫 번째 항목 사용",
                                            "WARNING",
                                            f"기업: {first_item.get('corp_name', 'N/A')}, 코드: {corp_code}",
                                        )
                                        return corp_code

                            # 직접 corp_code가 있는 경우
                            elif (
                                isinstance(parsed_data, dict)
                                and "corp_code" in parsed_data
                            ):
                                corp_code = parsed_data["corp_code"]
                                print(
                                    f"🔥🔥🔥 MCP 응답에서 직접 기업코드 추출 성공: {corp_code}"
                                )
                                log_step(
                                    "🔍 기업코드 추출 성공",
                                    "SUCCESS",
                                    f"추출된 기업코드: {corp_code}",
                                )
                                return corp_code

                        except json.JSONDecodeError as e:
                            print(f"🔥🔥🔥 JSON 파싱 실패: {e}")
                            log_step("🔍 JSON 파싱 실패", "ERROR", f"오류: {e}")

                            # 정규식으로 직접 corp_code 추출 시도
                            corp_code_match = re.search(
                                r'"corp_code"\s*:\s*"([^"]+)"', json_str
                            )
                            if corp_code_match:
                                corp_code = corp_code_match.group(1)
                                print(
                                    f"🔥🔥🔥 정규식으로 기업코드 추출 성공: {corp_code}"
                                )
                                log_step(
                                    "🔍 기업코드 추출 성공",
                                    "SUCCESS",
                                    f"추출된 기업코드: {corp_code}",
                                )
                                return corp_code

                log_step(
                    "🔍 결과 처리 실패",
                    "WARNING",
                    f"result 데이터를 처리할 수 없음. 타입: {type(result_data)}",
                )
            else:
                log_step(
                    "🔍 result 필드 없음",
                    "WARNING",
                    f"result 필드가 없거나 비어있음. 사용 가능한 키: {list(corp_lookup_result.keys())}",
                )

            log_step(
                "기업코드 추출 실패", "WARNING", "조회 결과에서 기업코드를 찾을 수 없음"
            )
            return ""  # 빈 문자열 반환 (더미값 제거)
        except Exception as e:
            log_step("기업코드 추출 오류", "ERROR", f"오류: {str(e)}")
            return ""  # 빈 문자열 반환 (더미값 제거)

    def _get_default_classification_with_error(
        self, error_message: str
    ) -> IntentClassificationResult:
        """오류가 있는 기본 분류 결과 반환"""
        result = IntentClassificationResult(
            scope=AnalysisScope.SINGLE_COMPANY,
            domain=AnalysisDomain.FINANCIAL,
            depth=AnalysisDepth.INTERMEDIATE,
            required_agents=["financial"],
            recommended_agents=["financial"],
            reasoning=f"오류로 인한 기본 분류: {error_message}",
        )
        result.corp_info = None  # 기업 정보 없음을 명시
        return result
    
    def _get_default_classification(self) -> IntentClassificationResult:
        """기본 분류 결과 반환 (오류 시)"""
        return IntentClassificationResult(
            scope=AnalysisScope.SINGLE_COMPANY,
            domain=AnalysisDomain.FINANCIAL,
            depth=AnalysisDepth.INTERMEDIATE,
            required_agents=["financial"],
            recommended_agents=["financial"],
            reasoning="기본 분류 (오류 발생으로 인한 대체)",
        )

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
