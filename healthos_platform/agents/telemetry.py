"""
Eminence HealthOS — Agent Telemetry
OpenTelemetry integration for distributed tracing of agent executions.
Provides trace context, span management, and metric collection.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from typing import Any, Generator

import structlog

logger = structlog.get_logger()

# ── OpenTelemetry Setup ──────────────────────────────────────────────────────

_tracer = None
_meter = None


def init_telemetry(
    service_name: str = "healthos-agents",
    otlp_endpoint: str = "http://localhost:4317",
) -> None:
    """Initialize OpenTelemetry with OTLP/gRPC export."""
    global _tracer, _meter

    try:
        from opentelemetry import trace, metrics
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader

        resource = Resource.create({"service.name": service_name})

        # Tracing
        tracer_provider = TracerProvider(resource=resource)
        span_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        tracer_provider.add_span_processor(BatchSpanProcessor(span_exporter))
        trace.set_tracer_provider(tracer_provider)
        _tracer = trace.get_tracer(service_name)

        # Metrics
        metric_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        metric_reader = PeriodicExportingMetricReader(metric_exporter, export_interval_millis=30000)
        meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
        metrics.set_meter_provider(meter_provider)
        _meter = metrics.get_meter(service_name)

        logger.info("telemetry.initialized", service=service_name, endpoint=otlp_endpoint)

    except ImportError:
        logger.warning(
            "telemetry.otel_not_installed",
            message="OpenTelemetry packages not installed. Install with: "
            "pip install opentelemetry-api opentelemetry-sdk "
            "opentelemetry-exporter-otlp-proto-grpc",
        )
    except Exception as e:
        logger.warning("telemetry.init_failed", error=str(e))


def auto_instrument_fastapi(app: Any) -> None:
    """Auto-instrument a FastAPI application."""
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)
        logger.info("telemetry.fastapi_instrumented")
    except ImportError:
        logger.debug("telemetry.fastapi_instrumentation_unavailable")


def auto_instrument_httpx() -> None:
    """Auto-instrument httpx HTTP client."""
    try:
        from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

        HTTPXClientInstrumentor().instrument()
        logger.info("telemetry.httpx_instrumented")
    except ImportError:
        logger.debug("telemetry.httpx_instrumentation_unavailable")


# ── Span Management ──────────────────────────────────────────────────────────


@contextmanager
def agent_span(
    agent_name: str,
    trace_id: str = "",
    tier: str = "",
    attributes: dict[str, Any] | None = None,
) -> Generator[Any, None, None]:
    """
    Context manager that creates a traced span for agent execution.
    Falls back to a no-op context if OpenTelemetry is not available.
    """
    extra_attrs = {
        "agent.name": agent_name,
        "agent.tier": tier,
        "agent.trace_id": trace_id,
        **(attributes or {}),
    }

    if _tracer is not None:
        with _tracer.start_as_current_span(
            f"agent.{agent_name}",
            attributes={k: str(v) for k, v in extra_attrs.items()},
        ) as span:
            try:
                yield span
            except Exception as e:
                span.set_attribute("error", True)
                span.set_attribute("error.message", str(e))
                raise
    else:
        # No-op context when OTel is not available
        yield _NoOpSpan()


class _NoOpSpan:
    """No-op span for when OpenTelemetry is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def add_event(self, name: str, attributes: dict | None = None) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass


# ── Metrics ──────────────────────────────────────────────────────────────────


class AgentMetrics:
    """Collects agent execution metrics."""

    def __init__(self) -> None:
        self._counters: dict[str, int] = {}
        self._histograms: dict[str, list[float]] = {}

        if _meter is not None:
            self._otel_counter = _meter.create_counter(
                "agent.executions",
                description="Total agent executions",
            )
            self._otel_histogram = _meter.create_histogram(
                "agent.duration_ms",
                description="Agent execution duration in milliseconds",
                unit="ms",
            )
        else:
            self._otel_counter = None
            self._otel_histogram = None

    def record_execution(
        self, agent_name: str, duration_ms: float, status: str
    ) -> None:
        """Record an agent execution."""
        key = f"{agent_name}:{status}"
        self._counters[key] = self._counters.get(key, 0) + 1
        self._histograms.setdefault(agent_name, []).append(duration_ms)

        if self._otel_counter:
            self._otel_counter.add(
                1, {"agent.name": agent_name, "agent.status": status}
            )
        if self._otel_histogram:
            self._otel_histogram.record(
                duration_ms, {"agent.name": agent_name}
            )

    def get_stats(self, agent_name: str | None = None) -> dict[str, Any]:
        """Get execution statistics."""
        if agent_name:
            durations = self._histograms.get(agent_name, [])
            return {
                "agent": agent_name,
                "total_executions": sum(
                    v for k, v in self._counters.items() if k.startswith(agent_name)
                ),
                "avg_duration_ms": sum(durations) / len(durations) if durations else 0,
                "min_duration_ms": min(durations) if durations else 0,
                "max_duration_ms": max(durations) if durations else 0,
            }

        return {"counters": dict(self._counters)}


# Module-level singleton
agent_metrics = AgentMetrics()
