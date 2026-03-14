"""
Eminence HealthOS — Base Agent Framework
All HealthOS agents inherit from BaseAgent, ensuring consistent lifecycle,
audit logging, error handling, and observability.
"""

from __future__ import annotations

import time
import uuid
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

import structlog

from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
    PipelineState,
)

logger = structlog.get_logger()


# ── Backward-Compatible Enums for Module Agents ──────────────────────────────

class AgentCapability(str, Enum):
    """Capabilities that agents can declare."""
    VITAL_MONITORING = "vital_monitoring"
    ANOMALY_DETECTION = "anomaly_detection"
    RISK_SCORING = "risk_scoring"
    ALERT_GENERATION = "alert_generation"
    CLINICAL_SUMMARY = "clinical_summary"
    CARE_PLAN_GENERATION = "care_plan_generation"
    MEDICATION_CHECK = "medication_check"
    PATIENT_COMMUNICATION = "patient_communication"
    LAB_ANALYSIS = "lab_analysis"
    SCHEDULING = "scheduling"
    COMPLIANCE_CHECK = "compliance_check"
    RESOURCE_OPTIMIZATION = "resource_optimization"
    DEVICE_INTEGRATION = "device_integration"


class BaseAgent(ABC):
    """
    Abstract base class for all HealthOS agents.

    Every agent must:
    1. Declare its name, tier, and version
    2. Implement the `process()` method
    3. Optionally override `validate_input()` and `on_error()`

    The `run()` method wraps `process()` with timing, logging, and audit.
    """

    name: str = "base_agent"
    tier: AgentTier = AgentTier.SENSING
    version: str = "1.0.0"
    description: str = ""
    requires_hitl: bool = False  # If True, always pause for human review

    # Clinical safety thresholds
    min_confidence: float = 0.0  # Below this, flag for review
    max_retries: int = 2

    def __init__(self) -> None:
        self._log = logger.bind(agent=self.name, tier=self.tier.value, version=self.version)

    # ── Public API ───────────────────────────────────────────────────────────

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """
        Execute the agent with full lifecycle management.
        Wraps process() with timing, error handling, and audit.
        """
        start = time.monotonic()
        trace_id = input_data.trace_id

        self._log.info("agent.start", trace_id=str(trace_id), trigger=input_data.trigger)

        try:
            # Validate input
            self.validate_input(input_data)

            # Execute the agent's core logic
            output = await self.process(input_data)

            # Check if HITL review is needed
            if self.requires_hitl or output.confidence < self.min_confidence:
                output.requires_hitl = True
                output.hitl_reason = output.hitl_reason or (
                    f"Confidence {output.confidence:.2f} below threshold {self.min_confidence}"
                )
                output.status = AgentStatus.WAITING_HITL

            duration_ms = int((time.monotonic() - start) * 1000)
            output.duration_ms = duration_ms

            self._log.info(
                "agent.complete",
                trace_id=str(trace_id),
                status=output.status.value,
                confidence=output.confidence,
                duration_ms=duration_ms,
                requires_hitl=output.requires_hitl,
            )

            return output

        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.error(
                "agent.error",
                trace_id=str(trace_id),
                error=str(exc),
                duration_ms=duration_ms,
            )
            return self.on_error(input_data, exc, duration_ms)

    async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
        """
        Execute this agent as part of a LangGraph pipeline.
        Converts pipeline state to AgentInput, runs, and merges output back.
        """
        agent_input = AgentInput(
            trace_id=state.trace_id,
            org_id=state.org_id,
            patient_id=state.patient_id,
            trigger=state.trigger_event,
            context={
                "patient_context": state.patient_context,
                "normalized_vitals": [v.model_dump() for v in state.normalized_vitals],
                "anomalies": [a.model_dump() for a in state.anomalies],
                "risk_assessments": [r.model_dump() for r in state.risk_assessments],
            },
        )

        output = await self.run(agent_input)

        # Merge output into pipeline state
        state.executed_agents.append(self.name)
        state.agent_outputs[self.name] = output

        if output.requires_hitl:
            state.requires_hitl = True
            state.hitl_reason = output.hitl_reason

        return state

    # ── Abstract / Override Points ───────────────────────────────────────────

    @abstractmethod
    async def process(self, input_data: AgentInput) -> AgentOutput:
        """Core agent logic. Must be implemented by subclasses."""
        ...

    def validate_input(self, input_data: AgentInput) -> None:
        """Validate input data. Override to add agent-specific checks."""
        pass

    def on_error(self, input_data: AgentInput, error: Exception, duration_ms: int) -> AgentOutput:
        """Handle errors. Override for agent-specific error recovery."""
        return AgentOutput(
            trace_id=input_data.trace_id,
            agent_name=self.name,
            status=AgentStatus.FAILED,
            confidence=0.0,
            result={},
            rationale=f"Agent failed: {error}",
            errors=[str(error)],
            duration_ms=duration_ms,
            requires_hitl=True,
            hitl_reason=f"Agent {self.name} failed and requires manual review",
        )

    # ── Utility Methods ──────────────────────────────────────────────────────

    def build_output(
        self,
        trace_id: uuid.UUID,
        result: dict[str, Any],
        confidence: float,
        rationale: str,
        status: AgentStatus = AgentStatus.COMPLETED,
    ) -> AgentOutput:
        """Helper to build a standard AgentOutput."""
        return AgentOutput(
            trace_id=trace_id,
            agent_name=self.name,
            status=status,
            confidence=confidence,
            result=result,
            rationale=rationale,
        )


class HealthOSAgent(ABC):
    """
    Backward-compatible base class for module agents.
    Provides the older-style __init__(name, tier, ...) constructor pattern.
    """

    def __init__(
        self,
        name: str,
        tier: AgentTier,
        description: str = "",
        version: str = "0.1.0",
    ) -> None:
        self.name = name
        self.tier = tier
        self.description = description
        self.version = version
        self._log = logger.bind(agent=self.name, tier=self.tier.value, version=self.version)

    @property
    def capabilities(self) -> list[AgentCapability]:
        return []

    @abstractmethod
    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """Core agent logic. Must be implemented by subclasses."""
        ...

    async def run(self, input_data: AgentInput) -> AgentOutput:
        """Execute with timing and error handling."""
        start = time.monotonic()
        try:
            output = await self.process(input_data)
            output.duration_ms = int((time.monotonic() - start) * 1000)
            return output
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            self._log.error("agent.error", error=str(exc), duration_ms=duration_ms)
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                status=AgentStatus.FAILED,
                confidence=0.0,
                rationale=f"Agent failed: {exc}",
                errors=[str(exc)],
                duration_ms=duration_ms,
            )
