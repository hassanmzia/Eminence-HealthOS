# Eminence HealthOS — Agent Implementation Guide

## Table of Contents

1. [Overview: 5-Layer Agent Architecture](#1-overview-5-layer-agent-architecture)
2. [BaseAgent Class API Reference](#2-baseagent-class-api-reference)
3. [AgentTier Enum Values](#3-agenttier-enum-values)
4. [Step-by-Step: Creating a New Agent](#4-step-by-step-creating-a-new-agent)
5. [Agent Registration and Discovery](#5-agent-registration-and-discovery)
6. [Event Publishing Patterns](#6-event-publishing-patterns)
7. [RBAC and Multi-Tenant Considerations](#7-rbac-and-multi-tenant-considerations)
8. [Testing Agents](#8-testing-agents)
9. [Best Practices and Common Pitfalls](#9-best-practices-and-common-pitfalls)

---

## 1. Overview: 5-Layer Agent Architecture

HealthOS organizes all agents across five operational layers that form a directed data-processing pipeline. Data flows upward from sensing through measurement, with each layer adding clinical value.

```
┌─────────────────────────────────────────────────────────────┐
│ LAYER 5: MEASUREMENT                                       │
│ Outcome Measurement │ Population Health │ Executive Insight │
│ Cost/Risk Insight                                          │
├─────────────────────────────────────────────────────────────┤
│ LAYER 4: ACTION                                            │
│ Patient Communication │ Scheduling │ Prior Authorization   │
│ Referral Coordination │ Follow-Up Plan │ Task Orchestration│
├─────────────────────────────────────────────────────────────┤
│ LAYER 3: DECISIONING                                       │
│ Master Orchestrator │ Context Assembly │ Policy/Rules       │
│ Quality/Confidence │ Human-in-the-Loop                     │
├─────────────────────────────────────────────────────────────┤
│ LAYER 2: INTERPRETATION                                    │
│ Anomaly Detection │ Trend Analysis │ Risk Scoring          │
│ Medication Review                                          │
├─────────────────────────────────────────────────────────────┤
│ LAYER 1: SENSING & INGESTION                               │
│ Device Ingestion │ Vitals Normalization │ Insurance Verify  │
│ EHR/FHIR Connector Services                               │
└─────────────────────────────────────────────────────────────┘
```

### Layer Responsibilities

| Layer | Purpose | Example Agents |
|-------|---------|----------------|
| **Sensing** | Ingest raw data from devices, EHRs, and external sources; normalize and validate | `device_ingestion`, `vitals_normalization` |
| **Interpretation** | Analyze normalized data for anomalies, trends, and patterns | `anomaly_detection`, `trend_analysis` |
| **Decisioning** | Orchestrate agent execution, apply policies, gate high-impact actions, assemble context | `master_orchestrator`, `policy_rules`, `hitl` |
| **Action** | Generate clinical notes, send alerts, trigger referrals, schedule follow-ups | `clinical_note`, `alert_generation` |
| **Measurement** | Track outcomes, compute population health metrics, produce audit trails | `population_health`, `audit_trace`, `quality_confidence` |

### Implementation Pattern: Deterministic + LLM Hybrid

HealthOS agents use a hybrid approach:

- **Deterministic logic** for thresholds, scoring algorithms, rules engines, FHIR data mapping, and compliance-heavy steps.
- **LLM-powered reasoning** for summaries, note generation, patient messaging drafts, cross-source reasoning, and exception handling (routed through `LLMRouter`).
- **Policy gating** ensures all high-impact actions pass through the policy engine before execution.
- **Audit trail** ensures every agent action is logged with full decision chain traceability.

---

## 2. BaseAgent Class API Reference

**Source:** `healthos_platform/agents/base.py`

All agents inherit from `BaseAgent`. There is also a backward-compatible `HealthOSAgent` class for older module agents that uses a constructor-based initialization pattern.

### Class Attributes

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | `str` | `"base_agent"` | Unique identifier for the agent. Used in registry lookup, logging, and audit trails. |
| `tier` | `AgentTier` | `AgentTier.SENSING` | Which operational layer this agent belongs to. |
| `version` | `str` | `"1.0.0"` | Semantic version string for the agent implementation. |
| `description` | `str` | `""` | Human-readable description of the agent's purpose. |
| `requires_hitl` | `bool` | `False` | If `True`, all outputs are automatically flagged for human-in-the-loop review. |
| `min_confidence` | `float` | `0.0` | Confidence threshold. Outputs below this value are flagged for HITL review. |
| `max_retries` | `int` | `2` | Maximum retry attempts (reserved for future use). |

### Constructor: `__init__(self)`

Binds a structured logger (`structlog`) with the agent's `name`, `tier`, and `version` for consistent observability. Access via `self._log`.

### Core Methods

#### `run(input_data: AgentInput) -> AgentOutput` (public entry point)

The full lifecycle method. **Call this, not `process()` directly.** It wraps `process()` with:

1. **Timing** — Records `duration_ms` on the output.
2. **Input validation** — Calls `validate_input()` before processing.
3. **HITL gating** — Checks `requires_hitl` and `min_confidence`; sets `output.requires_hitl = True` and `output.status = AgentStatus.WAITING_HITL` if review is needed.
4. **Structured logging** — Logs `agent.start`, `agent.complete`, and `agent.error` events with trace ID, status, confidence, and duration.
5. **Error handling** — Catches all exceptions and delegates to `on_error()`.

#### `run_in_pipeline(state: PipelineState) -> PipelineState`

Executes the agent as part of a LangGraph pipeline. Converts `PipelineState` into an `AgentInput`, calls `run()`, and merges the output back into the shared state. After execution:

- Appends the agent name to `state.executed_agents`.
- Stores the `AgentOutput` in `state.agent_outputs[self.name]`.
- Propagates HITL flags to the pipeline state.

Many agents override this method to work directly with typed pipeline state fields (e.g., `state.normalized_vitals`, `state.anomalies`) instead of going through the generic `AgentInput.context` dictionary.

#### `process(input_data: AgentInput) -> AgentOutput` (abstract)

The core logic that subclasses must implement. Receives validated input and must return an `AgentOutput`. This is where the agent's clinical or operational logic lives.

#### `validate_input(input_data: AgentInput) -> None`

Override to add agent-specific input validation. Raise an exception to abort execution (the error will be caught by `run()` and routed to `on_error()`).

#### `on_error(input_data, error, duration_ms) -> AgentOutput`

Default error handler. Returns a `FAILED` status output with `requires_hitl=True` and the error message. Override for custom error recovery (e.g., falling back to a rule-based approach when an LLM call fails).

#### `build_output(trace_id, result, confidence, rationale, status) -> AgentOutput`

Convenience method for constructing a well-formed `AgentOutput` with the agent's name pre-filled. Prefer this over constructing `AgentOutput` manually.

### Data Contracts

**Source:** `healthos_platform/agents/types.py`

#### `AgentInput`

```python
class AgentInput(BaseModel):
    trace_id: uuid.UUID          # Correlation ID for distributed tracing
    org_id: uuid.UUID            # Tenant organization ID (required)
    patient_id: uuid.UUID | None # Patient scope (None for population-level agents)
    trigger: str                 # What triggered execution (event type or upstream agent)
    context: dict[str, Any]      # Payload — agent-specific data
    messages: list[AgentMessage]  # Inter-agent messages
```

`AgentInput` also exposes backward-compatible properties:
- `input.data` aliases `input.context`
- `input.tenant_id` aliases `input.org_id`

#### `AgentOutput`

```python
class AgentOutput(BaseModel):
    trace_id: uuid.UUID
    agent_name: str
    status: AgentStatus           # COMPLETED, FAILED, or WAITING_HITL
    confidence: float             # 0.0–1.0; how confident the agent is in its result
    result: dict[str, Any]        # Agent-specific output payload
    rationale: str                # Human-readable explanation of the decision
    errors: list[str]             # Error messages (if any)
    duration_ms: int              # Execution time (set by run())
    requires_hitl: bool           # Whether human review is needed
    hitl_reason: str | None       # Why review is needed
```

#### `PipelineState`

Shared state flowing through a LangGraph agent pipeline:

```python
class PipelineState(BaseModel):
    trace_id: uuid.UUID
    org_id: uuid.UUID
    patient_id: uuid.UUID
    trigger_event: str

    # Data flowing through the pipeline
    raw_vitals: list[VitalReading]
    normalized_vitals: list[NormalizedVital]
    anomalies: list[AnomalyDetection]
    risk_assessments: list[RiskAssessment]
    alert_requests: list[AlertRequest]

    # Agent execution tracking
    executed_agents: list[str]
    agent_outputs: dict[str, AgentOutput]

    # Policy and governance
    policy_violations: list[str]
    requires_hitl: bool
    hitl_reason: str | None

    # Context assembled for downstream agents
    patient_context: dict[str, Any]
```

---

## 3. AgentTier Enum Values

**Source:** `healthos_platform/agents/types.py`

```python
class AgentTier(str, Enum):
    SENSING = "sensing"              # Layer 1: Data ingestion & normalization
    INTERPRETATION = "interpretation"  # Layer 2: Analysis & anomaly detection
    DECISIONING = "decisioning"      # Layer 3: Risk scoring & policy checks
    ACTION = "action"                # Layer 4: Alerts, notifications, orders
    MEASUREMENT = "measurement"      # Layer 5: Outcomes & population health

    # Backward-compatible aliases
    MONITORING = "sensing"
    DIAGNOSTIC = "interpretation"
    RISK = "decisioning"
    INTERVENTION = "action"
```

### When to Use Each Tier

| Tier | Use When Your Agent... | HITL Expectations |
|------|----------------------|-------------------|
| `SENSING` | Ingests, normalizes, or validates raw data from external sources (devices, EHR, labs) | Rarely needs HITL; data quality issues are flagged but not blocked |
| `INTERPRETATION` | Analyzes data to detect patterns, anomalies, or trends; produces derived signals | Set `min_confidence` to flag uncertain interpretations for review |
| `DECISIONING` | Makes routing decisions, applies policies, assembles context, or gates actions | Often interacts with HITL; policy violations always trigger review |
| `ACTION` | Generates clinical content, sends alerts, creates orders, or communicates with patients | Strongly recommended to set `requires_hitl = True` for clinical actions |
| `MEASUREMENT` | Measures outcomes, computes population metrics, produces audit logs or quality scores | HITL typically not needed; focus is on observability and reporting |

### Choosing the Right Tier

Ask yourself: "What does this agent **produce**?"

- Raw/normalized data → `SENSING`
- Signals, anomalies, scores → `INTERPRETATION`
- Execution plans, policy decisions, context → `DECISIONING`
- Clinical artifacts, alerts, patient-facing content → `ACTION`
- Metrics, audit records, quality scores → `MEASUREMENT`

---

## 4. Step-by-Step: Creating a New Agent

### Step 1: Choose your tier and create the file

Place your agent in the appropriate module directory:

```
modules/
  rpm/agents/           # Remote Patient Monitoring agents
  telehealth/agents/    # Telehealth agents
  analytics/agents/     # Analytics and population health agents
  your_module/agents/   # Your module's agents
```

### Step 2: Define the agent class

Here is a minimal agent:

```python
"""
Eminence HealthOS — Medication Adherence Agent
Layer 2 (Interpretation): Analyzes prescription fill data and
patient-reported intake to calculate adherence scores.
"""
from __future__ import annotations

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentTier,
)


class MedicationAdherenceAgent(BaseAgent):
    name = "medication_adherence"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Calculates medication adherence scores from fill and intake data"
    min_confidence = 0.7  # Flag low-confidence results for pharmacist review

    async def process(self, input_data: AgentInput) -> AgentOutput:
        prescriptions = input_data.context.get("prescriptions", [])
        fill_history = input_data.context.get("fill_history", [])

        adherence_rate = self._calculate_adherence(prescriptions, fill_history)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "adherence_rate": adherence_rate,
                "prescriptions_analyzed": len(prescriptions),
                "risk_flag": adherence_rate < 0.8,
            },
            confidence=0.85 if fill_history else 0.5,
            rationale=(
                f"Medication adherence rate: {adherence_rate:.0%} "
                f"across {len(prescriptions)} prescriptions"
            ),
        )

    def _calculate_adherence(
        self, prescriptions: list, fill_history: list
    ) -> float:
        if not prescriptions:
            return 1.0
        filled = sum(1 for p in prescriptions if p.get("id") in
                     {f.get("prescription_id") for f in fill_history})
        return filled / len(prescriptions)
```

### Step 3: Add LLM enhancement (optional)

For agents that benefit from natural language reasoning, use the `LLMRouter`. This is the pattern used by `AnomalyDetectionAgent`, `ClinicalNoteAgent`, and `PopulationHealthAgent`:

```python
from healthos_platform.ml.llm.router import llm_router, LLMRequest

class MedicationAdherenceAgent(BaseAgent):
    # ... (class attributes as above)

    async def process(self, input_data: AgentInput) -> AgentOutput:
        # 1. Deterministic logic first
        adherence_rate = self._calculate_adherence(...)

        # 2. LLM enhancement with graceful fallback
        llm_insight = None
        try:
            llm_resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": f"Analyze adherence rate of {adherence_rate:.0%}..."}],
                system="You are a clinical pharmacist...",
                temperature=0.3,
                max_tokens=512,
            ))
            llm_insight = llm_resp.content
        except Exception as e:
            self._log.warning("llm_call_failed", error=str(e))

        result = {"adherence_rate": adherence_rate}
        if llm_insight:
            result["clinical_insight"] = llm_insight

        # 3. Adjust confidence based on LLM availability
        confidence = 0.90 if llm_insight else 0.75

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=confidence,
            rationale=f"Adherence: {adherence_rate:.0%}{' (LLM-enhanced)' if llm_insight else ''}",
        )
```

Key pattern: **always run deterministic logic first, then enhance with LLM**. If the LLM call fails, the agent still returns a valid result with lower confidence.

### Step 4: Override `run_in_pipeline` (if needed)

If your agent participates in the LangGraph pipeline and needs to read/write typed fields on `PipelineState`, override `run_in_pipeline`:

```python
async def run_in_pipeline(self, state: PipelineState) -> PipelineState:
    """Analyze medication adherence from patient context."""
    prescriptions = state.patient_context.get("prescriptions", [])
    # ... compute results ...

    # Write results back to shared state
    state.patient_context["medication_adherence"] = {
        "rate": adherence_rate,
        "risk_flag": adherence_rate < 0.8,
    }
    state.executed_agents.append(self.name)
    return state
```

### Step 5: Add input validation (optional)

```python
def validate_input(self, input_data: AgentInput) -> None:
    if not input_data.context.get("prescriptions"):
        raise ValueError("MedicationAdherenceAgent requires 'prescriptions' in context")
```

### Step 6: Add custom error handling (optional)

```python
def on_error(self, input_data: AgentInput, error: Exception, duration_ms: int) -> AgentOutput:
    # Return a safe fallback instead of failing hard
    return self.build_output(
        trace_id=input_data.trace_id,
        result={"adherence_rate": None, "error": str(error)},
        confidence=0.0,
        rationale=f"Agent failed: {error}. Manual review required.",
        status=AgentStatus.FAILED,
    )
```

---

## 5. Agent Registration and Discovery

**Source:** `healthos_platform/orchestrator/registry.py`

### The AgentRegistry Singleton

`AgentRegistry` is a process-wide singleton that tracks all registered agents. It supports lookup by name and by tier.

```python
from healthos_platform.orchestrator.registry import registry
```

### Registry API

| Method | Returns | Description |
|--------|---------|-------------|
| `registry.register(agent)` | `None` | Register a `BaseAgent` instance. Logs a warning and skips if name is duplicate. |
| `registry.get(name)` | `BaseAgent \| None` | Look up an agent by its unique name. |
| `registry.get_by_tier(tier)` | `list[BaseAgent]` | Get all agents registered under a specific `AgentTier`. |
| `registry.list_agents()` | `list[dict]` | List all agents with metadata (name, tier, version, description, requires_hitl). |
| `registry.agent_count` | `int` | Total number of registered agents. |
| `registry.reset()` | `None` | Clear all registrations. **Used in tests only.** |

### How to Register Your Agents

Each module provides a `register_*_agents()` function in its `agents/__init__.py`. This function is called during application startup.

**Example — RPM module** (`modules/rpm/agents/__init__.py`):

```python
from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent
from modules.rpm.agents.device_ingestion import DeviceIngestionAgent
from modules.rpm.agents.risk_scoring import RiskScoringAgent
from modules.rpm.agents.trend_analysis import TrendAnalysisAgent
from modules.rpm.agents.vitals_normalization import VitalsNormalizationAgent
from modules.rpm.agents.adherence_monitoring import AdherenceMonitoringAgent


def register_rpm_agents() -> None:
    """Register all RPM agents with the global registry."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(DeviceIngestionAgent())
    registry.register(VitalsNormalizationAgent())
    registry.register(AnomalyDetectionAgent())
    registry.register(RiskScoringAgent())
    registry.register(TrendAnalysisAgent())
    registry.register(AdherenceMonitoringAgent())
```

**Example — Core platform agents** (`healthos_platform/agents/__init__.py`):

```python
def register_core_agents() -> None:
    """Register all 6 core platform control agents."""
    from healthos_platform.orchestrator.registry import registry

    registry.register(MasterOrchestratorAgent())
    registry.register(ContextAssemblyAgent())
    registry.register(PolicyRulesAgent())
    registry.register(HumanInTheLoopAgent())
    registry.register(AuditTraceAgent())
    registry.register(QualityConfidenceAgent())
```

### Adding Your Module's Registration

1. Create your agents in `modules/your_module/agents/`.
2. Add a `register_your_module_agents()` function in `modules/your_module/agents/__init__.py`.
3. Call it during app startup alongside the other registration functions.

---

## 6. Event Publishing Patterns

**Source:** `healthos_platform/services/kafka.py`

HealthOS uses Apache Kafka for asynchronous event-driven communication between agents and services.

### Event Envelope: `HealthOSEvent`

Every Kafka message uses the `HealthOSEvent` schema:

```python
class HealthOSEvent(BaseModel):
    event_id: str           # Auto-generated UUID
    event_type: str         # e.g., "vitals.ingested", "alert.generated", "agent.completed"
    source: str             # e.g., "api", "agent:risk_scoring", "device:apple_watch"
    org_id: str             # Tenant ID (required for isolation)
    patient_id: str | None  # Patient scope
    timestamp: str          # ISO 8601
    payload: dict[str, Any] # Event-specific data
    trace_id: str | None    # Correlation ID for distributed tracing
    correlation_id: str | None
```

### Kafka Topics

| Topic | Events Routed Here |
|-------|-------------------|
| `healthos.vitals.ingested` | `vitals.*` events |
| `healthos.alerts.generated` | `alert.*` events |
| `healthos.agent.events` | `agent.*` events (default fallback) |
| `healthos.patient.events` | `patient.*` events |
| `healthos.workflow.events` | `workflow.*` and `operations.*` events |

Routing is automatic based on the `event_type` prefix.

### Publishing Events from an Agent

Use the convenience functions for common event types:

```python
from healthos_platform.services.kafka import (
    publish_agent_event,
    publish_alert_generated,
    publish_vital_ingested,
)

# After your agent completes processing:
await publish_agent_event(
    org_id=str(input_data.org_id),
    agent_name=self.name,
    action="completed",               # becomes event_type "agent.completed"
    payload={
        "result": output.result,
        "confidence": output.confidence,
    },
    trace_id=str(input_data.trace_id),
)

# When generating an alert:
await publish_alert_generated(
    org_id=str(input_data.org_id),
    patient_id=str(input_data.patient_id),
    alert_data={
        "severity": "critical",
        "message": "SpO2 below 85%",
    },
    trace_id=str(input_data.trace_id),
)
```

For custom event types, use the generic `publish_event`:

```python
from healthos_platform.services.kafka import publish_event, HealthOSEvent

await publish_event(HealthOSEvent(
    event_type="workflow.care_plan.updated",
    source=f"agent:{self.name}",
    org_id=str(input_data.org_id),
    patient_id=str(input_data.patient_id),
    payload={"plan_id": plan_id, "changes": changes},
    trace_id=str(input_data.trace_id),
))
```

### Consuming Events

Register event handlers using the `EventConsumer` class:

```python
from healthos_platform.services.kafka import EventConsumer, HealthOSEvent, TOPIC_AGENT_EVENTS

async def handle_agent_completed(event: HealthOSEvent) -> None:
    # React to agent completion events
    agent_name = event.payload.get("agent_name")
    ...

consumer = EventConsumer(
    topics=[TOPIC_AGENT_EVENTS],
    group_id="my-handler-group",
)
consumer.register("agent.completed", handle_agent_completed)
consumer.register("agent.*", handle_any_agent_event)  # Wildcard prefix match
await consumer.start()
```

---

## 7. RBAC and Multi-Tenant Considerations

### Multi-Tenancy: `org_id` Is Mandatory

Every `AgentInput` carries an `org_id` (aliased as `tenant_id`). Every `PipelineState` carries an `org_id`. All data models (`VitalReading`, `AnomalyDetection`, `RiskAssessment`, `AlertRequest`) include both `patient_id` and `org_id`.

**Rule:** Never process data without verifying it belongs to the current tenant. Never produce output that leaks data across tenant boundaries.

### Tenant Isolation Layer

**Source:** `healthos_platform/security/tenant_isolation.py`

Tenant context is propagated via a Python `ContextVar`:

```python
from healthos_platform.security.tenant_isolation import (
    TenantScope,
    set_tenant_scope,
    get_tenant_scope,
    require_tenant_scope,
)
```

`TenantScope` is an immutable dataclass containing the `tenant_id`, `org_id`, `user_id`, `role`, and `permissions` for the current request.

### TenantAwareAgent Mixin

For agents that need to validate cross-tenant data access, use the `TenantAwareAgent` mixin:

```python
from healthos_platform.security.tenant_isolation import TenantAwareAgent

class MySecureAgent(BaseAgent, TenantAwareAgent):
    name = "my_secure_agent"
    tier = AgentTier.INTERPRETATION

    async def process(self, input_data: AgentInput) -> AgentOutput:
        records = input_data.context.get("records", [])

        # Validate each record belongs to the current tenant
        safe_records = [r for r in records if self.validate_tenant_access(r, "org_id")]

        result = self._analyze(safe_records)

        # Tag output with tenant context for audit
        result = self.tag_output(result)

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.9,
            rationale=f"Processed {len(safe_records)} tenant-scoped records",
        )
```

The mixin provides:

| Method | Purpose |
|--------|---------|
| `get_tenant_id()` | Returns the current tenant ID from context (or `"default"` if none set) |
| `validate_tenant_access(data, tenant_field)` | Checks that a data record belongs to the current tenant |
| `tag_output(result)` | Adds `_tenant_id` and `_org_id` metadata to output dicts |

### RBAC Roles and Permissions

**Source:** `healthos_platform/security/rbac.py`

| Role | Key Permissions | Agent Relevance |
|------|----------------|-----------------|
| `admin` | All permissions | Can manage agents, view audit logs |
| `clinician` | Read/write patients, vitals, encounters, care plans; view agents | Primary consumer of Action-layer agent outputs; signs off on HITL reviews |
| `care_manager` | Read/write patients, care plans; acknowledge alerts; view agents | Reviews care plans generated by agents |
| `nurse` | Read patients, read/write vitals, acknowledge alerts; view agents | Monitors Sensing-layer agent outputs (vitals dashboards) |
| `patient` | Read own vitals, alerts, encounters, care plans | Sees patient-facing summaries produced by Action-layer agents |
| `system` | All permissions | Internal agent-to-agent communication; agents run as `system` role |

Agents themselves execute with `system` role privileges. The RBAC layer is enforced at the API boundary, controlling which users can view agent outputs, acknowledge alerts, or approve HITL requests.

```python
from healthos_platform.security.rbac import has_permission, Permission

# Checked at API/service layer, not inside agents themselves:
if not has_permission(user.role, Permission.ALERTS_ACKNOWLEDGE):
    raise HTTPException(403, "Insufficient permissions")
```

### Multi-Tenant Guidelines for Agent Authors

1. **Always scope queries by `org_id`.** Never run unscoped database queries.
2. **Validate `org_id` on input data** matches the pipeline's `org_id` when processing lists of records.
3. **Use `TenantAwareAgent` mixin** when your agent processes data from multiple sources that could cross tenant boundaries.
4. **Include `org_id` in published events** so downstream consumers can enforce isolation.
5. **Never log PHI** (patient names, SSNs, full DOB) in agent logs. Use patient IDs and trace IDs only.

---

## 8. Testing Agents

**Source:** `tests/unit/test_agents.py`, `tests/unit/test_core_agents.py`

### Test Structure

Agent tests follow a consistent pattern:

1. **Identity tests** — Verify agent name and tier.
2. **Unit tests** — Test internal helper methods directly.
3. **Pipeline tests** — Run the agent via `run_in_pipeline()` with a prepared `PipelineState`.
4. **Standalone tests** — Run the agent via `run()` with an `AgentInput`.
5. **Integration tests** — Run a full multi-agent pipeline end-to-end.

### Fixtures

Standard fixtures used across agent tests:

```python
import uuid
from datetime import datetime, timezone
import pytest
from healthos_platform.agents.types import (
    AgentInput, PipelineState, NormalizedVital, VitalType,
)

@pytest.fixture
def org_id():
    return uuid.uuid4()

@pytest.fixture
def patient_id():
    return uuid.uuid4()

@pytest.fixture
def pipeline_state(org_id, patient_id):
    return PipelineState(
        org_id=org_id,
        patient_id=patient_id,
        trigger_event="vitals.ingested",
        patient_context={"raw_vitals": [...]},
    )
```

### Example: Testing a Standalone Agent

```python
@pytest.mark.asyncio
async def test_my_agent_standalone():
    from modules.my_module.agents.my_agent import MyAgent

    agent = MyAgent()

    # Verify identity
    assert agent.name == "my_agent"
    assert agent.tier == AgentTier.INTERPRETATION

    # Run with AgentInput
    input_data = AgentInput(
        org_id=uuid.uuid4(),
        trigger="test",
        context={"key": "value"},
    )
    output = await agent.run(input_data)

    assert output.status == AgentStatus.COMPLETED
    assert output.confidence > 0
    assert "expected_key" in output.result
```

### Example: Testing Pipeline Integration

```python
@pytest.mark.asyncio
async def test_my_agent_in_pipeline(pipeline_state):
    from modules.my_module.agents.my_agent import MyAgent

    # Run upstream agents first to populate state
    state = await UpstreamAgent().run_in_pipeline(pipeline_state)

    # Run agent under test
    agent = MyAgent()
    state = await agent.run_in_pipeline(state)

    assert "my_agent" in state.executed_agents
    assert state.patient_context.get("expected_field") is not None
```

### Example: Testing Internal Methods

```python
@pytest.mark.asyncio
async def test_anomaly_detection_critical_spo2():
    from modules.rpm.agents.anomaly_detection import AnomalyDetectionAgent

    detector = AnomalyDetectionAgent()

    state = PipelineState(
        org_id=uuid.uuid4(),
        patient_id=uuid.uuid4(),
        normalized_vitals=[
            NormalizedVital(
                patient_id=patient_id,
                org_id=org_id,
                vital_type=VitalType.SPO2,
                value={"value": 82},
                unit="%",
                recorded_at=datetime.now(timezone.utc),
                source="wearable",
                quality_score=1.0,
            )
        ],
    )

    state = await detector.run_in_pipeline(state)
    critical = [a for a in state.anomalies if a.severity == Severity.CRITICAL]
    assert len(critical) >= 1
```

### Example: Full Pipeline End-to-End Test

```python
@pytest.mark.asyncio
async def test_full_rpm_pipeline(pipeline_state):
    agents = [
        DeviceIngestionAgent(),
        VitalsNormalizationAgent(),
        AnomalyDetectionAgent(),
        RiskScoringAgent(),
        TrendAnalysisAgent(),
        AdherenceMonitoringAgent(),
    ]

    state = pipeline_state
    for agent in agents:
        state = await agent.run_in_pipeline(state)

    assert len(state.executed_agents) == 6
    assert len(state.raw_vitals) > 0
    assert len(state.normalized_vitals) > 0
    assert len(state.risk_assessments) > 0
```

### Testing the Registry

```python
def test_agent_registration():
    from modules.my_module.agents import register_my_module_agents

    reg = AgentRegistry()
    reg.reset()  # Clean slate for test isolation
    register_my_module_agents()

    assert reg.agent_count == 3  # however many agents your module has
    assert reg.get("my_agent") is not None

    tier_agents = reg.get_by_tier(AgentTier.INTERPRETATION)
    assert any(a.name == "my_agent" for a in tier_agents)
```

### Mocking LLM Calls

For agents that use `llm_router`, mock the LLM layer to avoid real API calls in tests:

```python
from unittest.mock import AsyncMock, patch

@pytest.mark.asyncio
async def test_agent_with_mocked_llm():
    with patch("modules.my_module.agents.my_agent.llm_router") as mock_router:
        mock_router.complete = AsyncMock(return_value=MockLLMResponse(content="Test insight"))

        agent = MyAgent()
        output = await agent.run(input_data)

        assert output.result.get("llm_insight") == "Test insight"
```

---

## 9. Best Practices and Common Pitfalls

### Best Practices

**1. Deterministic first, LLM second.**
Always implement rule-based logic as the primary path. Use LLM calls to enhance results (summaries, narratives, clinical interpretations). Wrap LLM calls in try/except and adjust confidence downward when the LLM is unavailable. See `AnomalyDetectionAgent` and `ClinicalNoteAgent` for examples of this pattern.

**2. Always use `build_output()` instead of constructing `AgentOutput` directly.**
It pre-fills `agent_name` and provides a consistent constructor signature.

**3. Set `min_confidence` thoughtfully.**
The `run()` method automatically flags outputs below `min_confidence` for human review. Set it based on the clinical risk profile of your agent's outputs:
- Informational outputs (dashboards, metrics): `0.0` or `0.5`
- Clinical decision support: `0.6` to `0.7`
- Action-layer agents (notes, orders): `0.7` to `0.8`

**4. Set `requires_hitl = True` for clinical-action agents.**
The `ClinicalNoteAgent` sets `requires_hitl = True` because providers must review and sign notes. Any agent whose output directly affects patient care should do the same.

**5. Include meaningful `rationale` strings.**
The `rationale` field is surfaced in audit logs and HITL review screens. Make it specific and quantitative: `"Detected 3 anomalies across 12 readings"` rather than `"Processing complete"`.

**6. Scope everything by `org_id`.**
Every query, every event, and every output must carry the organization scope. This is how HealthOS enforces tenant isolation.

**7. Use structured logging via `self._log`.**
The base class binds `agent`, `tier`, and `version` to every log entry. Add context-specific fields:
```python
self._log.info("analysis.complete", anomalies_found=len(anomalies), patient_id=str(patient_id))
```

**8. Version your agents.**
Bump the `version` attribute when you change agent logic. This is tracked in the registry and audit trail, making it possible to correlate behavior changes with deployments.

### Common Pitfalls

**1. Calling `process()` directly instead of `run()`.**
`process()` skips timing, logging, HITL gating, and error handling. Always use `run()` or `run_in_pipeline()` from external callers.

**2. Forgetting to append to `state.executed_agents` in `run_in_pipeline` overrides.**
If you override `run_in_pipeline`, you must add `state.executed_agents.append(self.name)` yourself. The base class does this in its default implementation, but custom overrides bypass it.

**3. Letting LLM failures crash the agent.**
Never let an LLM call propagate an unhandled exception. Always wrap in try/except and fall back to rule-based results:
```python
try:
    llm_resp = await llm_router.complete(...)
    result["narrative"] = llm_resp.content
except Exception as e:
    self._log.warning("llm_failed", error=str(e))
    # Agent continues with deterministic result only
```

**4. Returning confidence of 1.0.**
No automated system should claim 100% confidence. Use `0.95` as a practical ceiling for high-confidence results.

**5. Registering an agent with a duplicate name.**
The registry silently skips duplicates and logs a warning. Ensure each agent has a globally unique `name` attribute.

**6. Not testing the error path.**
Test what happens when your agent receives empty input, malformed data, or when downstream services are unavailable. The `on_error()` handler should produce a safe, reviewable output.

**7. Performing database writes inside `process()`.**
Agents should be pure functions over their input data. Persist results through the pipeline state or event bus, not by writing directly to the database inside the agent. This keeps agents testable and idempotent.

**8. Ignoring the `trace_id`.**
The `trace_id` connects an entire agent pipeline execution. Always pass it through to `build_output()`, published events, and log entries. It is the primary key for distributed tracing and audit reconstruction.
