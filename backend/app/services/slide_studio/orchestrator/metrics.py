"""
OTEL Metrics and Spans for Slide Studio Agent

OpenTelemetry 기반 trace + metrics 헬퍼 함수들.
Context Propagation을 통해 Parent-Child 관계의 트리 형태 트레이스를 지원.
DART metrics.py 패턴 참조.
"""

import logging
import time
import json
from typing import Dict, Any, Optional
from contextlib import contextmanager

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
            from app.telemetry.otel import get_tracer_for_service
            # 서비스별 TracerProvider 사용 (service.name = "agent-slides")
            _tracer = get_tracer_for_service("agent-slides", "slide-studio")
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
            _meter = get_meter("slide-studio")
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


def record_counter(name: str, attributes: Optional[Dict[str, str]] = None, value: int = 1):
    """
    Counter 기록.
    
    Args:
        name: Counter 이름 (예: "slide_studio_llm_calls_total")
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
        name: Histogram 이름 (예: "slide_studio_llm_latency_ms")
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


def get_trace_headers(parent_carrier: Optional[Dict[str, str]] = None) -> Dict[str, str]:
    """
    LLM 호출 시 전달할 trace context HTTP 헤더 반환.
    W3C Trace Context 형식 (traceparent, tracestate).
    
    Args:
        parent_carrier: 부모 span의 carrier (있으면 사용, 없으면 현재 context 사용)
        
    Returns:
        HTTP 헤더로 사용할 dict (traceparent 등)
    """
    try:
        from opentelemetry.propagate import inject
        from opentelemetry import trace
        from opentelemetry.context import attach, detach
        
        # Parent carrier가 있으면 attach하여 사용
        token = None
        if parent_carrier:
            parent_context = extract_context_from_carrier(parent_carrier)
            if parent_context:
                token = attach(parent_context)
        
        try:
            # 현재 context의 span을 carrier에 주입
            carrier = {}
            inject(carrier)
            return carrier
        finally:
            if token is not None:
                detach(token)
                
    except ImportError:
        return {}
    except Exception as e:
        logger.debug(f"Failed to get trace headers: {e}")
        return {}


@contextmanager
def start_slide_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_carrier: Optional[Dict[str, str]] = None,
    parent_trace_id: Optional[str] = None
):
    """
    슬라이드 단계용 span 생성 (Context Propagation 지원).
    
    Args:
        name: Span 이름 (예: "gen_ai.agent.slide_drafting")
        attributes: 추가 속성
        parent_carrier: 부모 span의 carrier (있으면 사용)
        parent_trace_id: 부모 trace_id (metadata로 저장)
        
    Yields:
        현재 span 객체
    """
    tracer = _get_tracer()
    
    # 기본 속성 (Span Attributes)
    attrs = {
        "component": "slide-studio"
    }
    if attributes:
        attrs.update(attributes)
    
    # GenAI 표준: agent.id와 agent.name (Span Attributes에 설정)
    # ResourceAttributes는 tracer의 resource에 설정되어야 하지만,
    # 모니터링 화면에서 조회할 때는 SpanAttributes도 확인하므로 여기에도 설정
    if "agent.id" not in attrs:
        attrs["agent.id"] = attrs.get("agent.id", "slide-studio")
    if "agent.name" not in attrs:
        attrs["agent.name"] = attrs.get("agent.name", "Slide Studio Agent")
    if "agent.type" not in attrs:
        attrs["agent.type"] = attrs.get("agent.type", "slides")
    
    # GenAI 표준: gen_ai.agent.id와 gen_ai.agent.name
    if "gen_ai.agent.id" not in attrs:
        attrs["gen_ai.agent.id"] = attrs.get("agent.id", "slide-studio")
    if "gen_ai.agent.name" not in attrs:
        attrs["gen_ai.agent.name"] = attrs.get("agent.name", "Slide Studio Agent")
    
    # parent_trace_id를 metadata로 저장
    if parent_trace_id:
        attrs["metadata.parent_trace_id"] = parent_trace_id
    
    try:
        from opentelemetry import trace
        from opentelemetry.context import attach, detach
        
        # Parent context 추출 및 attach
        token = None
        if parent_carrier:
            parent_context = extract_context_from_carrier(parent_carrier)
            if parent_context:
                token = attach(parent_context)
        
        try:
            with tracer.start_as_current_span(name, attributes=attrs) as span:
                yield span
        finally:
            if token is not None:
                detach(token)
                
    except ImportError:
        yield _NoOpSpan()
    except Exception as e:
        logger.warning(f"Failed to create span {name}: {e}")
        yield _NoOpSpan()


@contextmanager
def start_llm_call_span(
    node_name: str,
    model: str,
    messages: Optional[list] = None,
    parent_carrier: Optional[Dict[str, str]] = None,
    parent_trace_id: Optional[str] = None
):
    """
    LLM 호출용 span 생성 (Parent 노드의 child로 연결).
    
    Args:
        node_name: 호출한 노드 이름 (예: "slide_builder", "deck_planner")
        model: LLM 모델명
        messages: LLM 요청 메시지 (request body)
        parent_carrier: 부모 span의 carrier
        parent_trace_id: 부모 trace_id (metadata로 저장)
        
    Yields:
        tuple: (span, result_recorder)
            - span: OTEL span 객체
            - result_recorder: LLM 응답 결과를 기록하는 callable
    
    Example:
        with start_llm_call_span("slide_builder", "qwen-235b", messages, parent_carrier, parent_trace_id) as (span, record_result):
            response = await litellm_service.chat_completion_sync(...)
            record_result(response)
    """
    tracer = _get_tracer()
    # GenAI 표준 span 이름
    span_name = "gen_ai.content.completion"
    
    # LLM 호출 Counter 증가
    record_counter("slide_studio_llm_calls_total", {
        "node": node_name,
        "model": model
    })
    
    # GenAI 표준 속성
    attrs = {
        "service.name": "agent-slide-studio",
        "component": "slide-studio",
        "gen_ai.operation.name": "completion",
        "gen_ai.system": "litellm",
        "gen_ai.request.model": model,
        "gen_ai.agent.name": f"slide-studio.{node_name}"
    }
    
    # parent_trace_id를 metadata로 저장
    if parent_trace_id:
        attrs["metadata.parent_trace_id"] = parent_trace_id
    
    # Request messages 저장 (GenAI 표준: 각 프롬프트를 개별 속성으로)
    if messages:
        try:
            for i, msg in enumerate(messages[:5]):
                role = msg.get("role", "") if isinstance(msg, dict) else ""
                content = msg.get("content", "") if isinstance(msg, dict) else str(msg)
                if role:
                    attrs[f"gen_ai.prompt.{i}.role"] = role
                if content:
                    content_str = str(content)[:5000] if len(str(content)) > 5000 else str(content)
                    attrs[f"gen_ai.prompt.{i}.content"] = content_str
        except Exception:
            pass
    
    start_time = time.time()
    
    # Mutable container to hold the span (avoids nonlocal issues)
    span_holder = [None]
    
    # 결과 기록용 함수 (GenAI 표준)
    def record_result(response: Dict[str, Any]):
        """LLM 응답 결과를 span에 기록 + Histogram 기록 (GenAI 표준)"""
        try:
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)
            
            latency_ms = (time.time() - start_time) * 1000
            
            # LLM Latency Histogram 기록
            record_histogram("slide_studio_llm_latency_ms", latency_ms, {
                "node": node_name,
                "model": model
            })
            
            # LLM 토큰 Histogram 기록
            record_histogram("slide_studio_llm_tokens_prompt", prompt_tokens, {
                "node": node_name,
                "model": model
            })
            record_histogram("slide_studio_llm_tokens_completion", completion_tokens, {
                "node": node_name,
                "model": model
            })
            
            current_span = span_holder[0]
            if current_span and hasattr(current_span, 'set_attribute'):
                # GenAI 표준 속성
                current_span.set_attribute("gen_ai.usage.prompt_tokens", prompt_tokens)
                current_span.set_attribute("gen_ai.usage.completion_tokens", completion_tokens)
                current_span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
                current_span.set_attribute("gen_ai.latency_ms", latency_ms)
                
                # 모델명 (응답에서 가져오기)
                response_model = response.get("model", model)
                current_span.set_attribute("gen_ai.response.model", response_model)
                
                # Response content 저장
                choices = response.get("choices", [])
                if choices:
                    first_choice = choices[0]
                    message = first_choice.get("message", {})
                    content = message.get("content", "")
                    # 너무 길면 truncate
                    if len(content) > 10000:
                        content = content[:10000] + "... [truncated]"
                    current_span.set_attribute("gen_ai.completion.0.content", content)
                    
                    # finish_reason
                    finish_reason = first_choice.get("finish_reason", "")
                    if finish_reason:
                        current_span.set_attribute("gen_ai.response.finish_reason", finish_reason)
                
        except Exception as e:
            logger.debug(f"Failed to record LLM result: {e}")
    
    try:
        from opentelemetry import trace
        from opentelemetry.context import attach, detach
        
        # Parent context 추출 및 attach
        token = None
        if parent_carrier:
            parent_context = extract_context_from_carrier(parent_carrier)
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
