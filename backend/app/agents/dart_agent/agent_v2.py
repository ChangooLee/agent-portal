"""
DART Agent v2 (multi-pass / multi-agent orchestration).

This is the only supported DART engine going forward.
Legacy implementation lives in `app.agents.dart_agent.agent` and is deprecated.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from .base import DartBaseAgent, LiteLLMAdapter
from .metrics import start_dart_span, start_llm_call_span, record_counter, record_histogram, inject_context_to_carrier, get_trace_headers

logger = logging.getLogger(__name__)


class AnalysisDomain(Enum):
    FINANCIAL = "financial"
    GOVERNANCE = "governance"
    BUSINESS_STRUCTURE = "business_structure"
    CAPITAL_CHANGE = "capital_change"
    DEBT_FUNDING = "debt_funding"
    OVERSEAS_BUSINESS = "overseas_business"
    LEGAL_COMPLIANCE = "legal_compliance"
    EXECUTIVE_AUDIT = "executive_audit"
    DOCUMENT_ANALYSIS = "document_analysis"
    GENERAL = "general"


@dataclass
class IntentResult:
    domain: AnalysisDomain
    company_name: Optional[str] = None
    keywords: List[str] = field(default_factory=list)
    reasoning: str = ""


INTENT_SYSTEM_PROMPT = """당신은 DART(전자공시시스템) 관련 사용자 질문을 분석하는 의도 분류기입니다.

주어진 질문을 분석하여 다음을 판단하세요:

1) 분석 영역(domain):
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

2) 회사명(company_name): 질문에서 언급된 회사명 추출 (없으면 null)
3) 핵심 키워드(keywords): 분석에 필요한 핵심 키워드 3-5개

반드시 아래 JSON 형식으로만 응답하세요:
{
  "domain": "financial",
  "company_name": "삼성전자",
  "keywords": ["재무제표", "매출", "영업이익"],
  "reasoning": "..."
}
"""


class IntentClassifier:
    def __init__(self, model: str = "qwen-235b"):
        self.model = model
        self.llm = LiteLLMAdapter(model)

    async def classify(self, question: str, parent_carrier: Optional[Dict[str, str]] = None) -> IntentResult:
        with start_dart_span("dart_v2.intent_classify", {"question_length": len(question)}, parent_carrier):
            messages = [
                {"role": "system", "content": INTENT_SYSTEM_PROMPT},
                {"role": "user", "content": question},
            ]
            with start_llm_call_span("dart_v2_intent_classifier", self.model, messages, parent_carrier) as (_span, record):
                try:
                    resp = await self.llm.chat(
                        messages=messages,
                        tools=None,
                        trace_headers=get_trace_headers(),
                        temperature=0.1,
                        max_tokens=500,
                        metadata={"agent_id": "dart-v2-intent-classifier"},
                    )
                    record(resp)
                except Exception as e:
                    logger.error("Intent classification failed: %s", e, exc_info=True)
                    return IntentResult(domain=AnalysisDomain.GENERAL, reasoning=f"분류 실패: {e}")

            content = resp.get("choices", [{}])[0].get("message", {}).get("content", "") or ""
            try:
                parsed = json.loads(content)
            except Exception:
                # Fallback: try extract first JSON object
                import re

                m = re.search(r"\{[\s\S]*\}", content)
                if not m:
                    return IntentResult(domain=AnalysisDomain.GENERAL, reasoning="파싱 실패")
                try:
                    parsed = json.loads(m.group())
                except Exception:
                    return IntentResult(domain=AnalysisDomain.GENERAL, reasoning="파싱 실패")

            domain_str = (parsed.get("domain") or "general").strip()
            try:
                domain = AnalysisDomain(domain_str)
            except Exception:
                domain = AnalysisDomain.GENERAL

            return IntentResult(
                domain=domain,
                company_name=parsed.get("company_name"),
                keywords=parsed.get("keywords") or [],
                reasoning=parsed.get("reasoning") or "",
            )


class DartDomainAgent(DartBaseAgent):
    def __init__(self, domain: AnalysisDomain, model: str = "qwen-235b", max_iterations: int = 10):
        super().__init__(agent_name=f"dart_v2_{domain.value}", model=model, max_iterations=max_iterations)
        self.domain = domain

    async def _filter_tools(self, tools):
        # v2: keep full toolset for reliability. Tool narrowing can be added later.
        return tools

    def _create_system_prompt(self) -> str:
        base = "당신은 DART(전자공시시스템) 기반 기업공시 분석가입니다."
        domain_hint = {
            AnalysisDomain.FINANCIAL: "재무제표/손익/현금흐름 중심으로 분석하세요. 숫자는 근거(공시/계정/기간)를 함께 제시하세요.",
            AnalysisDomain.GOVERNANCE: "지배구조/주주/이사회/내부통제 중심으로 분석하세요. 핵심 리스크와 변화를 요약하세요.",
            AnalysisDomain.BUSINESS_STRUCTURE: "사업구조/자회사/세그먼트 중심으로 분석하세요. 사업 포트폴리오/리스크를 구조화하세요.",
            AnalysisDomain.CAPITAL_CHANGE: "자본변동/증자/주식 관련 이벤트를 요약하고 영향도를 평가하세요.",
            AnalysisDomain.DEBT_FUNDING: "부채/자금조달(회사채/차입/CP) 중심으로 분석하세요. 만기/금리/리스크를 포함하세요.",
            AnalysisDomain.OVERSEAS_BUSINESS: "해외사업/수출/환리스크/해외법인 중심으로 분석하세요.",
            AnalysisDomain.LEGAL_COMPLIANCE: "소송/제재/규정준수 관점에서 리스크를 평가하세요.",
            AnalysisDomain.EXECUTIVE_AUDIT: "임원/감사/보수/특수관계자 거래 관점에서 요약하세요.",
            AnalysisDomain.DOCUMENT_ANALYSIS: "공시 문서의 핵심 문구/표/근거를 인용하며 요약하세요.",
            AnalysisDomain.GENERAL: "질문 의도에 맞춰 필요한 공시 데이터부터 확인하고 분석하세요.",
        }.get(self.domain, "")
        fmt = """\n\n응답은 반드시 Markdown으로 구조화하세요:
