"""
DART Agent - Agent Portal용 기업공시분석 에이전트

LiteLLM + OpenDart MCP 기반 멀티에이전트 시스템.
원본 dart_agent.py, intent_classifier_agent.py 참조하여 간소화.
"""

import warnings
warnings.warn(
    "app.agents.dart_agent.agent is deprecated. Use app.agents.dart_agent.agent_v2 instead (v2 only).",
    DeprecationWarning,
    stacklevel=2,
)

import json
import logging
import time
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from dataclasses import dataclass, field

from .base import DartBaseAgent
from .mcp_client import MCPTool, get_opendart_mcp_client
from .metrics import (
    start_dart_span, start_llm_call_span,
    record_counter, record_histogram, get_trace_headers, inject_context_to_carrier
)

logger = logging.getLogger(__name__)


# =============================================================================
# 분석 영역 정의
# =============================================================================

class AnalysisDomain(Enum):
    """분석 영역"""
    FINANCIAL = "financial"              # 재무 분석
    GOVERNANCE = "governance"            # 지배구조
    BUSINESS_STRUCTURE = "business_structure"  # 사업구조
    CAPITAL_CHANGE = "capital_change"    # 자본변동
    DEBT_FUNDING = "debt_funding"        # 부채/자금조달
    OVERSEAS_BUSINESS = "overseas_business"  # 해외사업
    LEGAL_COMPLIANCE = "legal_compliance"  # 법률/규정
    EXECUTIVE_AUDIT = "executive_audit"  # 임원/감사
    DOCUMENT_ANALYSIS = "document_analysis"  # 문서분석
    GENERAL = "general"                  # 일반 질문


# 도메인별 도구 필터 (원본 참조)
DOMAIN_TOOL_FILTERS: Dict[AnalysisDomain, List[str]] = {
    AnalysisDomain.FINANCIAL: [
        "search_financial_single", "search_financial_ratio",
        "get_quarterly_financials", "get_annual_financials",
        "get_stock_info", "get_company_overview"
    ],
    AnalysisDomain.GOVERNANCE: [
        "search_governance", "get_directors_info",
        "get_major_shareholders", "get_audit_opinion"
    ],
    AnalysisDomain.BUSINESS_STRUCTURE: [
        "search_business", "get_subsidiary_info",
        "get_segment_info", "get_business_description"
    ],
    AnalysisDomain.CAPITAL_CHANGE: [
        "search_capital_change", "get_stock_issuance",
        "get_treasury_stock", "get_capital_increase"
    ],
    AnalysisDomain.DEBT_FUNDING: [
        "search_debt_funding", "get_bond_info",
        "get_loan_info", "get_cp_info"
    ],
    AnalysisDomain.OVERSEAS_BUSINESS: [
        "search_overseas", "get_overseas_subsidiary",
        "get_export_info", "get_forex_exposure"
    ],
    AnalysisDomain.LEGAL_COMPLIANCE: [
        "search_legal", "get_lawsuit_info",
        "get_penalty_info", "get_compliance_violation"
    ],
    AnalysisDomain.EXECUTIVE_AUDIT: [
        "search_executive", "get_executive_compensation",
        "get_related_party_transaction", "get_internal_audit"
    ],
    AnalysisDomain.DOCUMENT_ANALYSIS: [
        "search_disclosure", "get_disclosure_detail",
        "get_annual_report", "get_quarterly_report"
    ],
    AnalysisDomain.GENERAL: []  # 모든 도구 사용 가능
}


@dataclass
class IntentResult:
    """의도 분류 결과"""
    domain: AnalysisDomain
    company_name: Optional[str] = None
    company_code: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    reasoning: str = ""


# =============================================================================
# 의도 분류기
# =============================================================================

INTENT_SYSTEM_PROMPT = """당신은 DART(전자공시시스템) 관련 사용자 질문을 분석하는 의도 분류기입니다.

주어진 질문을 분석하여 다음을 판단하세요:

1. **분석 영역 (domain)**: 질문이 어떤 분야에 해당하는지 분류
   - financial: 재무제표, 매출, 이익, 현금흐름 등 재무 분석
   - governance: 이사회, 주주, 지배구조, 의결권 관련
   - business_structure: 사업 구조, 자회사, 계열사 관련
   - capital_change: 유상증자, 무상증자, 자본 변동
   - debt_funding: 회사채, 차입금, 자금조달
   - overseas_business: 해외 법인, 수출, 외환
   - legal_compliance: 소송, 제재, 규정 위반
   - executive_audit: 임원 보수, 감사 의견, 내부 거래
   - document_analysis: 공시문서 조회, 보고서 분석
   - general: 위 분류에 해당하지 않는 일반 질문

2. **회사명**: 질문에서 언급된 회사명 추출 (없으면 null)

3. **핵심 키워드**: 분석에 필요한 핵심 키워드 3-5개 추출

반드시 아래 JSON 형식으로 응답하세요:
```json
{
  "domain": "financial",
  "company_name": "삼성전자",
  "keywords": ["재무제표", "매출", "영업이익"],
  "reasoning": "사용자가 삼성전자의 재무 현황을 질문하여 financial 도메인으로 분류"
}
```
"""


