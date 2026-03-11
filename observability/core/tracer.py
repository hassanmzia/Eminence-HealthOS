"""
Unified Observability Tracer for HealthOS Multi-Agent System.

Consolidates tracing across LangSmith, Langfuse, and OpenTelemetry
with healthcare-specific decision logging, rationale capture,
and agent-to-agent conversation tracking.
"""

import os
import json
import uuid
import time
import logging
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from contextlib import asynccontextmanager
from enum import Enum

logger = logging.getLogger("healthos.observability.tracer")


class TraceStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"  # HITL interrupt
    SKIPPED = "skipped"


class DecisionRecord:
    """Immutable record of an agent decision with full rationale."""

    __slots__ = (
        "timestamp", "trace_id", "span_id", "agent_name", "agent_tier",
        "decision", "rationale", "confidence", "alternatives",
        "input_summary", "output_summary", "duration_ms",
        "patient_id", "tenant_id", "feature_contributions",
        "evidence_references", "requires_hitl", "safety_flags",
    )

    def __init__(
        self,
        trace_id: str,
        agent_name: str,
        decision: str,
        rationale: str,
        *,
        span_id: str = None,
        agent_tier: str = None,
        confidence: float = None,
        alternatives: List[Dict] = None,
        input_summary: Dict = None,
        output_summary: Dict = None,
        duration_ms: int = 0,
        patient_id: str = None,
        tenant_id: str = None,
        feature_contributions: List[Dict] = None,
        evidence_references: List[Dict] = None,
        requires_hitl: bool = False,
        safety_flags: List[str] = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.trace_id = trace_id
        self.span_id = span_id or str(uuid.uuid4())
        self.agent_name = agent_name
        self.agent_tier = agent_tier
        self.decision = decision
        self.rationale = rationale
        self.confidence = confidence
        self.alternatives = alternatives or []
        self.input_summary = _safe_serialize(input_summary or {})
        self.output_summary = _safe_serialize(output_summary or {})
        self.duration_ms = duration_ms
        self.patient_id = patient_id
        self.tenant_id = tenant_id
        self.feature_contributions = feature_contributions or []
        self.evidence_references = evidence_references or []
        self.requires_hitl = requires_hitl
        self.safety_flags = safety_flags or []

    def to_dict(self) -> Dict[str, Any]:
        return {attr: getattr(self, attr) for attr in self.__slots__}


class ConversationRecord:
    """Record of agent-to-agent communication."""

    __slots__ = (
        "timestamp", "trace_id", "sender_agent", "receiver_agent",
        "message_type", "capability", "payload", "response",
        "success", "duration_ms", "error",
    )

    def __init__(
        self,
        trace_id: str,
        sender_agent: str,
        receiver_agent: str,
        message_type: str,
        *,
        capability: str = None,
        payload: Dict = None,
        response: Dict = None,
        success: bool = True,
        duration_ms: int = 0,
        error: str = None,
    ):
        self.timestamp = datetime.now(timezone.utc).isoformat()
        self.trace_id = trace_id
        self.sender_agent = sender_agent
        self.receiver_agent = receiver_agent
        self.message_type = message_type
        self.capability = capability
        self.payload = _safe_serialize(payload or {})
        self.response = _safe_serialize(response or {})
        self.success = success
        self.duration_ms = duration_ms
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {attr: getattr(self, attr) for attr in self.__slots__}


class ObservabilityManager:
    """
    Unified observability manager supporting LangSmith, Langfuse, and OpenTelemetry.

    Provides:
    - Distributed tracing across all agent tiers
    - Decision logging with rationale and feature attribution
    - Agent-to-agent conversation tracking
    - LLM token/cost tracking
    - Retry and fallback logging
    """

    def __init__(self):
        self.langsmith_enabled = False
        self.langfuse_enabled = False
        self.otel_enabled = False
        self.langsmith_client = None
        self.langfuse = None
        self.otel_tracer = None

        self._decisions: List[DecisionRecord] = []
        self._conversations: List[ConversationRecord] = []
        self._retries: List[Dict] = []
        self._fallbacks: List[Dict] = []

        self._init_langsmith()
        self._init_langfuse()
        self._init_otel()

    def _init_langsmith(self):
        api_key = os.environ.get("LANGCHAIN_API_KEY")
        if not api_key:
            logger.info("LangSmith disabled (no LANGCHAIN_API_KEY)")
            return
        try:
            from langsmith import Client as LangSmithClient
            os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
            os.environ.setdefault("LANGCHAIN_PROJECT", "healthos-agents")
            self.langsmith_client = LangSmithClient()
            self.langsmith_enabled = True
            logger.info("LangSmith tracing enabled")
        except ImportError:
            logger.warning("langsmith package not installed")

    def _init_langfuse(self):
        public_key = os.environ.get("LANGFUSE_PUBLIC_KEY")
        if not public_key:
            logger.info("Langfuse disabled (no LANGFUSE_PUBLIC_KEY)")
            return
        try:
            from langfuse import Langfuse
            self.langfuse = Langfuse(
                public_key=public_key,
                secret_key=os.environ.get("LANGFUSE_SECRET_KEY"),
                host=os.environ.get("LANGFUSE_HOST", "https://cloud.langfuse.com"),
            )
            self.langfuse_enabled = True
            logger.info("Langfuse tracing enabled")
        except ImportError:
            logger.warning("langfuse package not installed")

    def _init_otel(self):
        endpoint = os.environ.get("OTEL_EXPORTER_OTLP_ENDPOINT")
        if not endpoint:
            logger.info("OpenTelemetry disabled (no OTEL_EXPORTER_OTLP_ENDPOINT)")
            return
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource

            resource = Resource.create({
                "service.name": os.environ.get("OTEL_SERVICE_NAME", "healthos-agents"),
                "service.version": os.environ.get("HEALTHOS_VERSION", "1.0.0"),
                "deployment.environment": os.environ.get("ENVIRONMENT", "development"),
            })
            provider = TracerProvider(resource=resource)
            exporter = OTLPSpanExporter(endpoint=endpoint)
            provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(provider)
            self.otel_tracer = trace.get_tracer("healthos.agents")
            self.otel_enabled = True
            logger.info("OpenTelemetry tracing enabled → %s", endpoint)
        except ImportError:
            logger.warning("opentelemetry packages not installed")

    # ── Trace / Span creation ────────────────────────────────────────

    def create_trace(
        self,
        name: str,
        session_id: str,
        user_id: str = None,
        patient_id: str = None,
        tenant_id: str = None,
        metadata: Dict = None,
    ) -> "TraceContext":
        return TraceContext(
            manager=self,
            name=name,
            session_id=session_id,
            user_id=user_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            metadata=metadata or {},
        )

    # ── Decision logging ─────────────────────────────────────────────

    def log_decision(self, record: DecisionRecord):
        """Log an agent decision with full rationale and feature attribution."""
        self._decisions.append(record)

        # Forward to Langfuse as a score
        if self.langfuse:
            try:
                self.langfuse.score(
                    trace_id=record.trace_id,
                    name=f"{record.agent_name}_decision",
                    value=record.confidence or 0.8,
                    comment=record.rationale,
                )
            except Exception as e:
                logger.warning("Langfuse scoring failed: %s", e)

        # Forward to OTel as span event
        if self.otel_tracer:
            try:
                from opentelemetry import trace as otel_trace
                span = otel_trace.get_current_span()
                if span and span.is_recording():
                    span.add_event(
                        f"decision.{record.agent_name}",
                        attributes={
                            "agent.decision": record.decision,
                            "agent.confidence": record.confidence or 0.0,
                            "agent.rationale": record.rationale[:500],
                            "agent.requires_hitl": record.requires_hitl,
                        },
                    )
            except Exception:
                pass

        logger.info(
            "Decision: agent=%s decision=%s confidence=%.2f hitl=%s",
            record.agent_name,
            record.decision,
            record.confidence or 0.0,
            record.requires_hitl,
        )

    # ── Conversation logging ─────────────────────────────────────────

    def log_conversation(self, record: ConversationRecord):
        """Log agent-to-agent communication."""
        self._conversations.append(record)

        if self.langfuse:
            try:
                self.langfuse.generation(
                    trace_id=record.trace_id,
                    name=f"a2a_{record.sender_agent}_to_{record.receiver_agent}",
                    input=record.payload,
                    output=record.response,
                    metadata={
                        "message_type": record.message_type,
                        "capability": record.capability,
                        "success": record.success,
                    },
                )
            except Exception as e:
                logger.warning("Langfuse generation logging failed: %s", e)

    # ── Retry / Fallback logging ─────────────────────────────────────

    def log_retry(
        self,
        trace_id: str,
        agent_name: str,
        attempt: int,
        max_attempts: int,
        error: str,
        backoff_seconds: float,
    ):
        """Log an agent retry attempt."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "agent_name": agent_name,
            "attempt": attempt,
            "max_attempts": max_attempts,
            "error": error[:500],
            "backoff_seconds": backoff_seconds,
        }
        self._retries.append(record)
        logger.warning(
            "Retry: agent=%s attempt=%d/%d backoff=%.1fs error=%s",
            agent_name, attempt, max_attempts, backoff_seconds, error[:100],
        )

    def log_fallback(
        self,
        trace_id: str,
        agent_name: str,
        primary_model: str,
        fallback_model: str,
        reason: str,
    ):
        """Log when an agent falls back to an alternative model or strategy."""
        record = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "trace_id": trace_id,
            "agent_name": agent_name,
            "primary_model": primary_model,
            "fallback_model": fallback_model,
            "reason": reason[:500],
        }
        self._fallbacks.append(record)
        logger.warning(
            "Fallback: agent=%s %s → %s reason=%s",
            agent_name, primary_model, fallback_model, reason[:100],
        )

    # ── LLM token/cost tracking ──────────────────────────────────────

    def log_llm_usage(
        self,
        trace_id: str,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = None,
        latency_ms: int = 0,
    ):
        """Log LLM token usage and cost for an agent call."""
        if self.langfuse:
            try:
                self.langfuse.generation(
                    trace_id=trace_id,
                    name=f"llm_{agent_name}",
                    model=model,
                    usage={
                        "input": input_tokens,
                        "output": output_tokens,
                        "total": input_tokens + output_tokens,
                    },
                    metadata={
                        "cost_usd": cost_usd,
                        "latency_ms": latency_ms,
                    },
                )
            except Exception as e:
                logger.warning("Langfuse LLM usage logging failed: %s", e)

        # Prometheus metrics (if available)
        try:
            from observability.metrics.collector import MetricsCollector
            MetricsCollector.instance().record_llm_usage(
                agent_name=agent_name,
                model=model,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cost_usd=cost_usd or 0.0,
                latency_ms=latency_ms,
            )
        except Exception:
            pass

    # ── Query methods ────────────────────────────────────────────────

    def get_decisions(
        self,
        trace_id: str = None,
        agent_name: str = None,
        limit: int = 100,
    ) -> List[Dict]:
        """Retrieve logged decisions, optionally filtered."""
        results = self._decisions
        if trace_id:
            results = [d for d in results if d.trace_id == trace_id]
        if agent_name:
            results = [d for d in results if d.agent_name == agent_name]
        return [d.to_dict() for d in results[-limit:]]

    def get_conversations(self, trace_id: str = None, limit: int = 100) -> List[Dict]:
        results = self._conversations
        if trace_id:
            results = [r for r in results if r.trace_id == trace_id]
        return [r.to_dict() for r in results[-limit:]]

    def get_retries(self, trace_id: str = None) -> List[Dict]:
        if trace_id:
            return [r for r in self._retries if r["trace_id"] == trace_id]
        return list(self._retries)

    def get_fallbacks(self, trace_id: str = None) -> List[Dict]:
        if trace_id:
            return [f for f in self._fallbacks if f["trace_id"] == trace_id]
        return list(self._fallbacks)

    # ── Connection status ────────────────────────────────────────────

    def status(self) -> Dict[str, Any]:
        return {
            "langsmith": {"enabled": self.langsmith_enabled},
            "langfuse": {"enabled": self.langfuse_enabled},
            "opentelemetry": {"enabled": self.otel_enabled},
            "stats": {
                "decisions_logged": len(self._decisions),
                "conversations_logged": len(self._conversations),
                "retries_logged": len(self._retries),
                "fallbacks_logged": len(self._fallbacks),
            },
        }

    def flush(self):
        if self.langfuse:
            try:
                self.langfuse.flush()
            except Exception as e:
                logger.warning("Langfuse flush failed: %s", e)


class TraceContext:
    """Context manager for a single trace/session spanning multiple agent calls."""

    def __init__(
        self,
        manager: ObservabilityManager,
        name: str,
        session_id: str,
        user_id: str = None,
        patient_id: str = None,
        tenant_id: str = None,
        metadata: Dict = None,
    ):
        self.manager = manager
        self.name = name
        self.session_id = session_id
        self.user_id = user_id
        self.patient_id = patient_id
        self.tenant_id = tenant_id
        self.metadata = metadata or {}
        self.trace_id = str(uuid.uuid4())
        self.decisions: List[DecisionRecord] = []
        self.conversations: List[ConversationRecord] = []
        self.langfuse_trace = None
        self.otel_span = None
        self.start_time = None

    async def __aenter__(self):
        self.start_time = time.monotonic()

        if self.manager.langfuse:
            try:
                self.langfuse_trace = self.manager.langfuse.trace(
                    id=self.trace_id,
                    name=self.name,
                    session_id=self.session_id,
                    user_id=self.user_id,
                    metadata={
                        **self.metadata,
                        "patient_id": self.patient_id,
                        "tenant_id": self.tenant_id,
                    },
                )
            except Exception as e:
                logger.warning("Failed to create Langfuse trace: %s", e)

        if self.manager.otel_tracer:
            try:
                self.otel_span = self.manager.otel_tracer.start_span(
                    self.name,
                    attributes={
                        "session.id": self.session_id,
                        "patient.id": self.patient_id or "",
                        "tenant.id": self.tenant_id or "",
                    },
                )
            except Exception as e:
                logger.warning("Failed to create OTel span: %s", e)

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.monotonic() - self.start_time) * 1000)

        if self.otel_span:
            try:
                if exc_type:
                    from opentelemetry.trace import StatusCode
                    self.otel_span.set_status(StatusCode.ERROR, str(exc_val))
                self.otel_span.set_attribute("trace.duration_ms", duration_ms)
                self.otel_span.set_attribute("trace.decisions_count", len(self.decisions))
                self.otel_span.end()
            except Exception:
                pass

        self.manager.flush()

    def span(self, name: str, input_data: Dict = None) -> "SpanContext":
        return SpanContext(trace=self, name=name, input_data=input_data)

    def log_decision(
        self,
        agent_name: str,
        decision: str,
        rationale: str,
        *,
        agent_tier: str = None,
        confidence: float = None,
        alternatives: List[Dict] = None,
        input_data: Dict = None,
        output_data: Dict = None,
        feature_contributions: List[Dict] = None,
        evidence_references: List[Dict] = None,
        requires_hitl: bool = False,
        safety_flags: List[str] = None,
        duration_ms: int = 0,
    ) -> DecisionRecord:
        record = DecisionRecord(
            trace_id=self.trace_id,
            agent_name=agent_name,
            decision=decision,
            rationale=rationale,
            agent_tier=agent_tier,
            confidence=confidence,
            alternatives=alternatives,
            input_summary=input_data,
            output_summary=output_data,
            duration_ms=duration_ms,
            patient_id=self.patient_id,
            tenant_id=self.tenant_id,
            feature_contributions=feature_contributions,
            evidence_references=evidence_references,
            requires_hitl=requires_hitl,
            safety_flags=safety_flags,
        )
        self.decisions.append(record)
        self.manager.log_decision(record)
        return record

    def log_conversation(
        self,
        sender: str,
        receiver: str,
        message_type: str,
        *,
        capability: str = None,
        payload: Dict = None,
        response: Dict = None,
        success: bool = True,
        duration_ms: int = 0,
        error: str = None,
    ) -> ConversationRecord:
        record = ConversationRecord(
            trace_id=self.trace_id,
            sender_agent=sender,
            receiver_agent=receiver,
            message_type=message_type,
            capability=capability,
            payload=payload,
            response=response,
            success=success,
            duration_ms=duration_ms,
            error=error,
        )
        self.conversations.append(record)
        self.manager.log_conversation(record)
        return record


class SpanContext:
    """Context manager for a span within a trace."""

    def __init__(self, trace: TraceContext, name: str, input_data: Dict = None):
        self.trace = trace
        self.name = name
        self.input_data = input_data or {}
        self.span_id = str(uuid.uuid4())
        self.start_time = None
        self.langfuse_span = None
        self.otel_span = None

    async def __aenter__(self):
        self.start_time = time.monotonic()

        if self.trace.langfuse_trace and self.trace.manager.langfuse:
            try:
                self.langfuse_span = self.trace.langfuse_trace.span(
                    name=self.name,
                    input=self.input_data,
                )
            except Exception as e:
                logger.warning("Failed to create Langfuse span: %s", e)

        if self.trace.manager.otel_tracer:
            try:
                self.otel_span = self.trace.manager.otel_tracer.start_span(
                    self.name,
                    attributes={"span.input_keys": str(list(self.input_data.keys()))},
                )
            except Exception:
                pass

        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration_ms = int((time.monotonic() - self.start_time) * 1000)

        if self.langfuse_span:
            try:
                self.langfuse_span.end()
            except Exception:
                pass

        if self.otel_span:
            try:
                self.otel_span.set_attribute("span.duration_ms", duration_ms)
                if exc_type:
                    from opentelemetry.trace import StatusCode
                    self.otel_span.set_status(StatusCode.ERROR, str(exc_val))
                self.otel_span.end()
            except Exception:
                pass

    def set_output(self, output: Dict):
        if self.langfuse_span:
            try:
                self.langfuse_span.update(output=_safe_serialize(output))
            except Exception:
                pass


# ── Decorators ────────────────────────────────────────────────────────


def trace_agent_action(agent_name: str, action: str, tier: str = None):
    """Decorator to trace agent actions with automatic retry/error logging."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, state, *args, **kwargs):
            start = time.monotonic()
            obs = getattr(self, "observability", None)
            trace_id = state.get("session_id", "unknown") if isinstance(state, dict) else "unknown"

            try:
                result = await func(self, state, *args, **kwargs)
                duration_ms = int((time.monotonic() - start) * 1000)

                if obs:
                    obs.log_conversation(ConversationRecord(
                        trace_id=trace_id,
                        sender_agent="orchestrator",
                        receiver_agent=agent_name,
                        message_type="action",
                        capability=action,
                        payload=_safe_serialize(state) if isinstance(state, dict) else {},
                        response=_safe_serialize(result) if isinstance(result, dict) else {},
                        success=True,
                        duration_ms=duration_ms,
                    ))

                return result

            except Exception as e:
                duration_ms = int((time.monotonic() - start) * 1000)
                if obs:
                    obs.log_conversation(ConversationRecord(
                        trace_id=trace_id,
                        sender_agent="orchestrator",
                        receiver_agent=agent_name,
                        message_type="error",
                        capability=action,
                        payload=_safe_serialize(state) if isinstance(state, dict) else {},
                        success=False,
                        duration_ms=duration_ms,
                        error=str(e)[:500],
                    ))
                raise

        return wrapper
    return decorator


def trace_decision(agent_name: str, tier: str = None):
    """Decorator to trace agent decisions with automatic rationale extraction."""
    def decorator(func):
        @wraps(func)
        async def wrapper(self, *args, **kwargs):
            start = time.monotonic()
            result = await func(self, *args, **kwargs)
            duration_ms = int((time.monotonic() - start) * 1000)

            if isinstance(result, dict):
                obs = getattr(self, "observability", None)
                if obs:
                    record = DecisionRecord(
                        trace_id=result.get("session_id", "unknown"),
                        agent_name=agent_name,
                        decision=result.get("decision", "unknown"),
                        rationale=result.get("rationale", ""),
                        agent_tier=tier,
                        confidence=result.get("confidence"),
                        input_summary=_safe_serialize(args[0]) if args else {},
                        output_summary=_safe_serialize(result),
                        duration_ms=duration_ms,
                        feature_contributions=result.get("feature_contributions", []),
                        requires_hitl=result.get("requires_hitl", False),
                        safety_flags=result.get("safety_flags", []),
                    )
                    obs.log_decision(record)

            return result
        return wrapper
    return decorator


# ── Helpers ───────────────────────────────────────────────────────────


def _safe_serialize(obj, max_depth: int = 3) -> Dict:
    """Safely serialize an object for logging, preventing unbounded output."""
    if max_depth <= 0:
        return {"_truncated": True}
    try:
        if isinstance(obj, dict):
            return {
                k: _truncate_value(v, max_depth=max_depth - 1)
                for k, v in list(obj.items())[:20]
            }
        elif isinstance(obj, (list, tuple)):
            return [_truncate_value(v, max_depth=max_depth - 1) for v in obj[:10]]
        else:
            return {"value": str(obj)[:500]}
    except Exception:
        return {"_error": "serialization_failed"}


def _truncate_value(value, max_length: int = 200, max_depth: int = 2) -> Any:
    if isinstance(value, str) and len(value) > max_length:
        return value[:max_length] + "..."
    elif isinstance(value, (list, tuple)) and len(value) > 10:
        return list(value[:10]) + ["..."]
    elif isinstance(value, dict):
        if max_depth <= 0:
            return {"_truncated": True}
        return {
            k: _truncate_value(v, max_length, max_depth - 1)
            for k, v in list(value.items())[:10]
        }
    return value