- 핵심 요약
- 근거 데이터(표/리스트)
- 해석 및 시사점
- (필요시) 한계/추가 확인 항목
"""
        return f"{base}\n\n[분석영역] {self.domain.value}\n{domain_hint}{fmt}"


class DartV2Agent:
    """
    v2 Orchestrator:
    intent classify -> run selected domain agents -> integrate -> SSE events
    """

    def __init__(self, model: str = "qwen-235b"):
        self.model = model
        self.intent_classifier = IntentClassifier(model=model)
        self._intro_llm = LiteLLMAdapter(model)

    async def _generate_start_message(self, question: str, parent_carrier: Optional[Dict[str, str]] = None) -> str:
        messages = [
            {
                "role": "system",
                "content": "사용자 질문에 대해 1~2문장으로만, 친근하고 단정한 한국어로 '무엇을 하겠다' 형태의 시작 안내를 작성하세요. 이모지는 쓰지 마세요.",
            },
            {"role": "user", "content": question},
        ]
        with start_llm_call_span("dart_v2_start_message", self.model, messages, parent_carrier) as (_span, record):
            resp = await self._intro_llm.chat(
                messages=messages,
                tools=None,
                trace_headers=get_trace_headers(),
                temperature=0.2,
                max_tokens=120,
                metadata={"agent_id": "dart-v2-start-message"},
            )
            record(resp)
        return resp.get("choices", [{}])[0].get("message", {}).get("content", "").strip() or "분석을 시작하겠습니다."

    def _select_domains(self, intent: IntentResult, question: str) -> List[AnalysisDomain]:
        # 최소 1개는 항상 선택
        domains: List[AnalysisDomain] = [intent.domain]
        q = question.lower()

        # Heuristic multi-agent expansion (safe & conservative)
        if any(k in q for k in ["지배구조", "이사회", "주주", "감사", "내부통제"]):
            if AnalysisDomain.GOVERNANCE not in domains:
                domains.append(AnalysisDomain.GOVERNANCE)
        if any(k in q for k in ["소송", "제재", "규정", "컴플라이언스"]):
            if AnalysisDomain.LEGAL_COMPLIANCE not in domains:
                domains.append(AnalysisDomain.LEGAL_COMPLIANCE)
        if any(k in q for k in ["보고서", "공시문서", "사업보고서", "분기보고서"]):
            if AnalysisDomain.DOCUMENT_ANALYSIS not in domains:
                domains.append(AnalysisDomain.DOCUMENT_ANALYSIS)

        # Upper bound to keep latency reasonable
        return domains[:3]

    def _build_fallback_report(self, question: str, intent: IntentResult, selected: List[AnalysisDomain], sub_results: List[Dict[str, Any]]) -> str:
        """
        Fallback report generator when integration LLM fails or returns empty.
        Uses collected agent answers/tools to produce a deterministic Markdown report.
        """
        company = intent.company_name or "N/A"
        lines: List[str] = []
        lines.append("## 분석 요약")
        lines.append("")
        lines.append(f"- 질문: {question}")
        lines.append(f"- 분류: {intent.domain.value}")
        if intent.company_name:
            lines.append(f"- 대상: {company}")
        if intent.keywords:
            lines.append(f"- 키워드: {', '.join(intent.keywords[:10])}")
        lines.append("")

        lines.append("## 수집된 결과")
        lines.append("")
        lines.append(f"- 실행된 에이전트: {', '.join([d.value for d in selected]) if selected else 'N/A'}")
        lines.append("")

        for r in sub_results:
            domain = r.get("domain") or "unknown"
            ans = (r.get("answer") or "").strip()
            tool_calls = r.get("tool_calls") or []
            lines.append(f"### {domain}")
            lines.append("")
            if ans:
                lines.append(ans)
            else:
                lines.append("- (해당 도메인에서 최종 요약을 생성하지 못했습니다. 도구 실행 로그/수집 데이터만 제공합니다.)")
            lines.append("")

            if tool_calls:
                lines.append("#### 사용 도구(요약)")
                for tc in tool_calls[:12]:
                    tool = tc.get("tool") or "unknown_tool"
                    # Avoid huge payloads
                    result_preview = (tc.get("result") or "").strip()
                    if len(result_preview) > 200:
                        result_preview = result_preview[:200] + "..."
                    lines.append(f"- **{tool}**: {result_preview}")
                lines.append("")

        lines.append("## 한계 및 추가 확인")
        lines.append("")
        lines.append("- 통합 LLM 응답이 비어있거나 실패하여, 수집된 결과를 기반으로 fallback 레포트를 생성했습니다.")
        lines.append("- 더 정확한 분석을 위해서는 공시 원문/주석 추출 결과가 충분히 제공되어야 합니다.")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    async def analyze_stream(self, question: str, session_id: Optional[str] = None):
        start_time = time.time()
        carrier: Dict[str, str] = {}
        try:
            inject_context_to_carrier(carrier)
        except Exception:
            pass

        def _safe_preview(val: Any, limit: int = 200) -> str:
            try:
                s = str(val or "")
            except Exception:
                return ""
            s = s.replace("\n", " ").replace("\r", " ").strip()
            return s[:limit] + ("..." if len(s) > limit else "")

        def _otel_record_event(span: Any, ev: Dict[str, Any], extra: Optional[Dict[str, Any]] = None):
            event_type = str(ev.get("event") or "unknown")
            attrs: Dict[str, Any] = {
                "dart.stream.event": event_type,
                "dart.session_id": session_id or "",
                "dart.model": self.model,
            }
            if "domain" in ev and ev.get("domain"):
                attrs["dart.domain"] = str(ev.get("domain"))
            if event_type in {"tool_start", "tool_end"}:
                if ev.get("tool_name"):
                    attrs["dart.tool_name"] = str(ev.get("tool_name"))
                if ev.get("tool"):
                    attrs["dart.tool_name"] = str(ev.get("tool"))
            if event_type in {"error"}:
                attrs["dart.error"] = _safe_preview(ev.get("error"), 300)
            if event_type in {"answer", "done"}:
                content = ev.get("content") or ev.get("answer") or ""
                try:
                    attrs["dart.report_length"] = int(len(str(content)))
                except Exception:
                    pass
            if extra:
                # Keep attributes small and safe
                for k, v in extra.items():
                    if v is None:
                        continue
                    if isinstance(v, (int, float, bool)):
                        attrs[k] = v
                    else:
                        attrs[k] = _safe_preview(v, 200)

            # Metrics: count every streamed event
            try:
                record_counter("dart_v2_stream_events_total", {"event": event_type})
            except Exception:
                pass

            # Span event
            try:
                if span is not None and hasattr(span, "add_event"):
                    span.add_event(f"sse.{event_type}", attributes=attrs)
            except Exception:
                pass

        with start_dart_span("dart_v2.analyze_stream", {"question_length": len(question)}, carrier) as span:
            # 0) LLM-start message (client may show it)
            try:
                start_msg = await self._generate_start_message(question, carrier)
                ev = {"event": "start", "content": start_msg}
                _otel_record_event(span, ev)
                yield ev
            except Exception as e:
                logger.debug("Failed to generate start message: %s", e)
                ev = {"event": "start"}
                _otel_record_event(span, ev, {"dart.start_msg_error": str(e)})
                yield ev

            # 1) intent
            ev = {"event": "analyzing", "message": "질문 의도를 분류하고 있습니다..."}
            _otel_record_event(span, ev)
            yield ev
            intent = await self.intent_classifier.classify(question, carrier)
            ev = {
                "event": "intent_classified",
                "domain": intent.domain.value,
                "company_name": intent.company_name,
                "reasoning": intent.reasoning,
            }
            _otel_record_event(span, ev, {"dart.company_name": intent.company_name or ""})
            yield ev

            selected = self._select_domains(intent, question)
            ev = {"event": "analyzing", "message": f"선택된 분석 에이전트: {', '.join([d.value for d in selected])}"}
            _otel_record_event(span, ev, {"dart.selected_domains": ",".join([d.value for d in selected])})
            yield ev

            # 2) run domain agents (sequential to keep tool logs ordered)
            sub_results: List[Dict[str, Any]] = []
            for domain in selected:
                agent = DartDomainAgent(domain=domain, model=self.model, max_iterations=10)
                ev = {"event": "analyzing", "message": f"{domain.value} 에이전트가 데이터를 수집 중입니다..."}
                _otel_record_event(span, ev, {"dart.domain": domain.value})
                yield ev

                done_payload: Optional[Dict[str, Any]] = None
                gen = agent.run_stream(question=question, session_id=session_id, parent_carrier=carrier)
                try:
                    async for ev in gen:
                        # Forward tool/iteration events for UI log
                        if ev.get("event") in {"iteration", "tool_start", "tool_end"}:
                            out = {**ev, "domain": domain.value}
                            _otel_record_event(span, out)
                            yield out
                        elif ev.get("event") == "error":
                            # Don't leak internal connectivity details to the UI.
                            logger.warning("Sub-agent error (%s): %s", domain.value, ev.get("error"))
                            out = {
                                "event": "analyzing",
                                "message": "일부 분석 단계에서 일시적 오류가 발생했지만 가능한 범위에서 결과를 생성 중입니다...",
                            }
                            _otel_record_event(span, out, {"dart.domain": domain.value, "dart.sub_agent_error": ev.get("error")})
                            yield out
                        if ev.get("event") == "done":
                            done_payload = ev
                finally:
                    try:
                        await gen.aclose()
                    except Exception:
                        pass

                sub_results.append(
                    {
                        "domain": domain.value,
                        "answer": (done_payload or {}).get("answer", ""),
                        "tool_calls": (done_payload or {}).get("tool_calls", []),
                        "tokens": (done_payload or {}).get("tokens", {"prompt": 0, "completion": 0, "total": 0}),
                    }
                )

            # 3) integrate (LLM)
            ev = {"event": "analyzing", "message": "수집된 결과를 통합하여 최종 레포트를 작성 중입니다..."}
            _otel_record_event(span, ev)
            yield ev
            integration_prompt = {
                "role": "system",
                "content": """당신은 여러 전문 분석 에이전트의 결과를 통합하여 하나의 최종 레포트를 작성합니다.

