"""
Base agent class for all HealthOS AI agents.

Every agent in the 30-agent architecture inherits from HealthOSAgent.
Provides lifecycle hooks, observability, decision recording, and
standardized input/output contracts.
"""

import logging
import time
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional


class AgentTier(str, Enum):
    MONITORING = "monitoring"       # Tier 1 — continuous data monitoring
    DIAGNOSTIC = "diagnostic"       # Tier 2 — analysis and diagnosis
    RISK = "risk"                   # Tier 3 — risk stratification
    INTERVENTION = "intervention"   # Tier 4 — care recommendations
    ACTION = "action"               # Tier 5 — execution and notification


class AgentCapability(str, Enum):
    VITAL_MONITORING = "vital_monitoring"
    LAB_ANALYSIS = "lab_analysis"
    RISK_SCORING = "risk_scoring"
    DRUG_INTERACTION = "drug_interaction"
    CARE_PLAN_GENERATION = "care_plan_generation"
    ALERT_GENERATION = "alert_generation"
    PATIENT_COMMUNICATION = "patient_communication"
    DEVICE_INTEGRATION = "device_integration"
    CLINICAL_SUMMARY = "clinical_summary"
    TRIAGE = "triage"


@dataclass
class AgentInput:
    """Standardized input to an agent."""
    patient_id: Optional[str] = None
    tenant_id: str = "default"
    trace_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data: dict = field(default_factory=dict)
    context: dict = field(default_factory=dict)
    source_agent: Optional[str] = None
    priority: str = "normal"  # low, normal, high, critical


@dataclass
class AgentOutput:
    """Standardized output from an agent."""
    agent_name: str
    agent_tier: str
    decision: str
    rationale: str = ""
    confidence: float = 0.0
    data: dict = field(default_factory=dict)
    feature_contributions: list = field(default_factory=list)
    alternatives: list = field(default_factory=list)
    evidence_references: list = field(default_factory=list)
    requires_hitl: bool = False
    safety_flags: list = field(default_factory=list)
    risk_level: Optional[str] = None
    downstream_agents: list = field(default_factory=list)
    duration_ms: int = 0
    model_used: Optional[str] = None
    input_tokens: int = 0
    output_tokens: int = 0


class HealthOSAgent(ABC):
    """
    Abstract base class for all HealthOS agents.

    Subclasses must implement:
        - process(input: AgentInput) -> AgentOutput
        - capabilities (property)
    """

    def __init__(
        self,
        name: str,
        tier: AgentTier,
        description: str = "",
        version: str = "0.1.0",
    ):
        self.name = name
        self.tier = tier
        self.description = description
        self.version = version
        self.logger = logging.getLogger(f"healthos.agent.{name}")
        self._is_initialized = False

    @property
    @abstractmethod
    def capabilities(self) -> list[AgentCapability]:
        """List of capabilities this agent provides."""
        ...

    @abstractmethod
    async def process(self, agent_input: AgentInput) -> AgentOutput:
        """Core processing logic — implemented by each agent."""
        ...

    async def initialize(self) -> None:
        """Optional startup hook — load models, warm caches, etc."""
        self._is_initialized = True

    async def shutdown(self) -> None:
        """Optional cleanup hook."""
        self._is_initialized = False

    async def execute(self, agent_input: AgentInput) -> AgentOutput:
        """
        Full execution pipeline with observability.

        Wraps process() with timing, logging, and decision recording.
        """
        if not self._is_initialized:
            await self.initialize()

        start = time.monotonic()
        self.logger.info(
            "Executing agent=%s tier=%s trace=%s patient=%s",
            self.name,
            self.tier.value,
            agent_input.trace_id[:12],
            agent_input.patient_id or "N/A",
        )

        try:
            output = await self.process(agent_input)
            output.agent_name = self.name
            output.agent_tier = self.tier.value
            output.duration_ms = int((time.monotonic() - start) * 1000)

            self.logger.info(
                "Agent %s completed in %dms confidence=%.2f hitl=%s",
                self.name,
                output.duration_ms,
                output.confidence,
                output.requires_hitl,
            )

            # Record decision for audit trail
            await self._record_decision(agent_input, output)

            return output

        except Exception as e:
            duration_ms = int((time.monotonic() - start) * 1000)
            self.logger.error(
                "Agent %s failed after %dms: %s",
                self.name,
                duration_ms,
                str(e),
            )
            raise

    async def _record_decision(
        self, agent_input: AgentInput, output: AgentOutput,
    ) -> None:
        """Persist the decision to the database for audit and explainability."""
        try:
            from platform.config.database import get_db_context
            from shared.models.agent import AgentDecision

            async with get_db_context() as db:
                decision = AgentDecision(
                    tenant_id=agent_input.tenant_id,
                    trace_id=agent_input.trace_id,
                    agent_name=output.agent_name,
                    agent_tier=output.agent_tier,
                    patient_id=agent_input.patient_id,
                    decision_type="recommendation",
                    decision=output.decision,
                    rationale=output.rationale,
                    confidence=output.confidence,
                    feature_contributions=output.feature_contributions,
                    alternatives=output.alternatives,
                    evidence_references=output.evidence_references,
                    requires_hitl=output.requires_hitl,
                    safety_flags=output.safety_flags,
                    risk_level=output.risk_level,
                    input_summary=agent_input.data,
                    output_summary=output.data,
                    duration_ms=output.duration_ms,
                    model_used=output.model_used,
                    input_tokens=output.input_tokens,
                    output_tokens=output.output_tokens,
                )
                db.add(decision)
        except Exception as e:
            self.logger.warning("Failed to record decision: %s", e)

    def __repr__(self):
        return f"<Agent {self.name} [{self.tier.value}] v{self.version}>"
