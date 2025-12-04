"""
OpenTelemetry Setup

참조: docs/plans/DATA_CLOUD_AGENT.md 섹션 8

OTEL tracer/meter 초기화 및 OTLP exporter 설정.
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Global instances
_tracer_provider = None
_meter_provider = None
_initialized = False


def init_telemetry(
    service_name: str = "agent-text2sql",
    otlp_endpoint: Optional[str] = None
) -> bool:
    """
    OpenTelemetry 초기화.
    
    Args:
        service_name: 서비스 이름
        otlp_endpoint: OTLP exporter 엔드포인트 (None이면 환경변수 사용)
        
    Returns:
        초기화 성공 여부
    """
    global _tracer_provider, _meter_provider, _initialized
    
    if _initialized:
        logger.debug("Telemetry already initialized")
        return True
    
    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        
        # OTLP endpoint
        endpoint = otlp_endpoint or os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4317")
        
        # Resource (서비스 식별)
        resource = Resource.create({
            "service.name": service_name,
            "service.namespace": "agent-portal",
            "deployment.environment": os.getenv("ENVIRONMENT", "development")
        })
        
        # Tracer Provider
        _tracer_provider = TracerProvider(resource=resource)
        
        # Span Exporter
        span_exporter = OTLPSpanExporter(endpoint=endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        
        trace.set_tracer_provider(_tracer_provider)
        
        # Meter Provider
        metric_exporter = OTLPMetricExporter(endpoint=endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
        _meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        
        metrics.set_meter_provider(_meter_provider)
        
        _initialized = True
        logger.info(f"OpenTelemetry initialized: service={service_name}, endpoint={endpoint}")
        
        return True
        
    except ImportError as e:
        logger.warning(f"OpenTelemetry packages not installed: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize OpenTelemetry: {e}")
        return False


def get_tracer(name: str = "text2sql"):
    """
    Tracer 인스턴스 획득.
    
    Args:
        name: Tracer 이름
        
    Returns:
        Tracer 인스턴스
    """
    if not _initialized:
        init_telemetry()
    
    try:
        from opentelemetry import trace
        return trace.get_tracer(name)
    except ImportError:
        logger.warning("OpenTelemetry not available")
        return _NoOpTracer()


def get_meter(name: str = "text2sql"):
    """
    Meter 인스턴스 획득.
    
    Args:
        name: Meter 이름
        
    Returns:
        Meter 인스턴스
    """
    if not _initialized:
        init_telemetry()
    
    try:
        from opentelemetry import metrics
        return metrics.get_meter(name)
    except ImportError:
        logger.warning("OpenTelemetry not available")
        return _NoOpMeter()


class _NoOpTracer:
    """No-op tracer fallback."""
    def start_span(self, name, **kwargs):
        return _NoOpSpan()
    
    def start_as_current_span(self, name, **kwargs):
        from contextlib import contextmanager
        
        @contextmanager
        def noop_context():
            yield _NoOpSpan()
        
        return noop_context()


class _NoOpSpan:
    """No-op span fallback."""
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


class _NoOpMeter:
    """No-op meter fallback."""
    def create_counter(self, name, **kwargs):
        return _NoOpCounter()
    
    def create_histogram(self, name, **kwargs):
        return _NoOpHistogram()
    
    def create_up_down_counter(self, name, **kwargs):
        return _NoOpCounter()


class _NoOpCounter:
    """No-op counter fallback."""
    def add(self, value, attributes=None):
        pass


class _NoOpHistogram:
    """No-op histogram fallback."""
    def record(self, value, attributes=None):
        pass

