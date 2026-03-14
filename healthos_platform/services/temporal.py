"""
Eminence HealthOS — Temporal Workflow Integration
Bridges the existing agent pipeline with Temporal for durable, long-running
clinical workflows.  Provides workflow definitions for patient onboarding,
critical alert escalation, and RPM review cycles, along with activity
wrappers that delegate to the HealthOS agent execution engine.

When the Temporal server is unreachable the module degrades gracefully:
the singleton client stays disconnected and callers receive clear errors
rather than unhandled exceptions.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

# ---------------------------------------------------------------------------
# Temporal SDK imports — guarded so the rest of the platform can load even
# when the SDK is not installed.
# ---------------------------------------------------------------------------
try:
    from temporalio import activity, workflow
    from temporalio.client import Client as _TemporalClient
    from temporalio.common import RetryPolicy
    from temporalio.worker import Worker

    TEMPORAL_AVAILABLE = True
except ImportError:  # pragma: no cover
    TEMPORAL_AVAILABLE = False

logger = logging.getLogger("healthos.temporal")

# Task queue shared by all clinical workflows / activities.
CLINICAL_TASK_QUEUE = "healthos-clinical"

# Default retry policy used by activities unless overridden.
_DEFAULT_RETRY_POLICY = (
    RetryPolicy(
        initial_interval=timedelta(seconds=1),
        backoff_coefficient=2.0,
        maximum_interval=timedelta(minutes=5),
        maximum_attempts=5,
        non_retryable_error_types=["ClinicalValidationError", "PatientNotFoundError"],
    )
    if TEMPORAL_AVAILABLE
    else None
)


# ═══════════════════════════════════════════════════════════════════════════════
# TEMPORAL CLIENT — Singleton async wrapper
# ═══════════════════════════════════════════════════════════════════════════════


class TemporalClient:
    """Singleton async wrapper around the Temporal SDK client.

    Usage::

        client = TemporalClient()
        await client.connect("localhost:7233")
        handle = await client.start_workflow(...)
        await client.close()
    """

    _instance: TemporalClient | None = None
    _client: _TemporalClient | None = None  # type: ignore[assignment]

    def __new__(cls) -> TemporalClient:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    # -- lifecycle -----------------------------------------------------------

    async def connect(
        self,
        target_host: str = "localhost:7233",
        namespace: str = "default",
    ) -> None:
        """Open a connection to the Temporal server."""
        if not TEMPORAL_AVAILABLE:
            logger.error(
                "temporal.sdk_missing — install temporalio to enable Temporal workflows"
            )
            return
        try:
            self._client = await _TemporalClient.connect(
                target_host, namespace=namespace
            )
            logger.info(
                "temporal.connected",
                extra={"target_host": target_host, "namespace": namespace},
            )
        except Exception:
            logger.exception("temporal.connect_failed")
            self._client = None

    async def close(self) -> None:
        """Release the Temporal client connection."""
        # The Temporal Python SDK client is lightweight and does not expose an
        # explicit ``close()``; we simply discard the reference.
        self._client = None
        logger.info("temporal.disconnected")

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    # -- helpers -------------------------------------------------------------

    def _ensure_client(self) -> _TemporalClient:  # type: ignore[return]
        if self._client is None:
            raise RuntimeError(
                "TemporalClient is not connected — call await client.connect() first"
            )
        return self._client

    # -- workflow operations -------------------------------------------------

    async def start_workflow(
        self,
        workflow_name: str,
        args: Any,
        *,
        task_queue: str = CLINICAL_TASK_QUEUE,
        workflow_id: str | None = None,
    ) -> str:
        """Start a Temporal workflow and return the workflow ID."""
        client = self._ensure_client()
        wf_id = workflow_id or f"healthos-{workflow_name}-{uuid.uuid4().hex[:12]}"

        # Look up the workflow class by name from our registry.
        wf_cls = _WORKFLOW_REGISTRY.get(workflow_name)
        if wf_cls is None:
            raise ValueError(f"Unknown workflow: {workflow_name}")

        handle = await client.start_workflow(
            wf_cls.run,
            args,
            id=wf_id,
            task_queue=task_queue,
        )
        logger.info(
            "temporal.workflow.started",
            extra={"workflow_id": handle.id, "workflow_name": workflow_name},
        )
        return handle.id

    async def signal_workflow(
        self,
        workflow_id: str,
        signal_name: str,
        payload: Any = None,
    ) -> None:
        """Send a signal to a running workflow."""
        client = self._ensure_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.signal(signal_name, payload)
        logger.info(
            "temporal.workflow.signaled",
            extra={"workflow_id": workflow_id, "signal": signal_name},
        )

    async def query_workflow(
        self,
        workflow_id: str,
        query_name: str,
    ) -> Any:
        """Query the state of a running workflow."""
        client = self._ensure_client()
        handle = client.get_workflow_handle(workflow_id)
        result = await handle.query(query_name)
        return result

    async def cancel_workflow(self, workflow_id: str) -> None:
        """Request cancellation of a running workflow."""
        client = self._ensure_client()
        handle = client.get_workflow_handle(workflow_id)
        await handle.cancel()
        logger.info(
            "temporal.workflow.cancelled",
            extra={"workflow_id": workflow_id},
        )


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY INPUT / OUTPUT DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class AgentActivityInput:
    """Payload handed to the ``run_agent_activity`` activity."""

    agent_name: str
    org_id: str
    patient_id: str | None = None
    context: dict[str, Any] | None = None


@dataclass
class AgentActivityResult:
    """Value returned by ``run_agent_activity``."""

    agent_name: str
    status: str
    result: dict[str, Any] | None = None
    errors: list[str] | None = None


@dataclass
class NotificationInput:
    provider_id: str
    message: str
    channel: str  # "sms" | "email" | "push" | "in_app"


@dataclass
class CreateEncounterInput:
    patient_id: str
    encounter_type: str
    reason: str
    org_id: str | None = None


@dataclass
class UpdatePatientStatusInput:
    patient_id: str
    status_updates: dict[str, Any]


# ═══════════════════════════════════════════════════════════════════════════════
# ACTIVITY DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

if TEMPORAL_AVAILABLE:

    @activity.defn(name="run_agent")
    async def run_agent_activity(input: AgentActivityInput) -> AgentActivityResult:
        """Execute a HealthOS agent as a Temporal activity.

        This bridges the existing ``ExecutionEngine.execute_single`` path so
        every agent invocation gains Temporal's automatic retries and
        heartbeat-based timeout detection.
        """
        from healthos_platform.agents.types import AgentInput
        from healthos_platform.orchestrator.engine import ExecutionEngine

        activity.heartbeat(f"starting agent {input.agent_name}")

        engine = ExecutionEngine()
        agent_input = AgentInput(
            org_id=uuid.UUID(input.org_id),
            patient_id=uuid.UUID(input.patient_id) if input.patient_id else None,
            trigger="temporal_activity",
            context=input.context or {},
        )

        output = await engine.execute_single(input.agent_name, agent_input)

        activity.heartbeat(f"agent {input.agent_name} finished")
        return AgentActivityResult(
            agent_name=input.agent_name,
            status=output.status.value,
            result=output.result,
            errors=output.errors if output.errors else None,
        )

    @activity.defn(name="send_notification")
    async def send_notification_activity(input: NotificationInput) -> dict[str, Any]:
        """Send a notification to a clinical provider.

        Currently delegates to the Celery notification worker; a future
        iteration can call an external messaging service directly.
        """
        activity.heartbeat(f"notifying {input.provider_id} via {input.channel}")

        from healthos_platform.services.workers import send_alert_notification

        # Fire the Celery task asynchronously — we don't block on it.
        send_alert_notification.delay(input.provider_id, [input.channel])

        return {
            "provider_id": input.provider_id,
            "channel": input.channel,
            "status": "dispatched",
        }

    @activity.defn(name="create_encounter")
    async def create_encounter_activity(input: CreateEncounterInput) -> dict[str, Any]:
        """Create an encounter record for a patient."""
        activity.heartbeat(f"creating encounter for patient {input.patient_id}")

        encounter_id = f"ENC-{uuid.uuid4().hex[:12]}"
        logger.info(
            "temporal.activity.encounter_created",
            extra={
                "encounter_id": encounter_id,
                "patient_id": input.patient_id,
                "encounter_type": input.encounter_type,
                "reason": input.reason,
            },
        )
        return {
            "encounter_id": encounter_id,
            "patient_id": input.patient_id,
            "encounter_type": input.encounter_type,
            "reason": input.reason,
            "status": "created",
        }

    @activity.defn(name="update_patient_status")
    async def update_patient_status_activity(
        input: UpdatePatientStatusInput,
    ) -> dict[str, Any]:
        """Apply status updates to a patient record."""
        activity.heartbeat(f"updating patient {input.patient_id}")

        logger.info(
            "temporal.activity.patient_status_updated",
            extra={
                "patient_id": input.patient_id,
                "updates": list(input.status_updates.keys()),
            },
        )
        return {
            "patient_id": input.patient_id,
            "updated_fields": list(input.status_updates.keys()),
            "status": "updated",
        }


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════


@dataclass
class PatientOnboardingInput:
    patient_id: str
    org_id: str
    insurance_info: dict[str, Any] | None = None
    care_preferences: dict[str, Any] | None = None


@dataclass
class CriticalAlertInput:
    alert_id: str
    patient_id: str
    org_id: str
    provider_id: str
    severity: str  # "high" | "critical"
    message: str
    acknowledgment_timeout_minutes: int = 15


@dataclass
class RPMReviewInput:
    patient_id: str
    org_id: str
    lookback_hours: int = 24


if TEMPORAL_AVAILABLE:

    # ── Patient Onboarding ─────────────────────────────────────────────────

    @workflow.defn(name="PatientOnboardingWorkflow")
    class PatientOnboardingWorkflow:
        """Durable multi-step patient onboarding.

        Steps:
        1. Verify insurance
        2. Create patient record
        3. Assign care team
        4. Generate care plan
        5. Schedule initial encounter
        6. Send welcome message
        """

        def __init__(self) -> None:
            self._current_step: str = "initialized"
            self._completed_steps: list[str] = []

        @workflow.run
        async def run(self, input: PatientOnboardingInput) -> dict[str, Any]:
            common_ctx = {
                "patient_id": input.patient_id,
                "org_id": input.org_id,
                "insurance_info": input.insurance_info or {},
                "care_preferences": input.care_preferences or {},
            }
            retry = _DEFAULT_RETRY_POLICY

            # 1 — Verify insurance
            self._current_step = "verify_insurance"
            insurance_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="insurance_verification",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context=common_ctx,
                ),
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("verify_insurance")

            # 2 — Create patient record
            self._current_step = "create_patient_record"
            await workflow.execute_activity(
                update_patient_status_activity,
                UpdatePatientStatusInput(
                    patient_id=input.patient_id,
                    status_updates={
                        "onboarding_status": "in_progress",
                        "insurance_verified": insurance_result.status == "completed",
                    },
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("create_patient_record")

            # 3 — Assign care team
            self._current_step = "assign_care_team"
            care_team_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="task_orchestration",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={**common_ctx, "action": "assign_care_team"},
                ),
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("assign_care_team")

            # 4 — Generate care plan
            self._current_step = "generate_care_plan"
            care_plan_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="task_orchestration",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        **common_ctx,
                        "action": "generate_care_plan",
                        "care_team": care_team_result.result,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=3),
                retry_policy=retry,
            )
            self._completed_steps.append("generate_care_plan")

            # 5 — Schedule initial encounter
            self._current_step = "schedule_initial_encounter"
            encounter = await workflow.execute_activity(
                create_encounter_activity,
                CreateEncounterInput(
                    patient_id=input.patient_id,
                    encounter_type="initial_visit",
                    reason="New patient onboarding",
                    org_id=input.org_id,
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=retry,
            )
            self._completed_steps.append("schedule_initial_encounter")

            # 6 — Send welcome message
            self._current_step = "send_welcome_message"
            await workflow.execute_activity(
                send_notification_activity,
                NotificationInput(
                    provider_id=input.patient_id,
                    message=(
                        "Welcome to HealthOS! Your initial visit has been scheduled."
                    ),
                    channel="email",
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("send_welcome_message")

            self._current_step = "completed"
            return {
                "patient_id": input.patient_id,
                "status": "onboarding_complete",
                "insurance_status": insurance_result.status,
                "care_plan": care_plan_result.result,
                "encounter_id": encounter["encounter_id"],
                "steps_completed": list(self._completed_steps),
            }

        @workflow.query(name="current_step")
        def current_step(self) -> str:
            return self._current_step

        @workflow.query(name="completed_steps")
        def completed_steps(self) -> list[str]:
            return list(self._completed_steps)

    # ── Critical Alert Escalation ──────────────────────────────────────────

    @workflow.defn(name="CriticalAlertWorkflow")
    class CriticalAlertWorkflow:
        """Alert with timer-based escalation if the provider does not acknowledge.

        Steps:
        1. Create alert record
        2. Notify primary provider
        3. Wait for acknowledgment (signal) with timeout
        4. Escalate if unacknowledged
        5. Create follow-up task
        """

        def __init__(self) -> None:
            self._acknowledged: bool = False
            self._acknowledged_by: str | None = None
            self._current_step: str = "initialized"
            self._escalated: bool = False

        @workflow.signal(name="acknowledge_alert")
        async def acknowledge_alert(self, acknowledged_by: str) -> None:
            self._acknowledged = True
            self._acknowledged_by = acknowledged_by

        @workflow.run
        async def run(self, input: CriticalAlertInput) -> dict[str, Any]:
            retry = _DEFAULT_RETRY_POLICY

            # 1 — Create alert record
            self._current_step = "create_alert"
            alert_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="task_orchestration",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "create_alert",
                        "alert_id": input.alert_id,
                        "severity": input.severity,
                        "message": input.message,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )

            # 2 — Notify primary provider
            self._current_step = "notify_provider"
            await workflow.execute_activity(
                send_notification_activity,
                NotificationInput(
                    provider_id=input.provider_id,
                    message=f"[{input.severity.upper()}] {input.message}",
                    channel="push",
                ),
                start_to_close_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )

            # 3 — Wait for acknowledgment signal with timeout
            self._current_step = "awaiting_acknowledgment"
            timeout = timedelta(minutes=input.acknowledgment_timeout_minutes)
            try:
                await workflow.wait_condition(
                    lambda: self._acknowledged, timeout=timeout
                )
            except asyncio.TimeoutError:
                pass  # handled below

            # 4 — Escalate if not acknowledged
            if not self._acknowledged:
                self._current_step = "escalating"
                self._escalated = True

                # Notify secondary / on-call
                await workflow.execute_activity(
                    send_notification_activity,
                    NotificationInput(
                        provider_id="on_call",
                        message=(
                            f"ESCALATION: Alert {input.alert_id} for patient "
                            f"{input.patient_id} was not acknowledged within "
                            f"{input.acknowledgment_timeout_minutes} min. "
                            f"Original provider: {input.provider_id}."
                        ),
                        channel="sms",
                    ),
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry,
                )

                # Also send push notification as backup
                await workflow.execute_activity(
                    send_notification_activity,
                    NotificationInput(
                        provider_id="on_call",
                        message=(
                            f"ESCALATION: Unacknowledged {input.severity} alert "
                            f"{input.alert_id}"
                        ),
                        channel="push",
                    ),
                    start_to_close_timeout=timedelta(minutes=2),
                    retry_policy=retry,
                )

            # 5 — Create follow-up task
            self._current_step = "create_follow_up"
            follow_up = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="task_orchestration",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "create_task",
                        "task_type": "alert_follow_up",
                        "alert_id": input.alert_id,
                        "escalated": self._escalated,
                        "acknowledged_by": self._acknowledged_by,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=3),
                retry_policy=retry,
            )

            self._current_step = "completed"
            return {
                "alert_id": input.alert_id,
                "patient_id": input.patient_id,
                "acknowledged": self._acknowledged,
                "acknowledged_by": self._acknowledged_by,
                "escalated": self._escalated,
                "follow_up": follow_up.result,
            }

        @workflow.query(name="alert_status")
        def alert_status(self) -> dict[str, Any]:
            return {
                "current_step": self._current_step,
                "acknowledged": self._acknowledged,
                "acknowledged_by": self._acknowledged_by,
                "escalated": self._escalated,
            }

    # ── RPM Review (Scheduled) ─────────────────────────────────────────────

    @workflow.defn(name="RPMReviewWorkflow")
    class RPMReviewWorkflow:
        """Periodic RPM review cycle.

        Steps:
        1. Aggregate recent vitals
        2. Run anomaly detection agent
        3. Run risk scoring agent
        4. Generate clinical summary
        5. Create encounter if anomalies warrant it
        """

        def __init__(self) -> None:
            self._current_step: str = "initialized"
            self._completed_steps: list[str] = []
            self._encounter_created: bool = False

        @workflow.run
        async def run(self, input: RPMReviewInput) -> dict[str, Any]:
            retry = _DEFAULT_RETRY_POLICY

            # 1 — Aggregate recent vitals
            self._current_step = "aggregate_vitals"
            vitals_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="vital_normalization",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "aggregate",
                        "lookback_hours": input.lookback_hours,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("aggregate_vitals")

            # 2 — Run anomaly detection
            self._current_step = "anomaly_detection"
            anomaly_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="anomaly_detection",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "detect",
                        "vitals": vitals_result.result,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=3),
                retry_policy=retry,
            )
            self._completed_steps.append("anomaly_detection")

            # 3 — Run risk scoring
            self._current_step = "risk_scoring"
            risk_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="risk_scoring",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "score",
                        "vitals": vitals_result.result,
                        "anomalies": anomaly_result.result,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=10),
                heartbeat_timeout=timedelta(minutes=3),
                retry_policy=retry,
            )
            self._completed_steps.append("risk_scoring")

            # 4 — Generate clinical summary
            self._current_step = "generate_summary"
            summary_result = await workflow.execute_activity(
                run_agent_activity,
                AgentActivityInput(
                    agent_name="task_orchestration",
                    org_id=input.org_id,
                    patient_id=input.patient_id,
                    context={
                        "action": "generate_clinical_summary",
                        "vitals": vitals_result.result,
                        "anomalies": anomaly_result.result,
                        "risk": risk_result.result,
                    },
                ),
                start_to_close_timeout=timedelta(minutes=5),
                heartbeat_timeout=timedelta(minutes=2),
                retry_policy=retry,
            )
            self._completed_steps.append("generate_summary")

            # 5 — Create encounter if warranted
            encounter_result: dict[str, Any] | None = None
            anomalies_detected = bool(
                anomaly_result.result and anomaly_result.result.get("anomalies")
            )
            risk_elevated = bool(
                risk_result.result
                and risk_result.result.get("risk_level") in ("high", "critical")
            )

            if anomalies_detected or risk_elevated:
                self._current_step = "create_encounter"
                encounter_result = await workflow.execute_activity(
                    create_encounter_activity,
                    CreateEncounterInput(
                        patient_id=input.patient_id,
                        encounter_type="rpm_review",
                        reason=(
                            "Automated RPM review: anomalies detected"
                            if anomalies_detected
                            else "Automated RPM review: elevated risk"
                        ),
                        org_id=input.org_id,
                    ),
                    start_to_close_timeout=timedelta(minutes=3),
                    retry_policy=retry,
                )
                self._encounter_created = True
                self._completed_steps.append("create_encounter")

            self._current_step = "completed"
            return {
                "patient_id": input.patient_id,
                "vitals_status": vitals_result.status,
                "anomalies": anomaly_result.result,
                "risk": risk_result.result,
                "summary": summary_result.result,
                "encounter_created": self._encounter_created,
                "encounter": encounter_result,
                "steps_completed": list(self._completed_steps),
            }

        @workflow.query(name="review_status")
        def review_status(self) -> dict[str, Any]:
            return {
                "current_step": self._current_step,
                "completed_steps": list(self._completed_steps),
                "encounter_created": self._encounter_created,
            }


# ═══════════════════════════════════════════════════════════════════════════════
# WORKFLOW REGISTRY — maps string names to workflow classes
# ═══════════════════════════════════════════════════════════════════════════════

_WORKFLOW_REGISTRY: dict[str, Any] = {}
if TEMPORAL_AVAILABLE:
    _WORKFLOW_REGISTRY = {
        "PatientOnboardingWorkflow": PatientOnboardingWorkflow,
        "CriticalAlertWorkflow": CriticalAlertWorkflow,
        "RPMReviewWorkflow": RPMReviewWorkflow,
    }


# ═══════════════════════════════════════════════════════════════════════════════
# WORKER SETUP
# ═══════════════════════════════════════════════════════════════════════════════


async def create_temporal_worker(
    client: TemporalClient | None = None,
    task_queue: str = CLINICAL_TASK_QUEUE,
) -> Worker | None:  # type: ignore[return]
    """Create and return a Temporal ``Worker`` registered with all clinical
    workflows and activities.

    The caller is responsible for running the worker, e.g.::

        worker = await create_temporal_worker(client)
        if worker:
            await worker.run()
    """
    if not TEMPORAL_AVAILABLE:
        logger.error(
            "temporal.worker.sdk_missing — cannot create worker without temporalio"
        )
        return None

    if client is None:
        client = TemporalClient()

    if not client.is_connected:
        logger.error("temporal.worker.not_connected — connect the client first")
        return None

    raw_client = client._ensure_client()

    worker = Worker(
        raw_client,
        task_queue=task_queue,
        workflows=[
            PatientOnboardingWorkflow,
            CriticalAlertWorkflow,
            RPMReviewWorkflow,
        ],
        activities=[
            run_agent_activity,
            send_notification_activity,
            create_encounter_activity,
            update_patient_status_activity,
        ],
    )
    logger.info(
        "temporal.worker.created",
        extra={
            "task_queue": task_queue,
            "workflows": list(_WORKFLOW_REGISTRY.keys()),
            "activities": [
                "run_agent",
                "send_notification",
                "create_encounter",
                "update_patient_status",
            ],
        },
    )
    return worker


# ═══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL CONVENIENCE
# ═══════════════════════════════════════════════════════════════════════════════

# Singleton instance — mirrors the pattern used by workflow_engine.py
temporal_client = TemporalClient()
