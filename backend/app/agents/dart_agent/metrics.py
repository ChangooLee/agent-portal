"""
OTEL Metrics and Spans for DART Agent

OpenTelemetry 기반 trace + metrics 헬퍼 함수들.
text2sql/metrics.py 패턴 참조.
"""

import logging
import json
import time
import functools
import inspect
from typing import Dict, Any, Optional, List, TYPE_CHECKING, AsyncGenerator, Callable, get_origin
from collections.abc import AsyncGenerator as ABCAsyncGenerator
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

    def add_event(self, name: str, attributes: Optional[Dict[str, Any]] = None):
        # Match OpenTelemetry Span API shape (best-effort).
        # This is intentionally a no-op.
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
    # GenAI Semantic Convention 표준 span 이름
    span_name = "gen_ai.content.completion"

    # GenAI 표준 속성
    attrs = {
        "service.name": "agent-dart",
        "component": "dart-agent",
        # GenAI 표준 속성
        "gen_ai.operation.name": "completion",
        "gen_ai.system": "litellm",
        "gen_ai.request.model": model,
        "gen_ai.agent.name": node_name,
    }

    start_time = time.time()
    span_holder: List[Any] = [_NoOpSpan()]

    def record_result(response: Dict[str, Any]):
        """LLM 응답 결과를 span에 기록 (GenAI 표준)"""
        try:
            usage = response.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            total_tokens = usage.get("total_tokens", prompt_tokens + completion_tokens)

            latency_ms = (time.time() - start_time) * 1000
            current_span = span_holder[0]
            if current_span and hasattr(current_span, "set_attribute"):
                # GenAI 표준 속성
                current_span.set_attribute("gen_ai.usage.prompt_tokens", prompt_tokens)
                current_span.set_attribute("gen_ai.usage.completion_tokens", completion_tokens)
                current_span.set_attribute("gen_ai.usage.total_tokens", total_tokens)
                current_span.set_attribute("gen_ai.latency_ms", latency_ms)

                response_model = response.get("model", model)
                current_span.set_attribute("gen_ai.response.model", response_model)

                response_content = (
                    response.get("choices", [{}])[0].get("message", {}).get("content")
                )
                if response_content:
                    current_span.set_attribute("gen_ai.completion.0.content", response_content)
                
                # finish_reason
                finish_reason = response.get("choices", [{}])[0].get("finish_reason", "")
                if finish_reason:
                    current_span.set_attribute("gen_ai.response.finish_reason", finish_reason)
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
                    # GenAI 표준: 각 프롬프트를 개별 속성으로 기록 (최대 5개)
                    for i, msg in enumerate(messages[:5]):
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if role:
                            span.set_attribute(f"gen_ai.prompt.{i}.role", role)
                        if content:
                            # 너무 길면 truncate
                            content_str = str(content)[:5000] if len(str(content)) > 5000 else str(content)
                            span.set_attribute(f"gen_ai.prompt.{i}.content", content_str)
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
    # GenAI Semantic Convention 표준 span 이름
    span_name = "gen_ai.tool.call"
    
    # 디버그 로그
    logger.info(f"[start_tool_call_span] Creating span: {span_name}, tool: {tool_name}, tracer type: {type(tracer).__name__}")

    # GenAI 표준 속성
    attrs = {
        "service.name": "agent-dart",
        "component": "dart-agent",
        "gen_ai.operation.name": "tool_call",
        "gen_ai.tool.name": tool_name,
    }

    start_time = time.time()
    span_holder: List[Any] = [_NoOpSpan()]

    def record_result(result: Any, error: Optional[str] = None):
        """Tool 호출 결과를 span에 기록 (GenAI 표준)"""
        try:
            latency_ms = (time.time() - start_time) * 1000
            current_span = span_holder[0]
            if current_span and hasattr(current_span, "set_attribute"):
                # GenAI 표준 속성
                current_span.set_attribute("gen_ai.tool.latency_ms", latency_ms)
                current_span.set_attribute("gen_ai.tool.success", error is None)
                if error:
                    current_span.set_attribute("gen_ai.tool.error", error)
                elif result:
                    result_str = (
                        json.dumps(result, ensure_ascii=False)
                        if isinstance(result, (dict, list))
                        else str(result)
                    )
                    current_span.set_attribute("gen_ai.tool.result", result_str)
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
                    # GenAI 표준 속성
                    span.set_attribute(
                        "gen_ai.tool.arguments",
                        json.dumps(arguments, ensure_ascii=False),
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


# =============================================================================
# 공통 observe 데코레이터 (OTEL span 자동 생성)
# =============================================================================

def _serialize_value(value: Any) -> str:
    """값을 JSON 문자열로 직렬화 (길이 제한 없음)."""
    try:
        import inspect
        # coroutine 객체는 직렬화 불가
        if inspect.iscoroutine(value):
            return f"<coroutine {type(value).__name__}>"
        # 함수 객체는 이름만 기록
        elif callable(value) and not isinstance(value, (str, int, float, bool, type(None))):
            return f"<function {getattr(value, '__name__', 'unknown')}>"
        elif isinstance(value, (dict, list)):
            return json.dumps(value, ensure_ascii=False, default=str)
        elif isinstance(value, str):
            return value
        else:
            return str(value)
    except Exception as e:
        return f"<serialization_error: {str(e)}>"


def observe(span_name: Optional[str] = None, include_args: bool = True, include_result: bool = True):
    """
    OTEL span을 자동으로 생성하는 데코레이터.
    
    모든 에이전트 메서드에 적용하여 자동으로 OTEL trace를 기록합니다.
    길이 제한 없이 전체 내용을 기록합니다.
    
    Args:
        span_name: Span 이름 (기본값: 함수명)
        include_args: 함수 인자를 span에 기록할지 여부
        include_result: 함수 반환값을 span에 기록할지 여부
    
    Usage:
        @observe()
        async def analyze_financial_data(self, context: AnalysisContext):
            ...
    """
    # start_dart_span과 inject_context_to_carrier를 외부 스코프에서 참조
    # (decorator 함수 내부에서 사용할 수 있도록)
    _start_dart_span_ref = start_dart_span
    _inject_context_to_carrier_ref = inject_context_to_carrier
    
    def decorator(func: Callable):
        # 함수가 AsyncGenerator인지 확인
        sig = inspect.signature(func)
        return_annotation = sig.return_annotation
        is_async_generator = False
        try:
            origin = get_origin(return_annotation)
            # AsyncGenerator 또는 collections.abc.AsyncGenerator 체크
            if origin is AsyncGenerator or origin is ABCAsyncGenerator:
                is_async_generator = True
            # 문자열로도 확인 (타입 힌트가 문자열로 저장된 경우)
            elif str(return_annotation).startswith('typing.AsyncGenerator') or 'AsyncGenerator' in str(return_annotation):
                is_async_generator = True
            # 타입 힌트가 없는 경우 함수가 generator인지 확인
            elif return_annotation == inspect.Signature.empty:
                # 함수 본문을 확인할 수 없으므로, 함수명이나 다른 힌트로 판단
                # analyze_*_data 패턴은 AsyncGenerator일 가능성이 높음
                if func.__name__.startswith('analyze_') and func.__name__.endswith('_data'):
                    is_async_generator = True
                # coordinate_*_stream 패턴도 AsyncGenerator일 가능성이 높음
                elif func.__name__.endswith('_stream'):
                    is_async_generator = True
        except Exception as e:
            logger.debug(f"Error checking return annotation: {e}")
            # 타입 힌트가 없거나 확인 불가능한 경우
            # analyze_*_data 패턴은 AsyncGenerator일 가능성이 높음
            if func.__name__.startswith('analyze_') and func.__name__.endswith('_data'):
                is_async_generator = True
            # coordinate_*_stream 패턴도 AsyncGenerator일 가능성이 높음
            elif func.__name__.endswith('_stream'):
                is_async_generator = True
        
        # AsyncGenerator와 일반 async 함수를 구분하여 래퍼 생성
        if is_async_generator:
            @functools.wraps(func)
            async def async_generator_wrapper(*args, **kwargs):
                # Span 이름 결정 (GenAI 표준: gen_ai.agent.{name})
                if span_name:
                    name = span_name
                else:
                    # GenAI 표준: gen_ai.agent.{agent_name}
                    if args and hasattr(args[0], '__class__'):
                        class_name = args[0].__class__.__name__
                        # Agent 접미사 제거하고 소문자로 변환
                        agent_name = class_name.lower().replace('agent', '').strip('_')
                        if not agent_name:
                            agent_name = class_name.lower()
                        name = f"gen_ai.agent.{agent_name}"
                    else:
                        name = f"gen_ai.agent.{func.__name__}"
                
                # 로그 (observe 데코레이터 동작 확인용)
                logger.info(f"[observe] Creating span: {name}, is_async_generator={is_async_generator}, func={func.__name__}")
                
                # 기본 속성 (GenAI 표준)
                base_attrs = {
                    "service.name": "agent-dart",
                    "component": "dart-agent",
                    "gen_ai.agent.function": func.__name__,
                }
                
                # 인자 기록용 속성 (나중에 span에 추가)
                arg_attrs = {}
                
                # 인자 기록 (길이 제한 없음)
                if include_args:
                    try:
                        if args and hasattr(args[0], '__class__'):
                            # self 인자 제외
                            bound_args = sig.bind(*args, **kwargs)
                            bound_args.apply_defaults()
                            args_dict = {k: v for k, v in bound_args.arguments.items() if k != 'self'}
                            
                            for key, value in args_dict.items():
                                try:
                                    serialized = _serialize_value(value)
                                    arg_attrs[f"function.arg.{key}"] = serialized
                                except Exception:
                                    pass
                        else:
                            # self가 없는 경우
                            bound_args = sig.bind(*args, **kwargs)
                            bound_args.apply_defaults()
                            for key, value in bound_args.arguments.items():
                                try:
                                    serialized = _serialize_value(value)
                                    arg_attrs[f"function.arg.{key}"] = serialized
                                except Exception:
                                    pass
                    except Exception as e:
                        logger.debug(f"Failed to serialize args: {e}")
                
                # Parent context 가져오기
                current_carrier = {}
                try:
                    _inject_context_to_carrier_ref(current_carrier)
                except Exception:
                    pass
                
                # Span 생성 및 실행 (기본 속성으로 span 생성)
                start_time = time.time()
                with _start_dart_span_ref(name, base_attrs, current_carrier) as span:
                    # 인자 속성도 span에 설정
                    for key, value in arg_attrs.items():
                        try:
                            if isinstance(value, str) and len(value) > 0:
                                span.set_attribute(key, value)
                            elif not isinstance(value, str):
                                span.set_attribute(key, str(value))
                        except Exception as e:
                            logger.debug(f"Failed to set arg attribute {key}: {e}")
                
                    try:
                        # AsyncGenerator인 경우 스트리밍 처리
                        final_result = None
                        result_parts = []
                        generator_exited = False
                        
                        try:
                            async for chunk in func(*args, **kwargs):
                                # 각 청크를 이벤트로 기록
                                try:
                                    # AgentResult 객체인지 확인 (dataclass 또는 dict)
                                    is_agent_result = False
                                    
                                    # AgentResult 객체 체크 (dataclass)
                                    if hasattr(chunk, 'key_findings') and hasattr(chunk, 'agent_name'):
                                        # AgentResult 객체
                                        is_agent_result = True
                                        final_result = chunk
                                        logger.info(f"[observe] AgentResult detected: {chunk.agent_name}, key_findings count: {len(chunk.key_findings) if chunk.key_findings else 0}")
                                        
                                        # 즉시 속성 기록 (Langfuse 방식: 감지 즉시 기록)
                                        try:
                                            # key_findings에서 None 값 필터링
                                            if chunk.key_findings:
                                                filtered_findings = [str(f) for f in chunk.key_findings if f is not None]
                                                final_response = "\n".join(filtered_findings) if filtered_findings else ""
                                            else:
                                                final_response = ""
                                            
                                            if final_response and span and hasattr(span, 'set_attribute'):
                                                span.set_attribute("gen_ai.agent.response", final_response)
                                                span.set_attribute("gen_ai.agent.response.length", len(final_response))
                                                logger.info(f"[observe] Recorded gen_ai.agent.response immediately: {len(final_response)} chars")
                                            
                                            # 추가 정보 즉시 기록
                                            if span and hasattr(span, 'set_attribute'):
                                                if hasattr(chunk, 'agent_name'):
                                                    span.set_attribute("gen_ai.agent.name", chunk.agent_name)
                                                if hasattr(chunk, 'analysis_type'):
                                                    span.set_attribute("gen_ai.agent.analysis_type", chunk.analysis_type)
                                                if hasattr(chunk, 'tools_used') and chunk.tools_used:
                                                    # None 값 필터링
                                                    filtered_tools = [str(t) for t in chunk.tools_used if t is not None]
                                                    if filtered_tools:
                                                        tools_str = ", ".join(filtered_tools)
                                                        span.set_attribute("gen_ai.agent.tools_used", tools_str)
                                                if hasattr(chunk, 'execution_time'):
                                                    span.set_attribute("gen_ai.agent.execution_time", chunk.execution_time)
                                                
                                                # supporting_data의 llm_response도 기록
                                                if hasattr(chunk, 'supporting_data') and chunk.supporting_data:
                                                    llm_response = chunk.supporting_data.get('llm_response', '')
                                                    if llm_response:
                                                        span.set_attribute("gen_ai.agent.llm_response", str(llm_response))
                                        except Exception as e:
                                            logger.warning(f"[observe] Failed to record AgentResult immediately: {e}")
                                    elif isinstance(chunk, dict):
                                        # Dict 형태
                                        chunk_type = chunk.get("type", "chunk")
                                        chunk_content = chunk.get("content") or chunk.get("message") or str(chunk)
                                        
                                        # 이벤트로 기록
                                        if hasattr(span, 'add_event'):
                                            event_attrs = {
                                                "chunk.type": chunk_type,
                                            }
                                            if chunk_content:
                                                event_attrs["chunk.content"] = _serialize_value(chunk_content)
                                            span.add_event(f"stream.{chunk_type}", attributes=event_attrs)
                                        
                                        # AgentResult인 경우 최종 결과로 저장
                                        if 'key_findings' in chunk or chunk.get('type') == 'agent_result':
                                            is_agent_result = True
                                            final_result = chunk
                                            logger.info(f"[observe] AgentResult (dict) detected: {chunk.get('agent_name', 'unknown')}")
                                    
                                    # AgentResult가 아닌 경우에도 청크 기록
                                    if not is_agent_result:
                                        result_parts.append(chunk)
                                            
                                except Exception as e:
                                    logger.warning(f"[observe] Failed to record chunk: {e}")
                                
                                yield chunk
                        except GeneratorExit:
                            # SSE 연결이 끊어지면 GeneratorExit 발생 - 정상적으로 처리
                            generator_exited = True
                            logger.info(f"[observe] GeneratorExit caught in {name} - SSE connection closed by client")
                            if span and hasattr(span, 'set_attribute'):
                                span.set_attribute("stream.client_disconnected", True)
                            # GeneratorExit는 정상적인 종료이므로 raise하지 않고 그냥 종료
                            return
                        
                        # 최종 결과 기록 (길이 제한 없음)
                        logger.info(f"[observe] Loop ended. final_result={final_result is not None}, include_result={include_result}, span={span is not None}, has_set_attribute={hasattr(span, 'set_attribute') if span else False}")
                        if include_result and span and hasattr(span, 'set_attribute'):
                            if final_result:
                                try:
                                    logger.info(f"[observe] Recording final result to span: {name}, final_result type: {type(final_result)}")
                                    
                                    if hasattr(final_result, 'key_findings'):
                                        # AgentResult 객체 (dataclass)
                                        final_response = "\n".join(final_result.key_findings) if final_result.key_findings else ""
                                        logger.info(f"[observe] AgentResult (dataclass): final_response length={len(final_response) if final_response else 0}")
                                        if final_response:
                                            # 길이 제한 없이 전체 내용 기록
                                            span.set_attribute("gen_ai.agent.response", final_response)
                                            span.set_attribute("gen_ai.agent.response.length", len(final_response))
                                            logger.info(f"[observe] Recorded gen_ai.agent.response: {len(final_response)} chars")
                                        
                                        # 추가 정보 기록
                                        if hasattr(final_result, 'agent_name'):
                                            span.set_attribute("gen_ai.agent.name", final_result.agent_name)
                                        if hasattr(final_result, 'analysis_type'):
                                            span.set_attribute("gen_ai.agent.analysis_type", final_result.analysis_type)
                                        if hasattr(final_result, 'tools_used') and final_result.tools_used:
                                            # None 값 필터링
                                            filtered_tools = [str(t) for t in final_result.tools_used if t is not None]
                                            if filtered_tools:
                                                tools_str = ", ".join(filtered_tools)
                                                span.set_attribute("gen_ai.agent.tools_used", tools_str)
                                        if hasattr(final_result, 'execution_time'):
                                            span.set_attribute("gen_ai.agent.execution_time", final_result.execution_time)
                                        
                                        # supporting_data의 llm_response도 기록
                                        if hasattr(final_result, 'supporting_data') and final_result.supporting_data:
                                            llm_response = final_result.supporting_data.get('llm_response', '')
                                            if llm_response:
                                                span.set_attribute("gen_ai.agent.llm_response", str(llm_response))
                                        
                                    elif isinstance(final_result, dict):
                                        # Dict 형태
                                        logger.info(f"[observe] AgentResult (dict): keys={list(final_result.keys())}")
                                        if 'key_findings' in final_result:
                                            key_findings = final_result['key_findings']
                                            if key_findings:
                                                final_response = "\n".join(key_findings) if isinstance(key_findings, list) else str(key_findings)
                                                if final_response:
                                                    # 길이 제한 없이 전체 내용 기록
                                                    span.set_attribute("gen_ai.agent.response", final_response)
                                                    span.set_attribute("gen_ai.agent.response.length", len(final_response))
                                                    logger.info(f"[observe] Recorded gen_ai.agent.response (dict): {len(final_response)} chars")
                                        
                                        # 추가 정보 기록
                                        if 'agent_name' in final_result:
                                            span.set_attribute("gen_ai.agent.name", str(final_result['agent_name']))
                                        if 'analysis_type' in final_result:
                                            span.set_attribute("gen_ai.agent.analysis_type", str(final_result['analysis_type']))
                                        if 'tools_used' in final_result and final_result['tools_used']:
                                            tools_str = ", ".join(final_result['tools_used']) if isinstance(final_result['tools_used'], list) else str(final_result['tools_used'])
                                            span.set_attribute("gen_ai.agent.tools_used", tools_str)
                                        if 'execution_time' in final_result:
                                            span.set_attribute("gen_ai.agent.execution_time", float(final_result['execution_time']))
                                    
                                    # 실행 시간 기록 (함수 실행 시간)
                                    execution_time = time.time() - start_time
                                    span.set_attribute("function.execution_time", execution_time)
                                    
                                    logger.info(f"[observe] Successfully recorded final result to span: {name}")
                                    
                                except Exception as e:
                                    logger.error(f"[observe] Failed to record final result: {e}", exc_info=True)
                            else:
                                logger.debug(f"[observe] No final_result to record for span: {name}")
                    except Exception as e:
                        # 에러 기록
                        if span and hasattr(span, 'set_attribute'):
                            span.set_attribute("error", str(e))
                            span.set_attribute("error.type", type(e).__name__)
                            if hasattr(span, 'record_exception'):
                                span.record_exception(e)
                        raise
        
        else:
            # 일반 async 함수용 래퍼
            @functools.wraps(func)
            async def async_function_wrapper(*args, **kwargs):
                # Span 이름 결정 (GenAI 표준: gen_ai.agent.{name})
                if span_name:
                    name = span_name
                else:
                    # GenAI 표준: gen_ai.agent.{agent_name}
                    if args and hasattr(args[0], '__class__'):
                        class_name = args[0].__class__.__name__
                        # Agent 접미사 제거하고 소문자로 변환
                        agent_name = class_name.lower().replace('agent', '').strip('_')
                        if not agent_name:
                            agent_name = class_name.lower()
                        name = f"gen_ai.agent.{agent_name}"
                    else:
                        name = f"gen_ai.agent.{func.__name__}"
                
                # 로그
                logger.info(f"[observe] Creating span: {name}, func={func.__name__}")
                
                # 기본 속성 (GenAI 표준)
                base_attrs = {
                    "service.name": "agent-dart",
                    "component": "dart-agent",
                    "gen_ai.agent.function": func.__name__,
                }
                
                # Parent context 가져오기
                current_carrier = {}
                try:
                    _inject_context_to_carrier_ref(current_carrier)
                except Exception:
                    pass
                
                # Span 생성 및 실행
                start_time = time.time()
                with _start_dart_span_ref(name, base_attrs, current_carrier) as span:
                    try:
                        result = await func(*args, **kwargs)
                        
                        # 반환값 기록 (길이 제한 없음)
                        if include_result and span and hasattr(span, 'set_attribute'):
                            try:
                                serialized_result = _serialize_value(result)
                                span.set_attribute("function.result", serialized_result)
                                span.set_attribute("function.result.length", len(serialized_result))
                            except Exception as e:
                                logger.debug(f"Failed to record result: {e}")
                        
                        # 실행 시간 기록
                        execution_time = time.time() - start_time
                        if span and hasattr(span, 'set_attribute'):
                            span.set_attribute("function.execution_time", execution_time)
                        
                        return result
                        
                    except Exception as e:
                        # 에러 기록
                        if span and hasattr(span, 'set_attribute'):
                            span.set_attribute("error", str(e))
                            span.set_attribute("error.type", type(e).__name__)
                            if hasattr(span, 'record_exception'):
                                span.record_exception(e)
                        raise
        
        # AsyncGenerator인 경우와 일반 함수인 경우에 따라 다른 래퍼 반환
        if is_async_generator:
            return async_generator_wrapper
        else:
            return async_function_wrapper
    
    return decorator


