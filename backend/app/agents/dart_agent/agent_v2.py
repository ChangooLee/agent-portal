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

중요 도메인 지식/가드레일:
- 생명보험/보험사 문맥에서 'CSM'은 일반적으로 IFRS17의 Contractual Service Margin(보험계약마진)을 의미합니다.
  이 경우 고객만족도 지수 등으로 오인하지 마세요.

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
                        temperature=0.0,
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
        # v2: keep broad toolset, but exclude known-bad/ambiguous tools that degrade reliability.
        deny = {
            # This tool has been observed to produce non-JSON-serializable bytes in some deployments.
            "get_corporation_code",
            # This meta tool often causes wasted iterations and higher latency; avoid in production runs.
            "get_opendart_tool_info",
        }
        filtered = []
        for t in tools or []:
            try:
                name = getattr(t, "name", None) or ""
            except Exception:
                name = ""
            if name in deny:
                continue
            filtered.append(t)
        return filtered

    def _create_system_prompt(self) -> str:
        base = "당신은 DART(전자공시시스템) 기반 기업공시 분석가입니다."
        domain_hint = {
            AnalysisDomain.FINANCIAL: (
                "재무제표/손익/현금흐름 중심으로 분석하세요. 숫자는 근거(공시/계정/기간)를 함께 제시하세요.\n"
                "특히 보험사/CSM(보험계약마진) 비교 요청 시:\n"
                "- '국내 3대 생보사'는 통상 삼성생명/한화생명/교보생명으로 가정하되, 가정임을 명시하세요.\n"
                "- 각 회사별로 corp_code를 정확히 식별한 뒤, 최신 분기/사업 보고서의 rcp_no를 찾으세요.\n"
                "- CSM은 주석에서 '보험계약마진' 키워드로 우선 검색하세요(필요 시 CSM/계약서비스이익/보험계약부채도 보조).\n"
                "- CSM 수치를 제시할 때는 rcp_no와 검색 결과의 table_id 또는 matched_content 일부(수치 포함)를 함께 인용하세요.\n"
                "- 근거가 없으면 '확인 불가'로 두고 숫자를 만들지 마세요.\n"
            ),
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
                "content": (
                    "사용자 질문에 대해 1~2문장으로만, 친근하고 단정한 한국어로 '무엇을 하겠다' 형태의 시작 안내를 작성하세요.\n"
                    "- 약어/지표(예: CSM)를 임의로 풀어쓰거나 정의하지 마세요.\n"
                    "- 아직 확인하지 않은 수치/순위를 단정하지 마세요.\n"
                    "- 공시/주석에서 근거를 찾아 비교하겠다는 계획만 말하세요.\n"
                    "이모지는 쓰지 마세요."
                ),
            },
            {"role": "user", "content": question},
        ]
        with start_llm_call_span("dart_v2_start_message", self.model, messages, parent_carrier) as (_span, record):
            resp = await self._intro_llm.chat(
                messages=messages,
                tools=None,
                trace_headers=get_trace_headers(),
                temperature=0.0,
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
                lines.append("#### 사용 도구(근거 요약)")
                import re
                for tc in tool_calls[:15]:
                    tool = tc.get("tool") or "unknown_tool"
                    args = tc.get("args") if isinstance(tc.get("args"), dict) else {}
                    rcp_no = tc.get("rcp_no") or args.get("rcp_no")
                    lines.append(f"- **{tool}**" + (f" (rcp_no: {rcp_no})" if rcp_no else ""))

                    # Prefer structured table evidence
                    tables = tc.get("tables") if isinstance(tc.get("tables"), list) else []
                    if tool == "search_financial_notes" and tables:
                        for t in tables[:5]:
                            if not isinstance(t, dict):
                                continue
                            table_id = t.get("table_id")
                            mc = (t.get("matched_content") or "").strip()
                            # Extract numeric after 보험계약마진 when present
                            m = re.search(r"보험계약마진\\s*([0-9][0-9,]*)", mc)
                            extracted = m.group(1) if m else None
                            if table_id:
                                lines.append(f"  - table_id: `{table_id}`" + (f", 보험계약마진 추출: **{extracted}**" if extracted else ""))
                            if mc:
                                lines.append(f"    - excerpt: {mc[:260]}{'...' if len(mc)>260 else ''}")
                    else:
                        # Fallback: preview
                        rp = (tc.get(\"result_preview\") or \"\").strip()
                        if rp:
                            lines.append(f\"  - excerpt: {rp[:260]}{'...' if len(rp)>260 else ''}\")
                lines.append("")

        lines.append("## 한계 및 추가 확인")
        lines.append("")
        lines.append("- 통합 LLM 응답이 비어있거나 실패하여, 수집된 결과를 기반으로 fallback 레포트를 생성했습니다.")
        lines.append("- 더 정확한 분석을 위해서는 공시 원문/주석 추출 결과가 충분히 제공되어야 합니다.")
        lines.append("")
        return "\n".join(lines).strip() + "\n"

    async def analyze_stream(
        self,
        question: str,
        session_id: Optional[str] = None,
        parent_carrier: Optional[Dict[str, str]] = None,
    ):
        start_time = time.time()
        # IMPORTANT:
        # - Prefer explicit parent_carrier from HTTP layer to guarantee a single TraceId
        #   across async generator boundaries.
        # - After we create the v2 span, we re-inject to get a carrier for THAT span so
        #   all downstream spans (intent/LLM/tool/sub-agents) become children of v2.
        root_carrier: Dict[str, str] = dict(parent_carrier or {})
        if not root_carrier:
            try:
                inject_context_to_carrier(root_carrier)
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

        with start_dart_span("dart_v2.analyze_stream", {"question_length": len(question)}, root_carrier) as span:
            # Correlation helper: store app-level ids on the v2 span too.
            try:
                if session_id:
                    span.set_attribute("trace_id", session_id)
                    span.set_attribute("session_id", session_id)
            except Exception:
                pass

            span_carrier: Dict[str, str] = {}
            try:
                inject_context_to_carrier(span_carrier)
            except Exception:
                span_carrier = dict(root_carrier)

            # 0) LLM-start message (client may show it)
            try:
                start_msg = await self._generate_start_message(question, span_carrier)
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
            intent = await self.intent_classifier.classify(question, span_carrier)
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

            def _normalize_tool_calls(tool_calls: Any) -> List[Dict[str, Any]]:
                """
                Normalize tool call results into a compact, cite-friendly structure.
                This improves answer quality by letting the integrator reference rcp_no/table_id/etc.
                """
                norm: List[Dict[str, Any]] = []
                if not isinstance(tool_calls, list):
                    return norm

                allow_tools = {
                    "get_corporation_code_by_name",
                    "get_corporation_info",
                    "get_disclosure_list",
                    "get_disclosure_document",
                    "search_financial_notes",
                }

                for tc in tool_calls[:60]:
                    if not isinstance(tc, dict):
                        continue
                    tool = tc.get("tool") or tc.get("tool_name") or "unknown_tool"
                    if tool not in allow_tools:
                        continue
                    args = tc.get("args") if isinstance(tc.get("args"), dict) else None
                    res = tc.get("result")

                    parsed = None
                    if isinstance(res, dict):
                        parsed = res
                    elif isinstance(res, str):
                        s = res.strip()
                        if s.startswith("{") and s.endswith("}"):
                            try:
                                parsed = json.loads(s)
                            except Exception:
                                parsed = None

                    item: Dict[str, Any] = {"tool": tool}
                    if args:
                        # keep small
                        item["args"] = {k: _safe_preview(v, 120) for k, v in list(args.items())[:10]}

                    # Extract structured evidence for key tools
                    if isinstance(parsed, dict):
                        # Common id fields
                        for k in ("rcp_no", "corp_code", "corporation_code", "corporation_name", "status", "status_code"):
                            if k in parsed and parsed.get(k) is not None:
                                item[k] = _safe_preview(parsed.get(k), 200)

                        if tool == "search_financial_notes":
                            results = parsed.get("results") or {}
                            tables = results.get("tables") or []
                            # Keep top matches only (these usually include table_id + matched_content)
                            ev_tables: List[Dict[str, Any]] = []
                            search_term = str(parsed.get("search_term") or "")
                            if isinstance(tables, list):
                                kept = 0
                                for t in tables:
                                    if not isinstance(t, dict):
                                        continue
                                    mc_raw = (t.get("matched_content") or "")
                                    # Prefer tables that actually contain the searched term (or CSM/보험계약마진)
                                    if search_term and search_term not in mc_raw and "보험계약마진" not in mc_raw and "CSM" not in mc_raw:
                                        continue
                                    ev_tables.append(
                                        {
                                            "table_id": t.get("table_id"),
                                            "section": t.get("section"),
                                            "context_type": t.get("context_type"),
                                            "matched_content": _safe_preview(mc_raw, 260),
                                        }
                                    )
                                    kept += 1
                                    if kept >= 3:
                                        break
                            item["tables"] = ev_tables
                            # Summary is useful for sanity
                            if "summary" in parsed:
                                item["summary"] = parsed.get("summary")

                        # Disclosure list helps cite rcp_no
                        if tool == "get_disclosure_list":
                            disclosures = parsed.get("items") or parsed.get("disclosures") or []
                            ev_disc: List[Dict[str, Any]] = []
                            if isinstance(disclosures, list):
                                for d in disclosures[:6]:
                                    if not isinstance(d, dict):
                                        continue
                                    ev_disc.append(
                                        {
                                            "rcp_no": d.get("rcp_no"),
                                            "report_nm": d.get("report_nm"),
                                            "rcept_dt": d.get("rcept_dt"),
                                        }
                                    )
                            item["disclosures"] = ev_disc
                    else:
                        # Fallback: keep a preview of raw string result (may include numbers)
                        if isinstance(res, str):
                            item["result_preview"] = _safe_preview(res, 600)

                    norm.append(item)
                    if len(norm) >= 15:
                        break

                return norm
            for domain in selected:
                agent = DartDomainAgent(domain=domain, model=self.model, max_iterations=10)
                ev = {"event": "analyzing", "message": f"{domain.value} 에이전트가 데이터를 수집 중입니다..."}
                _otel_record_event(span, ev, {"dart.domain": domain.value})
                yield ev

                done_payload: Optional[Dict[str, Any]] = None
                gen = agent.run_stream(question=question, session_id=session_id, parent_carrier=span_carrier)
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
                        "tool_calls": _normalize_tool_calls((done_payload or {}).get("tool_calls", [])),
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
- 숫자는 근거가 있으면 함께 표기 (특히 CSM/보험계약마진 등 주요 지표)
- 불확실하면 추측하지 말고 '확인 불가'로 표기

근거/추적 가능성 (중요):
- agent_results.tool_calls에는 MCP 도구 실행 결과(예: search_financial_notes)가 포함될 수 있습니다.
- 주요 수치(예: 회사별 CSM)를 제시할 때는 아래를 반드시 함께 포함하세요:
  - rcp_no(공시번호) 또는 해당 결과에서 확인 가능한 식별자
  - table_id(예: table_217) 또는 matched_content 일부(수치가 포함된 원문 일부)
  - 단위가 명시되어 있으면 단위를 그대로 쓰고, 단위가 불명확하면 '단위 확인 필요'로 표시
- 근거가 없는 수치는 절대 만들어내지 마세요.
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
                with start_llm_call_span("dart_v2_integrate", self.model, messages, span_carrier) as (_span, record):
                    resp = await self._intro_llm.chat(
                        messages=messages,
                        tools=None,
                        trace_headers=get_trace_headers(),
                        temperature=0.0,
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

            # Quality guardrail: if the integrator starts inventing evidence on CSM-style questions,
            # fall back to an evidence-only report derived from tool outputs.
            try:
                if any(k in question for k in ["CSM", "보험계약마진"]) and any(k in final_md for k in ["(추정", "가정 기반", "note_"]):
                    record_counter("dart_v2_report_fallback_total", {"reason": "unreliable_integration"})
                    final_md = self._build_fallback_report(question, intent, selected, sub_results)
            except Exception:
                pass

            # Post-process: fix common unit conversion mistakes (quality guardrail).
            # Example: "1,024,700백만원(102.47조원)" should be 1.02조원.
            try:
                import re

                def _fix_baekman_to_jo(m: re.Match) -> str:
                    bold = bool(m.groupdict().get("bold"))
                    raw = m.group("num")
                    try:
                        n = float(raw.replace(",", ""))
                    except Exception:
                        return m.group(0)
                    expected_jo = n / 1_000_000.0
                    # keep 2 decimals, strip trailing zeros
                    jo_txt = f"{expected_jo:.2f}".rstrip("0").rstrip(".")
                    if bold:
                        return f"**{raw}**백만원({jo_txt}조원)"
                    return f"{raw}백만원({jo_txt}조원)"

                # 1) Plain number
                final_md = re.sub(
                    r"(?P<num>[0-9][0-9,]*)\s*백만원\s*\(\s*(?P<jo>[0-9]+(?:\.[0-9]+)?)\s*조원\s*\)",
                    _fix_baekman_to_jo,
                    final_md,
                )
                # 2) Bold number (markdown)
                final_md = re.sub(
                    r"(?P<bold>\*\*)(?P<num>[0-9][0-9,]*)(?P=bold)\s*백만원\s*\(\s*(?P<jo>[0-9]+(?:\.[0-9]+)?)\s*조원\s*\)",
                    _fix_baekman_to_jo,
                    final_md,
                )
            except Exception:
                pass

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


