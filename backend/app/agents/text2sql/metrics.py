"""
OTEL Metrics and Spans for Text-to-SQL Agent

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 4, 8

OpenTelemetry 기반 trace + metrics 헬퍼 함수들.
Context Propagation을 통해 Parent-Child 관계의 트리 형태 트레이스를 지원.
"""

import logging
from typing import Dict, Any, Optional, TYPE_CHECKING
from contextlib import contextmanager

if TYPE_CHECKING:
    from .state import SqlAgentState

logger = logging.getLogger(__name__)

# OTEL tracer/meter는 telemetry/otel.py에서 초기화
_tracer = None
_meter = None
_counters = {}
_histograms = {}


def _get_tracer():
    """Tracer 인스턴스 획득 (지연 초기화)."""
    global _tracer
    if _tracer is None:
        try:
            from app.telemetry.otel import get_tracer
            _tracer = get_tracer("text2sql")
        except ImportError:
            logger.warning("OTEL tracer not available, using no-op")
            _tracer = _NoOpTracer()
    return _tracer


def _get_meter():
    """Meter 인스턴스 획득 (지연 초기화)."""
    global _meter
    if _meter is None:
        try:
            from app.telemetry.otel import get_meter
            _meter = get_meter("text2sql")
        except ImportError:
            logger.warning("OTEL meter not available, using no-op")
            _meter = _NoOpMeter()
    return _meter


class _NoOpSpan:
    """No-op span for when OTEL is not available."""
    def set_attribute(self, key, value):
        pass
    
    def set_status(self, status):
        pass
    
    def record_exception(self, exception):
        pass
    
    def end(self):
        pass
    
    def __enter__(self):
        return self
    
    def __exit__(self, *args):
        pass


class _NoOpTracer:
    """No-op tracer for when OTEL is not available."""
    def start_span(self, name, attributes=None):
        return _NoOpSpan()
    
    @contextmanager
    def start_as_current_span(self, name, attributes=None):
        yield _NoOpSpan()


class _NoOpMeter:
    """No-op meter for when OTEL is not available."""
    def create_counter(self, name, **kwargs):
        return _NoOpCounter()
    
    def create_histogram(self, name, **kwargs):
        return _NoOpHistogram()


class _NoOpCounter:
    """No-op counter."""
    def add(self, value, attributes=None):
        pass


class _NoOpHistogram:
    """No-op histogram."""
    def record(self, value, attributes=None):
        pass


def start_span(name: str, attributes: Optional[Dict[str, Any]] = None):
    """
    OTEL span 시작.
    
    Args:
        name: Span 이름 (예: "text2sql.planner")
        attributes: Span 속성
        
    Returns:
        Span 객체 (end_span으로 종료해야 함)
    """
    tracer = _get_tracer()
    
    attrs = {
        "service.name": "agent-text2sql",
        "component": "text2sql"
    }
    if attributes:
        attrs.update(attributes)
    
    try:
        span = tracer.start_span(name, attributes=attrs)
        return span
    except Exception as e:
        logger.warning(f"Failed to start span: {e}")
        return _NoOpSpan()


def end_span(span, error: Optional[Exception] = None):
    """
    OTEL span 종료.
    
    Args:
        span: 종료할 span
        error: 에러가 있으면 기록
    """
    try:
        if error:
            span.record_exception(error)
        span.end()
    except Exception as e:
        logger.warning(f"Failed to end span: {e}")


def record_counter(name: str, attributes: Optional[Dict[str, str]] = None, value: int = 1):
    """
    Counter 기록.
    
    Args:
        name: Counter 이름 (예: "text2sql_requests_total")
        attributes: 태그/라벨
        value: 증가량 (기본 1)
    """
    global _counters
    
    try:
        meter = _get_meter()
        
        if name not in _counters:
            _counters[name] = meter.create_counter(
                name,
                description=f"Counter for {name}"
            )
        
        _counters[name].add(value, attributes=attributes)
        
    except Exception as e:
        logger.debug(f"Failed to record counter {name}: {e}")


def record_histogram(name: str, value: float, attributes: Optional[Dict[str, str]] = None):
    """
    Histogram 기록.
    
    Args:
        name: Histogram 이름 (예: "text2sql_planning_latency_ms")
        value: 기록할 값
        attributes: 태그/라벨
    """
    global _histograms
    
    try:
        meter = _get_meter()
        
        if name not in _histograms:
            _histograms[name] = meter.create_histogram(
                name,
                description=f"Histogram for {name}"
            )
        
        _histograms[name].record(value, attributes=attributes)
        
    except Exception as e:
        logger.debug(f"Failed to record histogram {name}: {e}")


# ========== Context Propagation을 지원하는 새로운 함수들 ==========

def inject_context_to_carrier(carrier: Dict[str, str]) -> Dict[str, str]:
    """
    현재 span context를 carrier(dict)에 주입.
    W3C Trace Context 형식으로 traceparent, tracestate 저장.
    
    Args:
        carrier: context를 저장할 dict
        
    Returns:
        context가 주입된 carrier
    """
    try:
        from opentelemetry import trace
        from opentelemetry.propagate import inject
        
        inject(carrier)
        return carrier
    except ImportError:
        logger.debug("OpenTelemetry propagate not available")
        return carrier
    except Exception as e:
        logger.debug(f"Failed to inject context: {e}")
        return carrier


