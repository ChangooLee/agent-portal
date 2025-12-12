"""
OTEL Metrics and Spans for DART Agent

OpenTelemetry 기반 trace + metrics 헬퍼 함수들.
text2sql/metrics.py 패턴 참조.
"""

import logging
import json
import time
from typing import Dict, Any, Optional, List, TYPE_CHECKING
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
            from app.telemetry.otel import get_tracer
            _tracer = get_tracer("dart-agent")
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
            _meter = get_meter("dart-agent")
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
    
    def __enter__(self, *args):
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


# =============================================================================
# Context Propagation 함수들
# =============================================================================

def inject_context_to_carrier(carrier: Dict[str, str]) -> Dict[str, str]:
    """현재 span context를 carrier(dict)에 주입."""
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
    """carrier(dict)에서 trace context 추출."""
    try:
        from opentelemetry.propagate import extract
        return extract(carrier)
    except ImportError:
        logger.debug("OpenTelemetry propagate not available")
        return None
    except Exception as e:
        logger.debug(f"Failed to extract context: {e}")
        return None


def get_trace_headers() -> Dict[str, str]:
    """LLM 호출 시 전달할 trace context HTTP 헤더 반환."""
    try:
        from opentelemetry.propagate import inject
        carrier = {}
        inject(carrier)
        return carrier
    except ImportError:
        return {}
    except Exception as e:
        logger.debug(f"Failed to get trace headers: {e}")
        return {}


# =============================================================================
# Span 헬퍼 함수들
# =============================================================================

@contextmanager
def start_dart_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_carrier: Optional[Dict[str, str]] = None
):
    """
    DART Agent용 span 생성.
    
    Args:
        name: Span 이름 (예: "dart.intent_classify", "dart.financial_analysis")
        attributes: 추가 속성
        parent_carrier: 부모 context carrier (있으면 child로 연결)
        
    Yields:
        현재 span 객체
    """
    """
    NOTE (CRITICAL):
    - Generator-based context managers MUST yield exactly once.
    - If this function yields again while handling an exception thrown into the generator
      (contextmanager __exit__ uses generator.throw), Python raises:
        RuntimeError: generator didn't stop after throw()
    """
    from contextlib import nullcontext

    tracer = _get_tracer()

    # 기본 속성
    attrs = {"service.name": "agent-dart", "component": "dart-agent"}
    if attributes:
        attrs.update(attributes)

    token = None
    try:
        # Parent context attach (optional)
        try:
            from opentelemetry.context import attach
            if parent_carrier:
                parent_context = extract_context_from_carrier(parent_carrier)
                if parent_context:
                    token = attach(parent_context)
        except Exception:
            token = None

        # Span context manager (fallback to no-op)
        try:
            span_cm = tracer.start_as_current_span(name, attributes=attrs)
        except Exception as e:
            logger.debug(f"Failed to create span {name}: {e}")
            span_cm = nullcontext(_NoOpSpan())

        with span_cm as span:
            yield span
    finally:
        if token is not None:
            try:
                from opentelemetry.context import detach
                detach(token)
            except Exception:
                pass