class IntentClassifier:
    """의도 분류기"""
    
    def __init__(self, model: str = "qwen-235b"):
        self.model = model
        self._litellm_service = None
    
    @property
    def litellm_service(self):
        if self._litellm_service is None:
            from app.services.litellm_service import litellm_service
            self._litellm_service = litellm_service
        return self._litellm_service
    
    async def classify(
        self,
        question: str,
        parent_carrier: Optional[Dict[str, str]] = None
    ) -> IntentResult:
        """의도 분류 수행"""
        
        with start_dart_span("dart.intent_classify", {"question_length": len(question)}, parent_carrier) as span:
            messages = [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": question}
            ]
            
            with start_llm_call_span("intent_classifier", self.model, messages, parent_carrier) as (llm_span, record):
                try:
                    response = await self.litellm_service.chat_completion_sync(
                        model=self.model,
                        messages=messages,
                        temperature=0.1,
                        max_tokens=500,
                        trace_headers=get_trace_headers(),
                        metadata={"agent_id": "dart-intent-classifier"}
                    )
                    record(response)
                except Exception as e:
                    logger.error(f"Intent classification failed: {e}")
                    return IntentResult(domain=AnalysisDomain.GENERAL, reasoning=f"분류 실패: {e}")
            
            # 응답 파싱
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            try:
                # JSON 추출
                import re
                json_match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group())
                    
                    domain_str = parsed.get("domain", "general")
                    try:
                        domain = AnalysisDomain(domain_str)
                    except ValueError:
                        domain = AnalysisDomain.GENERAL
                    
                    result = IntentResult(
                        domain=domain,
                        company_name=parsed.get("company_name"),
                        keywords=parsed.get("keywords", []),
                        reasoning=parsed.get("reasoning", "")
                    )
                    
                    if hasattr(span, 'set_attribute'):
                        span.set_attribute("intent.domain", domain.value)
                        span.set_attribute("intent.company", result.company_name or "")
                    
                    return result
                    
            except json.JSONDecodeError as e:
                logger.warning(f"Intent JSON parse failed: {e}")
            
            return IntentResult(domain=AnalysisDomain.GENERAL, reasoning="파싱 실패")


# =============================================================================
# DART 메인 에이전트
# =============================================================================

DART_SYSTEM_PROMPT_TEMPLATE = """당신은 DART(전자공시시스템) 전문 분석가입니다.

**사용자 질문**: {question}
**분석 영역**: {domain}
{company_info}

## 분석 가이드라인

1. 사용자 질문을 정확히 이해하고 관련 공시 정보를 조회하세요.
2. 조회한 데이터를 바탕으로 통찰력 있는 분석을 제공하세요.
3. 숫자 데이터는 명확한 출처와 함께 제시하세요.
4. 불확실한 정보는 추측하지 말고 "해당 정보를 찾을 수 없습니다"라고 말하세요.

## 응답 형식

분석 결과를 명확하고 구조화된 형식으로 제공하세요:
- 핵심 발견 사항을 먼저 요약
- 상세 데이터와 근거 제시
- 필요시 리스크 요소나 주의사항 언급
"""


