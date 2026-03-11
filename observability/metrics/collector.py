"""
Unified Metrics Collector for HealthOS Agent Observability.

Provides Prometheus-compatible metrics for agent execution,
LLM usage, clinical safety, and system health.
Falls back gracefully when prometheus_client is not installed.
"""

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("healthos.observability.metrics")

# Try importing prometheus_client; provide no-op fallback if unavailable
try:
    from prometheus_client import Counter, Histogram, Gauge, Info, CollectorRegistry
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logger.info("prometheus_client not installed — metrics will be logged only")


class _NoOpMetric:
    """No-op metric when Prometheus is unavailable."""
    def labels(self, *args, **kwargs):
        return self
    def inc(self, *args, **kwargs):
        pass
    def dec(self, *args, **kwargs):
        pass
    def set(self, *args, **kwargs):
        pass
    def observe(self, *args, **kwargs):
        pass
    def info(self, *args, **kwargs):
        pass


class MetricsCollector:
    """
    Singleton metrics collector for HealthOS agents.

    Metrics:
    - Agent execution: run count, latency, error rate
    - LLM usage: tokens, cost, calls per model
    - Clinical safety: alerts, HITL interrupts, guardrail violations
    - System health: queue depth, active agents, memory usage
    """

    _instance: Optional["MetricsCollector"] = None

    @classmethod
    def instance(cls) -> "MetricsCollector":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self):
        if PROMETHEUS_AVAILABLE:
            self._init_prometheus()
        else:
            self._init_noop()

        # In-memory counters for non-Prometheus environments
        self._counters: Dict[str, float] = {}

    def _init_prometheus(self):
        # Agent execution metrics
        self.agent_runs = Counter(
            "healthos_agent_runs_total",
            "Total agent executions",
            ["agent_name", "agent_tier", "status"],
        )
        self.agent_latency = Histogram(
            "healthos_agent_latency_seconds",
            "Agent execution latency",
            ["agent_name", "agent_tier"],
            buckets=[0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0],
        )
        self.agent_errors = Counter(
            "healthos_agent_errors_total",
            "Total agent errors",
            ["agent_name", "agent_tier", "error_type"],
        )

        # LLM usage metrics
        self.llm_tokens = Counter(
            "healthos_llm_tokens_total",
            "Total LLM tokens consumed",
            ["agent_name", "model", "direction"],  # direction: input|output
        )
        self.llm_cost = Counter(
            "healthos_llm_cost_usd_total",
            "Total LLM cost in USD",
            ["agent_name", "model"],
        )
        self.llm_calls = Counter(
            "healthos_llm_calls_total",
            "Total LLM API calls",
            ["agent_name", "model", "status"],
        )
        self.llm_latency = Histogram(
            "healthos_llm_latency_seconds",
            "LLM call latency",
            ["agent_name", "model"],
            buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0],
        )

        # Clinical safety metrics
        self.alerts_generated = Counter(
            "healthos_alerts_generated_total",
            "Total clinical alerts generated",
            ["agent_name", "severity"],  # severity: LOW|MEDIUM|HIGH|CRITICAL|EMERGENCY
        )
        self.hitl_interrupts = Counter(
            "healthos_hitl_interrupts_total",
            "Total HITL interrupt requests",
            ["agent_name", "risk_level"],
        )
        self.hitl_decisions = Counter(
            "healthos_hitl_decisions_total",
            "Total HITL decisions by physicians",
            ["decision"],  # approve|reject|modify|escalate
        )
        self.guardrail_violations = Counter(
            "healthos_guardrail_violations_total",
            "Total guardrail violations detected",
            ["violation_type"],  # prompt_injection|restricted_topic|rate_limit|etc.
        )
        self.phi_detections = Counter(
            "healthos_phi_detections_total",
            "Total PHI detections",
            ["event_type"],  # PHI_DETECTED|PHI_REDACTED
        )

        # A2A communication metrics
        self.a2a_messages = Counter(
            "healthos_a2a_messages_total",
            "Total agent-to-agent messages",
            ["sender", "receiver", "status"],
        )

        # System health
        self.active_agents = Gauge(
            "healthos_active_agents",
            "Currently active agents",
            ["agent_tier"],
        )
        self.queue_depth = Gauge(
            "healthos_queue_depth",
            "Current task queue depth",
            ["queue_name"],
        )

        # Retry and fallback metrics
        self.retries = Counter(
            "healthos_retries_total",
            "Total retry attempts",
            ["agent_name", "attempt"],
        )
        self.fallbacks = Counter(
            "healthos_fallbacks_total",
            "Total fallback activations",
            ["agent_name", "primary_model", "fallback_model"],
        )

    def _init_noop(self):
        noop = _NoOpMetric()
        self.agent_runs = noop
        self.agent_latency = noop
        self.agent_errors = noop
        self.llm_tokens = noop
        self.llm_cost = noop
        self.llm_calls = noop
        self.llm_latency = noop
        self.alerts_generated = noop
        self.hitl_interrupts = noop
        self.hitl_decisions = noop
        self.guardrail_violations = noop
        self.phi_detections = noop
        self.a2a_messages = noop
        self.active_agents = noop
        self.queue_depth = noop
        self.retries = noop
        self.fallbacks = noop

    # ── Convenience methods ──────────────────────────────────────────

    def record_agent_run(
        self, agent_name: str, tier: str, status: str, duration_seconds: float,
    ):
        """Record a complete agent execution."""
        self.agent_runs.labels(agent_name=agent_name, agent_tier=tier, status=status).inc()
        self.agent_latency.labels(agent_name=agent_name, agent_tier=tier).observe(duration_seconds)
        if status == "error":
            self.agent_errors.labels(
                agent_name=agent_name, agent_tier=tier, error_type="runtime",
            ).inc()

    def record_llm_usage(
        self,
        agent_name: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float = 0.0,
        latency_ms: int = 0,
    ):
        """Record LLM token usage and cost."""
        self.llm_tokens.labels(agent_name=agent_name, model=model, direction="input").inc(input_tokens)
        self.llm_tokens.labels(agent_name=agent_name, model=model, direction="output").inc(output_tokens)
        self.llm_cost.labels(agent_name=agent_name, model=model).inc(cost_usd)
        self.llm_calls.labels(agent_name=agent_name, model=model, status="success").inc()
        self.llm_latency.labels(agent_name=agent_name, model=model).observe(latency_ms / 1000.0)

    def record_alert(self, agent_name: str, severity: str):
        self.alerts_generated.labels(agent_name=agent_name, severity=severity).inc()

    def record_hitl_interrupt(self, agent_name: str, risk_level: str):
        self.hitl_interrupts.labels(agent_name=agent_name, risk_level=risk_level).inc()

    def record_hitl_decision(self, decision: str):
        self.hitl_decisions.labels(decision=decision).inc()

    def record_guardrail_violation(self, violation_type: str):
        self.guardrail_violations.labels(violation_type=violation_type).inc()

    def record_a2a_message(self, sender: str, receiver: str, success: bool):
        status = "success" if success else "error"
        self.a2a_messages.labels(sender=sender, receiver=receiver, status=status).inc()

    def record_retry(self, agent_name: str, attempt: int):
        self.retries.labels(agent_name=agent_name, attempt=str(attempt)).inc()

    def record_fallback(self, agent_name: str, primary: str, fallback: str):
        self.fallbacks.labels(
            agent_name=agent_name, primary_model=primary, fallback_model=fallback,
        ).inc()

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of metrics (for non-Prometheus environments)."""
        if not PROMETHEUS_AVAILABLE:
            return {"prometheus_available": False, "counters": self._counters}
        return {"prometheus_available": True, "message": "Metrics available at /metrics endpoint"}