요구사항:
- 반드시 Markdown으로 작성
- 섹션을 '## ' 헤더로 분리 (최소 3개)
- 숫자는 근거가 있으면 함께 표기
- 불확실하면 추측하지 말고 '확인 불가'로 표기
""",
            }
            integration_input = {
                "role": "user",
                "content": json.dumps(
                    {
                        "question": question,
                        "intent": {
                            "domain": intent.domain.value,
                            "company_name": intent.company_name,
                            "keywords": intent.keywords,
                        },
                        "agent_results": sub_results,
                    },
                    ensure_ascii=False,
                ),
            }
            messages = [integration_prompt, integration_input]

            resp: Optional[Dict[str, Any]] = None
            final_md: str = ""
            integrate_error: Optional[str] = None
            try:
                with start_llm_call_span("dart_v2_integrate", self.model, messages, carrier) as (_span, record):
                    resp = await self._intro_llm.chat(
                        messages=messages,
                        tools=None,
                        trace_headers=get_trace_headers(),
                        temperature=0.2,
                        max_tokens=1800,
                        metadata={"agent_id": "dart-v2-integrator"},
                    )
                    record(resp)
                final_md = (resp or {}).get("choices", [{}])[0].get("message", {}).get("content", "") or ""
                final_md = final_md.strip()
            except Exception as e:
                integrate_error = str(e)
                logger.error("Integration LLM failed: %s", e, exc_info=True)

            # Fallback conditions: integration failed OR empty/too short output
            fallback_reason: Optional[str] = None
            if integrate_error:
                fallback_reason = "integrate_error"
            elif not final_md:
                fallback_reason = "integrate_empty"
            elif len(final_md) < 80:
                fallback_reason = "integrate_too_short"

            if fallback_reason:
                record_counter("dart_v2_report_fallback_total", {"reason": fallback_reason})
                logger.warning(
                    "Using fallback report (reason=%s, company=%s, domains=%s)",
                    fallback_reason,
                    intent.company_name,
                    ",".join([d.value for d in selected]),
                )
                final_md = self._build_fallback_report(question, intent, selected, sub_results)
                _otel_record_event(span, {"event": "analyzing", "message": "통합 LLM 응답이 불안정하여 fallback 레포트를 생성했습니다."}, {"dart.fallback_reason": fallback_reason})

            # Merge token usage (best-effort)
            merged_tokens = {"prompt": 0, "completion": 0, "total": 0}
            for r in sub_results:
                t = r.get("tokens") or {}
                merged_tokens["prompt"] += int(t.get("prompt", 0) or 0)
                merged_tokens["completion"] += int(t.get("completion", 0) or 0)
                merged_tokens["total"] += int(t.get("total", 0) or 0)

            usage = resp.get("usage") or {}
            merged_tokens["prompt"] += int(usage.get("prompt_tokens", 0) or 0)
            merged_tokens["completion"] += int(usage.get("completion_tokens", 0) or 0)
            merged_tokens["total"] += int(usage.get("total_tokens", 0) or 0)

            total_latency = (time.time() - start_time) * 1000
            record_counter("dart_v2_requests_total", {"domain": intent.domain.value})
            record_histogram("dart_v2_latency_ms", total_latency, {"domain": intent.domain.value})

            ev = {"event": "answer", "content": final_md}
            _otel_record_event(span, ev, {"dart.total_latency_ms": total_latency})
            yield ev
            ev = {
                "event": "done",
                "answer": final_md,
                "tokens": merged_tokens,
                "total_latency_ms": total_latency,
            }
            _otel_record_event(span, ev, {"dart.total_latency_ms": total_latency, "dart.tokens_total": merged_tokens.get("total", 0)})
            yield ev
            ev = {
                "event": "complete",
                "total_latency_ms": total_latency,
                "intent": {"domain": intent.domain.value, "company_name": intent.company_name},
            }
            _otel_record_event(span, ev, {"dart.total_latency_ms": total_latency})
            yield ev


_dart_v2_agent: Optional[DartV2Agent] = None


def get_dart_agent(model: str = "qwen-235b") -> DartV2Agent:
    global _dart_v2_agent
    if _dart_v2_agent is None or _dart_v2_agent.model != model:
        _dart_v2_agent = DartV2Agent(model=model)
    return _dart_v2_agent