@contextmanager
def start_llm_call_span(
    node_name: str,
    model: str,
    messages: Optional[List[Dict[str, Any]]] = None,
    parent_carrier: Optional[Dict[str, str]] = None
):
    """
    LLM 호출용 span 생성.
    
    Args:
        node_name: 호출한 노드 이름 (예: "intent_classifier", "financial_agent")
        model: LLM 모델명
        messages: LLM에 전달된 메시지
        parent_carrier: 부모 context carrier
        
    Yields:
        tuple: (span, result_recorder)
    """
    from contextlib import nullcontext

    tracer = _get_tracer()
    span_name = f"dart.llm_call.{node_name}"

    attrs = {
        "service.name": "agent-dart",
        "component": "dart-agent",
        "llm.model": model,
        "llm.node": node_name,
    }

    start_time = time.time()
    span_holder: List[Any] = [_NoOpSpan()]

    def record_result(response: Dict[str, Any]):
        """LLM 응답 결과를 span에 기록"""
        try:
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            latency_ms = (time.time() - start_time) * 1000
            current_span = span_holder[0]
            if current_span and hasattr(current_span, "set_attribute"):
                current_span.set_attribute("llm.usage.prompt_tokens", prompt_tokens)
                current_span.set_attribute("llm.usage.completion_tokens", completion_tokens)
                current_span.set_attribute("llm.usage.total_tokens", total_tokens)
                current_span.set_attribute("llm.latency_ms", latency_ms)

                response_model = response.get("model", model)
                current_span.set_attribute("llm.response.model", response_model)

                response_content = (
                    response.get("choices", [{}])[0].get("message", {}).get("content")
                )
                if response_content:
                    current_span.set_attribute("llm.response.content", response_content[:1000])
        except Exception as e:
            logger.debug(f"Failed to record LLM result: {e}")

    token = None
    try:
        # Parent context attach (optional)
        try:
            from opentelemetry.context import attach
            if parent_carrier:
                parent_context = extract_context_from_carrier(parent_carrier)
                if parent_context:
                    token = attach(parent_context)
        except Exception:
            token = None

        # Span context manager (fallback to no-op)
        try:
            span_cm = tracer.start_as_current_span(span_name, attributes=attrs)
        except Exception as e:
            logger.debug(f"Failed to create LLM call span {span_name}: {e}")
            span_cm = nullcontext(_NoOpSpan())

        with span_cm as span:
            span_holder[0] = span
            try:
                if messages and hasattr(span, "set_attribute"):
                    span.set_attribute(
                        "llm.request.messages",
                        json.dumps(messages, ensure_ascii=False)[:2000],
                    )
            except Exception:
                pass
            yield span, record_result
    finally:
        if token is not None:
            try:
                from opentelemetry.context import detach
                detach(token)
            except Exception:
                pass


@contextmanager
def start_tool_call_span(
    tool_name: str,
    arguments: Optional[Dict[str, Any]] = None,
    parent_carrier: Optional[Dict[str, str]] = None
):
    """
    MCP Tool 호출용 span 생성.
    
    Args:
        tool_name: 도구 이름
        arguments: 도구 인자
        parent_carrier: 부모 context carrier
        
    Yields:
        tuple: (span, result_recorder)
    """
    from contextlib import nullcontext

    tracer = _get_tracer()
    span_name = f"dart.tool_call.{tool_name}"

    attrs = {"service.name": "agent-dart", "component": "dart-agent", "tool.name": tool_name}

    start_time = time.time()
    span_holder: List[Any] = [_NoOpSpan()]

    def record_result(result: Any, error: Optional[str] = None):
        """Tool 호출 결과를 span에 기록"""
        try:
            latency_ms = (time.time() - start_time) * 1000
            current_span = span_holder[0]
            if current_span and hasattr(current_span, "set_attribute"):
                current_span.set_attribute("tool.latency_ms", latency_ms)
                current_span.set_attribute("tool.success", error is None)
                if error:
                    current_span.set_attribute("tool.error", error)
                elif result:
                    result_str = (
                        json.dumps(result, ensure_ascii=False)
                        if isinstance(result, (dict, list))
                        else str(result)
                    )
                    current_span.set_attribute("tool.result", result_str[:1000])
        except Exception as e:
            logger.debug(f"Failed to record tool result: {e}")

    token = None
    try:
        # Parent context attach (optional)
        try:
            from opentelemetry.context import attach
            if parent_carrier:
                parent_context = extract_context_from_carrier(parent_carrier)
                if parent_context:
                    token = attach(parent_context)
        except Exception:
            token = None

        # Span context manager (fallback to no-op)
        try:
            span_cm = tracer.start_as_current_span(span_name, attributes=attrs)
        except Exception as e:
            logger.debug(f"Failed to create tool call span {span_name}: {e}")
            span_cm = nullcontext(_NoOpSpan())

        with span_cm as span:
            span_holder[0] = span
            try:
                if arguments and hasattr(span, "set_attribute"):
                    span.set_attribute(
                        "tool.arguments",
                        json.dumps(arguments, ensure_ascii=False)[:1000],
                    )
            except Exception:
                pass
            yield span, record_result
    finally:
        if token is not None:
            try:
                from opentelemetry.context import detach
                detach(token)
            except Exception:
                pass


# =============================================================================
# Metrics 헬퍼 함수들
# =============================================================================

def record_counter(name: str, attributes: Optional[Dict[str, str]] = None, value: int = 1):
    """Counter 기록."""
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
    """Histogram 기록."""
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


