"""
OTEL Metrics and Spans for Legislation Agent

OpenTelemetry 기반 trace + metrics 헬퍼 함수들.
"""

import logging
from typing import Dict, Any, Optional
from contextlib import contextmanager

logger = logging.getLogger(__name__)

_tracer = None
_service_tracers = {}
_active_service_name = "agent-legislation"


def set_active_service(service_name: str):
    """활성 서비스 이름 설정"""
    global _active_service_name
    _active_service_name = service_name
    logger.debug(f"Set active service to: {service_name}")


def _get_tracer():
    """Tracer 인스턴스 획득"""
    global _tracer, _service_tracers
    
    if _active_service_name in _service_tracers:
        return _service_tracers[_active_service_name]
    
    try:
        from app.telemetry.otel import get_tracer_for_service
        tracer = get_tracer_for_service(_active_service_name, "legislation-agent")
        _service_tracers[_active_service_name] = tracer
        logger.debug(f"Created tracer for service: {_active_service_name}")
        return tracer
    except ImportError:
        logger.warning("OTEL tracer not available, using no-op")
        return _NoOpTracer()
    except Exception as e:
        logger.warning(f"Failed to get tracer for {_active_service_name}: {e}")
        return _NoOpTracer()


class _NoOpSpan:
    def set_attribute(self, key, value):
        pass
    def set_status(self, status):
        pass
    def add_event(self, name, attributes=None):
        pass
    def __enter__(self):
        return self
    def __exit__(self, *args):
        pass


class _NoOpTracer:
    @contextmanager
    def start_as_current_span(self, name, attributes=None, **kwargs):
        yield _NoOpSpan()


def extract_context_from_carrier(carrier: Dict[str, str]):
    """carrier(dict)에서 trace context 추출"""
    try:
        from opentelemetry.propagate import extract
        return extract(carrier)
    except ImportError:
        return None
    except Exception as e:
        logger.debug(f"Failed to extract context: {e}")
        return None


@contextmanager
def start_legislation_span(
    name: str,
    attributes: Optional[Dict[str, Any]] = None,
    parent_carrier: Optional[Dict[str, str]] = None
):
    """
    Legislation 에이전트용 span 시작 (Context Propagation 지원).
    
    Args:
        name: Span 이름
        attributes: 추가 속성
        parent_carrier: 부모 span의 carrier (있으면 사용)
    """
    tracer = _get_tracer()
    
    span_attributes = {
        "agent.type": "legislation",
        "service.name": _active_service_name,
    }
    if attributes:
        span_attributes.update(attributes)
    
    # GenAI 표준 속성 추가 (모니터링 화면에서 인식)
    if "gen_ai.agent.id" not in span_attributes:
        span_attributes["gen_ai.agent.id"] = span_attributes.get("agent.id", "legislation-agent")
    if "gen_ai.agent.name" not in span_attributes:
        span_attributes["gen_ai.agent.name"] = span_attributes.get("agent.name", "Legislation Agent")
    if "gen_ai.agent.type" not in span_attributes:
        span_attributes["gen_ai.agent.type"] = "legislation"
    
    try:
        from opentelemetry.context import attach, detach
        
        # Parent context 추출 및 attach
        token = None
        if parent_carrier:
            parent_context = extract_context_from_carrier(parent_carrier)
            if parent_context:
                token = attach(parent_context)
        
        try:
            with tracer.start_as_current_span(name, attributes=span_attributes) as span:
                yield span
        finally:
            if token is not None:
                detach(token)
    except ImportError:
        yield _NoOpSpan()
    except Exception as e:
        logger.warning(f"Failed to create span {name}: {e}")
        yield _NoOpSpan()


def record_tool_call(tool_name: str, arguments: Dict[str, Any], result: Any, latency_ms: float):
    """도구 호출 기록"""
    logger.info(f"[Legislation Tool] {tool_name}: latency={latency_ms:.1f}ms, args={arguments}")


def inject_context_to_carrier(carrier: Dict[str, str]):
    """현재 context를 carrier에 주입"""
    try:
        from opentelemetry.propagate import inject
        inject(carrier)
    except ImportError:
        pass