def extract_context_from_carrier(carrier: Dict[str, str]):
    """
    carrier(dict)에서 trace context 추출.
    
    Args:
        carrier: traceparent/tracestate가 있는 dict
        
    Returns:
        추출된 context 객체 (없으면 None)
    """
    try:
        from opentelemetry.propagate import extract
        
        return extract(carrier)
    except ImportError:
        logger.debug("OpenTelemetry propagate not available")
        return None
    except Exception as e:
        logger.debug(f"Failed to extract context: {e}")
        return None


@contextmanager
def start_agent_span(
    state: "SqlAgentState",
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    is_entry: bool = False
):
    """
    Agent 노드용 span 생성 (Context Propagation 지원).
    
    트리 구조:
    - text2sql.agent (root)
      └── text2sql.entry
          ├── text2sql.dialect_resolver
          ├── text2sql.schema_selector
          ├── text2sql.planner
          │   └── text2sql.llm_call.planner
          ├── text2sql.generator
          │   ├── text2sql.llm_call.generator_0
          │   └── text2sql.llm_call.generator_1
          ├── text2sql.executor
          └── text2sql.answer_formatter
              └── text2sql.llm_call.answer
    
    Args:
        state: SqlAgentState (otel_carrier, entry_carrier 포함)
        name: Span 이름 (예: "text2sql.planner")
        attributes: 추가 속성
        is_entry: entry 노드인 경우 True (entry_carrier 설정)
        
    Yields:
        현재 span 객체
    """
    tracer = _get_tracer()
    
    # 기본 속성
    attrs = {
        "service.name": "agent-text2sql",
        "component": "text2sql"
    }
    if attributes:
        attrs.update(attributes)
    
    # State에서 connection_id, dialect 등 추가
    if state.get("connection_id"):
        attrs["db.connection_id"] = state["connection_id"]
    if state.get("dialect"):
        attrs["dialect"] = state["dialect"]
    
    # agent.id와 agent.name은 root span에서 상속받거나 기본값 사용
    # root span에서 이미 설정되었으므로 여기서는 기본값만 설정 (없는 경우)
    if "agent.id" not in attrs:
        attrs["agent.id"] = "text2sql-agent"
    if "agent.name" not in attrs:
        attrs["agent.name"] = "Text-to-SQL Agent"
    
    try:
        from opentelemetry import trace
        from opentelemetry.context import attach, detach
        
        # Parent context 선택:
        # - entry 노드: otel_carrier (root span)에서 parent 읽기
        # - 그 외 노드: entry_carrier (entry span)에서 parent 읽기
        parent_carrier = state.get("otel_carrier") if is_entry else state.get("entry_carrier")
        
        parent_context = None
        token = None
        
        if parent_carrier:
            parent_context = extract_context_from_carrier(parent_carrier)
            if parent_context:
                token = attach(parent_context)
        
        try:
            with tracer.start_as_current_span(name, attributes=attrs) as span:
                # 새 span의 context를 저장
                new_carrier = {}
                inject_context_to_carrier(new_carrier)
                
                if is_entry:
                    # entry 노드: entry_carrier 설정 (다른 노드들의 parent)
                    state["entry_carrier"] = new_carrier
                
                # otel_carrier는 항상 현재 노드의 context로 업데이트 (LLM call용)
                state["otel_carrier"] = new_carrier
                
                yield span
        finally:
            if token is not None:
                detach(token)
                
    except ImportError:
        yield _NoOpSpan()
    except Exception as e:
        logger.warning(f"Failed to create span {name}: {e}")
        yield _NoOpSpan()


def get_trace_headers(state: "SqlAgentState") -> Dict[str, str]:
    """
    LLM 호출 시 전달할 trace context HTTP 헤더 반환.
    W3C Trace Context 형식 (traceparent, tracestate).
    
    Args:
        state: SqlAgentState
        
    Returns:
        HTTP 헤더로 사용할 dict (traceparent 등)
    """
    try:
        from opentelemetry.propagate import inject
        from opentelemetry import trace
        
        # 현재 context의 span을 carrier에 주입
        carrier = {}
        inject(carrier)
        
        return carrier
    except ImportError:
        return {}
    except Exception as e:
        logger.debug(f"Failed to get trace headers: {e}")
        return {}


def create_root_span_carrier(trace_id: Optional[str] = None) -> Dict[str, str]:
    """
    그래프 실행 전 root span 생성 및 carrier 반환.
    
    Args:
        trace_id: 외부에서 전달된 trace_id (있으면 사용)
        
    Returns:
        root span의 context가 담긴 carrier
    """
    tracer = _get_tracer()
    
    try:
        from opentelemetry import trace
        
        # Root span 생성
        with tracer.start_as_current_span(
            "text2sql.agent",
            attributes={
                "service.name": "agent-text2sql",
                "component": "text2sql",
                "span.kind": "server"
            }
        ) as root_span:
            # External trace_id가 있으면 속성으로 저장
            if trace_id:
                root_span.set_attribute("app.external_trace_id", trace_id)
            
            # Context를 carrier에 저장
            carrier = {}
            inject_context_to_carrier(carrier)
            
            return carrier
            
    except ImportError:
        return {}
    except Exception as e:
        logger.warning(f"Failed to create root span: {e}")
        return {}