class DartAgent(DartBaseAgent):
    """DART 기업공시분석 에이전트"""
    
    def __init__(
        self,
        model: str = "qwen-235b",
        max_iterations: int = 10
    ):
        super().__init__(
            agent_name="dart_agent",
            model=model,
            max_iterations=max_iterations
        )
        self.intent_classifier = IntentClassifier(model)
        self._current_domain: Optional[AnalysisDomain] = None
        self._current_company: Optional[str] = None
    
    async def _filter_tools(self, tools: List[MCPTool]) -> List[MCPTool]:
        """도메인에 따라 도구 필터링"""
        if self._current_domain is None or self._current_domain == AnalysisDomain.GENERAL:
            # 일반 질문은 모든 도구 사용
            return tools
        
        # 도메인별 도구 필터
        allowed_prefixes = DOMAIN_TOOL_FILTERS.get(self._current_domain, [])
        
        if not allowed_prefixes:
            return tools
        
        filtered = []
        for tool in tools:
            # 정확히 매칭하거나 prefix로 시작하면 포함
            if any(tool.name == prefix or tool.name.startswith(prefix) for prefix in allowed_prefixes):
                filtered.append(tool)
        
        # 필터링된 도구가 너무 적으면 전체 도구 사용
        if len(filtered) < 3:
            logger.info(f"Too few tools after filtering ({len(filtered)}), using all tools")
            return tools
        
        return filtered
    
    def _create_system_prompt(self) -> str:
        """시스템 프롬프트 생성"""
        company_info = ""
        if self._current_company:
            company_info = f"**분석 대상 회사**: {self._current_company}\n"
        
        return DART_SYSTEM_PROMPT_TEMPLATE.format(
            question=getattr(self, '_current_question', ''),
            domain=self._current_domain.value if self._current_domain else 'general',
            company_info=company_info
        )
    
    async def analyze(
        self,
        question: str,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        DART 분석 실행.
        
        1. 의도 분류
        2. 도구 필터링
        3. 에이전트 실행
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            
        Returns:
            분석 결과
        """
        with start_dart_span("dart.analyze", {"question_length": len(question)}) as span:
            current_carrier = {}
            inject_context_to_carrier(current_carrier)
            
            start_time = time.time()
            
            # 1. 의도 분류
            intent = await self.intent_classifier.classify(question, current_carrier)
            logger.info(f"Intent classified: domain={intent.domain.value}, company={intent.company_name}")
            
            self._current_domain = intent.domain
            self._current_company = intent.company_name
            self._current_question = question
            
            # 도구 다시 필터링 (도메인 변경됨)
            self._initialized = False
            
            # 2. 에이전트 실행
            result = await self.run(question, session_id, current_carrier)
            
            # 결과에 메타데이터 추가
            result["intent"] = {
                "domain": intent.domain.value,
                "company_name": intent.company_name,
                "keywords": intent.keywords,
                "reasoning": intent.reasoning
            }
            
            total_latency = (time.time() - start_time) * 1000
            result["total_latency_ms"] = total_latency
            
            if hasattr(span, 'set_attribute'):
                span.set_attribute("intent.domain", intent.domain.value)
                span.set_attribute("intent.company", intent.company_name or "")
                span.set_attribute("total_latency_ms", total_latency)
            
            record_counter("dart_analyze_requests_total", {"domain": intent.domain.value})
            record_histogram("dart_analyze_latency_ms", total_latency, {"domain": intent.domain.value})
            
            return result
    
    async def analyze_stream(
        self,
        question: str,
        session_id: Optional[str] = None
    ):
        """
        DART 분석 실행 (스트리밍).
        
        Args:
            question: 사용자 질문
            session_id: 세션 ID
            
        Yields:
            스트림 이벤트
        """
        # start_dart_span() 호출을 안전하게 처리 (pickle 오류 등 예외 발생 가능)
        try:
            span_context = start_dart_span("dart.analyze_stream", {"question_length": len(question)})
        except Exception as span_error:
            logger.warning(f"Failed to create span dart.analyze_stream: {span_error}")
            # span 생성 실패해도 계속 진행 (no-op context manager 사용)
            from contextlib import nullcontext
            span_context = nullcontext()
        
        # span context 사용 (예외 발생해도 계속 진행)
        try:
            with span_context:
                current_carrier = {}
                try:
                    inject_context_to_carrier(current_carrier)
                except Exception:
                    pass  # context injection 실패해도 계속 진행
                
                start_time = time.time()
                
                try:
                    yield {"event": "analyzing", "message": "질문을 분석하고 있습니다..."}
                except Exception as yield_error:
                    logger.error(f"Failed to yield analyzing event: {yield_error}")
                
                # 1. 의도 분류
                try:
                    intent = await self.intent_classifier.classify(question, current_carrier)
                    
                    try:
                        yield {
                            "event": "intent_classified",
                            "domain": intent.domain.value,
                            "company_name": intent.company_name,
                            "reasoning": intent.reasoning
                        }
                    except Exception as yield_error:
                        logger.error(f"Failed to yield intent_classified event: {yield_error}")
                    
                    self._current_domain = intent.domain
                    self._current_company = intent.company_name
                    self._current_question = question
                    self._initialized = False
                except Exception as e:
                    logger.error(f"Intent classification failed in analyze_stream: {e}")
                    try:
                        yield {"event": "error", "error": f"의도 분류 실패: {str(e)}"}
                    except Exception as yield_error:
                        logger.error(f"Failed to yield error event: {yield_error}")
                    try:
                        yield {
                            "event": "complete",
                            "total_latency_ms": (time.time() - start_time) * 1000,
                            "intent": {"domain": "general", "company_name": None},
                            "error": str(e)
                        }
                    except Exception as yield_error:
                        logger.error(f"Failed to yield complete event: {yield_error}")
                    return
                
                # 2. 스트리밍 에이전트 실행
                # 참고 프로젝트 패턴: async for 루프를 try-except로 감싸서 예외를 내부에서 처리
                # initialize()를 먼저 호출하여 실패 시 generator를 시작하지 않도록 함
                try:
                    await self.initialize()
                except Exception as init_error:
                    logger.error(f"Agent initialization failed in analyze_stream: {init_error}", exc_info=True)
                    try:
                        yield {"event": "error", "error": f"에이전트 초기화 실패: {str(init_error)}"}
                    except Exception as yield_error:
                        logger.error(f"Failed to yield initialization error event: {yield_error}")
                    try:
                        yield {
                            "event": "complete",
                            "total_latency_ms": (time.time() - start_time) * 1000,
                            "intent": {
                                "domain": intent.domain.value,
                                "company_name": intent.company_name
                            },
                            "error": str(init_error)
                        }
                    except Exception as yield_error:
                        logger.error(f"Failed to yield complete event after initialization error: {yield_error}")
                    return  # generator 종료
                
                # 초기화 성공 후 run_stream() 호출
                run_stream_gen = None
                try:
                    run_stream_gen = self.run_stream(question, session_id, current_carrier)
                    # async for 루프를 try-except로 감싸서 예외를 내부에서 처리
                    try:
                        async for event in run_stream_gen:
                            try:
                                yield event
                            except Exception as yield_error:
                                logger.error(f"Failed to yield event from run_stream: {yield_error}")
                                # yield 실패 시 루프 종료
                                break
                    except StopAsyncIteration:
                        # 정상 종료
                        pass
                    except GeneratorExit:
                        # Generator가 종료됨
                        pass
                    except Exception as loop_error:
                        # async for 루프 내부에서 예외 발생 시 처리
                        logger.error(f"Error in run_stream loop: {loop_error}", exc_info=True)
                        # 에러 이벤트 yield 시도
                        try:
                            yield {"event": "error", "error": f"에이전트 실행 중 오류: {str(loop_error)}"}
                        except Exception as yield_error:
                            logger.error(f"Failed to yield error event: {yield_error}")
                    finally:
                        # generator 정리 시도 (예외 발생 여부와 관계없이)
                        if run_stream_gen:
                            try:
                                await run_stream_gen.aclose()
                            except (StopAsyncIteration, GeneratorExit):
                                # 정상 종료 또는 이미 종료됨
                                pass
                            except Exception as close_error:
                                logger.debug(f"run_stream_gen.aclose() failed: {close_error}")
                except Exception as e:
                    # run_stream() 호출 자체에서 예외 발생 시 처리
                    logger.error(f"Agent run_stream failed in analyze_stream: {e}", exc_info=True)
                    try:
                        yield {"event": "error", "error": f"에이전트 실행 실패: {str(e)}"}
                    except Exception as yield_error:
                        logger.error(f"Failed to yield error event: {yield_error}")
                
                total_latency = (time.time() - start_time) * 1000
                
                yield {
                    "event": "complete",
                    "total_latency_ms": total_latency,
                    "intent": {
                        "domain": intent.domain.value,
                        "company_name": intent.company_name
                    }
                }
        except Exception as e:
            # 최상위 예외 처리: generator가 정상적으로 종료되도록 보장
            logger.error(f"Unexpected error in analyze_stream: {e}", exc_info=True)
            try:
                yield {"event": "error", "error": f"예기치 않은 오류: {str(e)}"}
            except Exception as yield_error:
                logger.error(f"Failed to yield error event in exception handler: {yield_error}")
            try:
                yield {
                    "event": "complete",
                    "total_latency_ms": 0,
                    "intent": {"domain": "general", "company_name": None},
                    "error": str(e)
                }
            except Exception as yield_error:
                logger.error(f"Failed to yield complete event in exception handler: {yield_error}")


# =============================================================================
# 싱글톤 인스턴스
# =============================================================================

_dart_agent: Optional[DartAgent] = None


def get_dart_agent(model: str = "qwen-235b") -> DartAgent:
    """DART 에이전트 싱글톤 반환"""
    global _dart_agent
    if _dart_agent is None:
        _dart_agent = DartAgent(model=model)
    return _dart_agent