@contextmanager
def start_llm_call_span(
    state: "SqlAgentState",
    node_name: str,
    model: str,
    messages: Optional[list] = None
):
    """
    LLM 호출용 span 생성 (Parent 노드의 child로 연결).
    
    LiteLLM의 자체 OTEL 트레이스와 별개로, text2sql 에이전트 내에서
    LLM 호출을 추적하여 완전한 트리 구조를 만듦.
    
    Args:
        state: SqlAgentState (otel_carrier 포함)
        node_name: 호출한 노드 이름 (예: "planner", "generator")
        model: LLM 모델명
        messages: LLM 요청 메시지 (request body)
        
    Yields:
        tuple: (span, result_recorder)
            - span: OTEL span 객체
            - result_recorder: LLM 응답 결과를 기록하는 callable
    
    Example:
        with start_llm_call_span(state, "planner", "qwen-235b", messages) as (span, record_result):
            response = await litellm_service.chat_completion_sync(...)
            record_result(response)
    """
    import time
    import json
    tracer = _get_tracer()
    span_name = f"text2sql.llm_call.{node_name}"
    
    # LLM 호출 Counter 증가 (가이드 섹션 8)
    record_counter("text2sql_llm_calls_total", {
        "node": node_name,
        "model": model
    })
    
    # 기본 속성
    attrs = {
        "service.name": "agent-text2sql",
        "component": "text2sql",
        "llm.model": model,
        "llm.node": node_name
    }
    
    # Request messages 저장 (최대 10000자로 제한하여 저장)
    if messages:
        try:
            request_json = json.dumps(messages, ensure_ascii=False)
            # 너무 길면 truncate
            if len(request_json) > 10000:
                request_json = request_json[:10000] + "... [truncated]"
            attrs["llm.request.messages"] = request_json
        except Exception:
            pass
    
    start_time = time.time()
    
    # Mutable container to hold the span (avoids nonlocal issues)
    span_holder = [None]
    
    # 결과 기록용 함수
    def record_result(response: Dict[str, Any]):
        """LLM 응답 결과를 span에 기록 + Histogram 기록"""
        try:
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # LLM Latency Histogram 기록 (가이드 섹션 8)
            record_histogram("text2sql_llm_latency_ms", latency_ms, {
                "node": node_name,
                "model": model
            })
            
            # LLM 토큰 Histogram 기록 (가이드 섹션 8)
            record_histogram("text2sql_llm_tokens_prompt", prompt_tokens, {
                "node": node_name,
                "model": model
            })
            record_histogram("text2sql_llm_tokens_completion", completion_tokens, {
                "node": node_name,
                "model": model
            })
            
            current_span = span_holder[0]
            if current_span and hasattr(current_span, 'set_attribute'):
                current_span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
                current_span.set_attribute("llm.usage.completion_tokens", completion_tokens)
                current_span.set_attribute("llm.usage.total_tokens", total_tokens)
                current_span.set_attribute("llm.latency_ms", latency_ms)
                
                # 모델명 (응답에서 가져오기)
                response_model = response.get("model", model)
                current_span.set_attribute("llm.response.model", response_model)
                
                # Response content 저장
                choices = response.get("choices", [])
                if choices:
                    first_choice = choices[0]
                    message = first_choice.get("message", {})
                    content = message.get("content", "")
                    # 너무 길면 truncate
                    if len(content) > 10000:
                        content = content[:10000] + "... [truncated]"
                    current_span.set_attribute("llm.response.content", content)
                    
                    # finish_reason
                    finish_reason = first_choice.get("finish_reason", "")
                    if finish_reason:
                        current_span.set_attribute("llm.response.finish_reason", finish_reason)
                
        except Exception as e:
            logger.debug(f"Failed to record LLM result: {e}")
    
    try:
        from opentelemetry import trace
        from opentelemetry.context import attach, detach
        
        # Parent context 추출 및 attach
        token = None
        if state.get("otel_carrier"):
            parent_context = extract_context_from_carrier(state["otel_carrier"])
            if parent_context:
                token = attach(parent_context)
        
        try:
            # LLM 호출 span 생성 (parent 노드의 child가 됨)
            with tracer.start_as_current_span(span_name, attributes=attrs) as span:
                # 현재 span을 기록용으로 저장
                span_holder[0] = span
                
                yield span, record_result
        finally:
            if token is not None:
                detach(token)
                
    except ImportError:
        span_holder[0] = _NoOpSpan()
        yield span_holder[0], record_result
    except Exception as e:
        logger.warning(f"Failed to create LLM call span: {e}")
        span_holder[0] = _NoOpSpan()
        yield span_holder[0], record_result

