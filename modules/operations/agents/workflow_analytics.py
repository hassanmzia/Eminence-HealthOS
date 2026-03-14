"""
Eminence HealthOS — Workflow Analytics Agent
Layer 5 (Measurement): Analyzes operational workflow performance, identifies
bottlenecks, tracks KPIs, and generates insights for process improvement.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from typing import Any

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router
from modules.operations.workflow_engine import (
    StepStatus,
    WorkflowDefinition,
    WorkflowStatus,
    workflow_engine,
)

logger = logging.getLogger("healthos.agent.workflow_analytics")


class WorkflowAnalyticsAgent(BaseAgent):
    """Analyzes workflow performance and generates operational insights."""

    name = "workflow_analytics"
    tier = AgentTier.MEASUREMENT
    version = "1.0.0"
    description = "Analyzes workflow performance, bottlenecks, and operational KPIs"
    min_confidence = 0.75

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "summary")

        if action == "summary":
            output = self._generate_summary(input_data)
        elif action == "bottleneck_analysis":
            output = self._analyze_bottlenecks(input_data)
        elif action == "kpi_report":
            output = self._generate_kpi_report(input_data)
        elif action == "trend_analysis":
            output = self._analyze_trends(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown analytics action: {action}",
                status=AgentStatus.FAILED,
            )

        # --- LLM: generate workflow insights ---
        try:
            result_data = output.result if hasattr(output, "result") else {}
            prompt = (
                "You are a healthcare operations analyst. "
                "Analyze the following workflow analytics data and provide concise, actionable "
                "insights about operational efficiency, key performance trends, bottlenecks, "
                "and prioritized recommendations for improvement.\n\n"
                f"Action: {action}\n"
                f"Analytics data: {json.dumps(result_data, indent=2, default=str)}"
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": prompt}],
                system=(
                    "You are a workflow analytics narrator for a healthcare operations platform. "
                    "Provide clear, data-driven insights that help operations managers quickly "
                    "understand performance patterns and make informed decisions. Prioritize "
                    "recommendations by potential impact."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            if isinstance(result_data, dict):
                result_data["workflow_insights"] = resp.content
        except Exception:
            logger.warning("LLM workflow_insights generation failed; continuing without it")

        return output

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_workflows(org_id: str | None = None) -> list[WorkflowDefinition]:
        """Return all workflows, optionally filtered by org_id."""
        wfs = list(workflow_engine._workflows.values())
        if org_id:
            wfs = [w for w in wfs if w.org_id == org_id]
        return wfs

    @staticmethod
    def _step_duration_hours(step) -> float | None:
        """Return duration in hours for a completed step, or None."""
        if step.started_at and step.completed_at:
            delta = (step.completed_at - step.started_at).total_seconds()
            return delta / 3600
        return None

    @staticmethod
    def _workflow_duration_hours(wf: WorkflowDefinition) -> float | None:
        """Return total workflow duration in hours if completed."""
        if wf.completed_at and wf.created_at:
            delta = (wf.completed_at - wf.created_at).total_seconds()
            return delta / 3600
        return None

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------

    def _generate_summary(self, input_data: AgentInput) -> AgentOutput:
        """Generate operations summary dashboard data from the workflow engine."""
        ctx = input_data.context
        period = ctx.get("period", "weekly")
        org_id = ctx.get("org_id")

        now = datetime.now(timezone.utc)
        workflows = self._get_workflows(org_id)

        # --- Workflow-level counts ---
        status_counts: dict[str, int] = defaultdict(int)
        completion_hours: list[float] = []
        for wf in workflows:
            status_counts[wf.status.value] += 1
            dur = self._workflow_duration_hours(wf)
            if dur is not None:
                completion_hours.append(dur)

        total_wf = len(workflows)
        completed_wf = status_counts.get("completed", 0)
        active_wf = status_counts.get("active", 0)
        failed_wf = status_counts.get("failed", 0)
        completion_rate = completed_wf / total_wf if total_wf else 0.0
        avg_completion_h = (
            sum(completion_hours) / len(completion_hours) if completion_hours else 0.0
        )

        # --- Step-level counts ---
        total_steps = 0
        steps_completed = 0
        steps_pending = 0
        steps_failed = 0
        step_durations: list[float] = []
        for wf in workflows:
            for step in wf.steps:
                total_steps += 1
                if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                    steps_completed += 1
                    dur = self._step_duration_hours(step)
                    if dur is not None:
                        step_durations.append(dur)
                elif step.status in (StepStatus.PENDING, StepStatus.READY, StepStatus.BLOCKED):
                    steps_pending += 1
                elif step.status == StepStatus.FAILED:
                    steps_failed += 1

        avg_step_h = (
            sum(step_durations) / len(step_durations) if step_durations else 0.0
        )

        # --- SLA violations ---
        sla_violations = (
            workflow_engine.check_sla_violations(org_id) if org_id else []
        )
        if not org_id:
            # Aggregate across all orgs
            seen_orgs: set[str] = set()
            for wf in workflows:
                seen_orgs.add(wf.org_id)
            for oid in seen_orgs:
                sla_violations.extend(workflow_engine.check_sla_violations(oid))

        sla_compliant_steps = total_steps - len(sla_violations) - steps_failed
        sla_compliance = sla_compliant_steps / total_steps if total_steps else 0.0

        # --- Per-agent-type step breakdowns ---
        pa_steps = [
            s for wf in workflows for s in wf.steps
            if s.agent_name == "prior_authorization"
        ]
        pa_submitted = len(pa_steps)
        pa_approved = sum(1 for s in pa_steps if s.status == StepStatus.COMPLETED)
        pa_denied = sum(1 for s in pa_steps if s.status == StepStatus.FAILED)
        pa_pending = pa_submitted - pa_approved - pa_denied
        pa_approval_rate = pa_approved / pa_submitted if pa_submitted else 0.0
        pa_durations = [self._step_duration_hours(s) for s in pa_steps if self._step_duration_hours(s) is not None]
        pa_avg_h = sum(pa_durations) / len(pa_durations) if pa_durations else 0.0

        ref_steps = [
            s for wf in workflows for s in wf.steps
            if s.agent_name == "referral_coordination"
        ]
        ref_total = len(ref_steps)
        ref_completed = sum(1 for s in ref_steps if s.status == StepStatus.COMPLETED)
        ref_pending = ref_total - ref_completed
        ref_rate = ref_completed / ref_total if ref_total else 0.0

        billing_steps = [
            s for wf in workflows for s in wf.steps
            if s.agent_name == "billing_readiness"
        ]
        bill_total = len(billing_steps)
        bill_accepted = sum(1 for s in billing_steps if s.status == StepStatus.COMPLETED)
        bill_denied = sum(1 for s in billing_steps if s.status == StepStatus.FAILED)
        bill_pending = bill_total - bill_accepted - bill_denied
        bill_acceptance_rate = bill_accepted / bill_total if bill_total else 0.0

        summary = {
            "period": period,
            "generated_at": now.isoformat(),
            "workflows": {
                "total_created": total_wf,
                "completed": completed_wf,
                "active": active_wf,
                "failed": failed_wf,
                "completion_rate": round(completion_rate, 3),
                "avg_completion_hours": round(avg_completion_h, 1),
            },
            "tasks": {
                "total_created": total_steps,
                "completed": steps_completed,
                "pending": steps_pending,
                "failed": steps_failed,
                "sla_violations": len(sla_violations),
                "sla_compliance": round(max(sla_compliance, 0.0), 3),
                "avg_completion_hours": round(avg_step_h, 1),
            },
            "prior_authorizations": {
                "submitted": pa_submitted,
                "approved": pa_approved,
                "denied": pa_denied,
                "pending": pa_pending,
                "approval_rate": round(pa_approval_rate, 3),
                "avg_turnaround_hours": round(pa_avg_h, 1),
            },
            "referrals": {
                "created": ref_total,
                "completed": ref_completed,
                "pending": ref_pending,
                "completion_rate": round(ref_rate, 3),
            },
            "billing": {
                "claims_submitted": bill_total,
                "claims_accepted": bill_accepted,
                "claims_denied": bill_denied,
                "claims_pending": bill_pending,
                "acceptance_rate": round(bill_acceptance_rate, 3),
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=summary,
            confidence=0.88,
            rationale=(
                f"Operations summary ({period}): "
                f"{summary['workflows']['completion_rate']:.1%} workflow completion, "
                f"{summary['tasks']['sla_compliance']:.1%} SLA compliance"
            ),
        )

    def _analyze_bottlenecks(self, input_data: AgentInput) -> AgentOutput:
        """Identify bottlenecks by analysing real step performance data."""
        ctx = input_data.context
        org_id = ctx.get("org_id")
        now = datetime.now(timezone.utc)
        workflows = self._get_workflows(org_id)

        # --- Collect per-step-name and per-agent metrics ---
        step_durations: dict[str, list[float]] = defaultdict(list)
        step_failure_counts: dict[str, int] = defaultdict(int)
        step_total_counts: dict[str, int] = defaultdict(int)
        agent_retries: dict[str, int] = defaultdict(int)
        agent_step_count: dict[str, int] = defaultdict(int)

        for wf in workflows:
            for step in wf.steps:
                step_total_counts[step.name] += 1
                agent_step_count[step.agent_name] += 1
                agent_retries[step.agent_name] += step.retry_count

                dur = self._step_duration_hours(step)
                if dur is not None:
                    step_durations[step.name].append(dur)

                if step.status == StepStatus.FAILED:
                    step_failure_counts[step.name] += 1

        # --- Steps with longest average duration ---
        avg_durations = {
            name: sum(durs) / len(durs)
            for name, durs in step_durations.items()
            if durs
        }
        slowest_steps = sorted(avg_durations.items(), key=lambda x: -x[1])[:5]

        # --- Steps with highest failure rate ---
        failure_rates = {
            name: step_failure_counts.get(name, 0) / total
            for name, total in step_total_counts.items()
            if total > 0
        }
        worst_failure = sorted(failure_rates.items(), key=lambda x: -x[1])[:5]

        # --- Agents with most retries ---
        retry_ranking = sorted(agent_retries.items(), key=lambda x: -x[1])[:5]

        # --- Dependency chain delays: steps blocked longest ---
        blocked_steps: list[dict[str, Any]] = []
        for wf in workflows:
            if wf.status != WorkflowStatus.ACTIVE:
                continue
            for step in wf.steps:
                if step.status in (StepStatus.PENDING, StepStatus.BLOCKED):
                    wait_hours = (now - wf.created_at).total_seconds() / 3600
                    blocked_steps.append({
                        "workflow_id": wf.workflow_id,
                        "step_name": step.name,
                        "waiting_hours": round(wait_hours, 1),
                        "depends_on": step.depends_on,
                    })
        blocked_steps.sort(key=lambda x: -x["waiting_hours"])
        top_blocked = blocked_steps[:5]

        # --- Build bottleneck records ---
        bottlenecks: list[dict[str, Any]] = []

        for name, avg_h in slowest_steps:
            sla = None
            for wf in workflows:
                for s in wf.steps:
                    if s.name == name:
                        sla = s.sla_hours
                        break
                if sla is not None:
                    break
            severity = "high" if (sla and avg_h > sla) else "medium"
            bottlenecks.append({
                "area": name,
                "issue": f"Average duration {avg_h:.1f}h" + (f" exceeds {sla}h SLA" if sla and avg_h > sla else ""),
                "severity": severity,
                "metric_type": "slow_step",
                "avg_duration_hours": round(avg_h, 1),
                "sla_hours": sla,
                "occurrences": len(step_durations.get(name, [])),
            })

        for name, rate in worst_failure:
            if rate <= 0:
                continue
            bottlenecks.append({
                "area": name,
                "issue": f"Failure rate {rate:.1%} ({step_failure_counts[name]}/{step_total_counts[name]})",
                "severity": "high" if rate > 0.2 else "medium",
                "metric_type": "high_failure_rate",
                "failure_rate": round(rate, 3),
                "total_failures": step_failure_counts[name],
            })

        for agent_name, retries in retry_ranking:
            if retries <= 0:
                continue
            bottlenecks.append({
                "area": agent_name,
                "issue": f"{retries} total retries across {agent_step_count[agent_name]} steps",
                "severity": "high" if retries > 5 else "medium" if retries > 2 else "low",
                "metric_type": "agent_retries",
                "total_retries": retries,
                "total_steps": agent_step_count[agent_name],
            })

        # Deduplicate by area+metric_type, sort by severity
        severity_order = {"high": 0, "medium": 1, "low": 2}
        bottlenecks.sort(key=lambda b: severity_order.get(b["severity"], 3))

        total_savings = sum(
            b.get("avg_duration_hours", 0) * b.get("occurrences", 0)
            for b in bottlenecks
            if b.get("metric_type") == "slow_step" and b.get("severity") == "high"
        )

        result = {
            "bottlenecks": bottlenecks,
            "total_identified": len(bottlenecks),
            "high_severity": sum(1 for b in bottlenecks if b["severity"] == "high"),
            "dependency_delays": top_blocked,
            "estimated_total_time_savings_hours": round(total_savings, 1),
            "analyzed_at": now.isoformat(),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.82,
            rationale=(
                f"Bottleneck analysis: {len(bottlenecks)} identified, "
                f"{round(total_savings, 1)}h potential time savings"
            ),
        )

    def _generate_kpi_report(self, input_data: AgentInput) -> AgentOutput:
        """Generate operational KPI report from real workflow data."""
        ctx = input_data.context
        period = ctx.get("period", "monthly")
        org_id = ctx.get("org_id")
        now = datetime.now(timezone.utc)
        workflows = self._get_workflows(org_id)

        # --- Efficiency metrics ---
        step_durations: list[float] = []
        wf_durations: list[float] = []
        total_steps = 0
        steps_no_retry = 0

        for wf in workflows:
            dur = self._workflow_duration_hours(wf)
            if dur is not None:
                wf_durations.append(dur)
            for step in wf.steps:
                total_steps += 1
                sd = self._step_duration_hours(step)
                if sd is not None:
                    step_durations.append(sd)
                if step.status == StepStatus.COMPLETED and step.retry_count == 0:
                    steps_no_retry += 1

        completed_steps = sum(
            1 for wf in workflows for s in wf.steps
            if s.status in (StepStatus.COMPLETED, StepStatus.SKIPPED)
        )

        avg_step_h = sum(step_durations) / len(step_durations) if step_durations else 0.0
        avg_wf_h = sum(wf_durations) / len(wf_durations) if wf_durations else 0.0
        first_pass_rate = steps_no_retry / completed_steps if completed_steps else 0.0

        # --- Quality metrics ---
        # SLA compliance
        sla_violation_count = 0
        if org_id:
            sla_violation_count = len(workflow_engine.check_sla_violations(org_id))
        else:
            seen_orgs: set[str] = {wf.org_id for wf in workflows}
            for oid in seen_orgs:
                sla_violation_count += len(workflow_engine.check_sla_violations(oid))
        sla_compliance = (total_steps - sla_violation_count) / total_steps if total_steps else 0.0

        # Prior auth approval rate
        pa_steps = [s for wf in workflows for s in wf.steps if s.agent_name == "prior_authorization"]
        pa_done = sum(1 for s in pa_steps if s.status in (StepStatus.COMPLETED, StepStatus.FAILED))
        pa_approved = sum(1 for s in pa_steps if s.status == StepStatus.COMPLETED)
        pa_approval_rate = pa_approved / pa_done if pa_done else 0.0

        # Insurance verification turnaround
        iv_steps = [s for wf in workflows for s in wf.steps if s.agent_name == "insurance_verification"]
        iv_durations = [self._step_duration_hours(s) for s in iv_steps if self._step_duration_hours(s) is not None]
        iv_avg_h = sum(iv_durations) / len(iv_durations) if iv_durations else 0.0

        # Referral completion rate
        ref_steps = [s for wf in workflows for s in wf.steps if s.agent_name == "referral_coordination"]
        ref_total = len(ref_steps)
        ref_completed = sum(1 for s in ref_steps if s.status == StepStatus.COMPLETED)
        ref_rate = ref_completed / ref_total if ref_total else 0.0

        # Billing claim acceptance rate
        bill_steps = [s for wf in workflows for s in wf.steps if s.agent_name == "billing_readiness"]
        bill_done = sum(1 for s in bill_steps if s.status in (StepStatus.COMPLETED, StepStatus.FAILED))
        bill_accepted = sum(1 for s in bill_steps if s.status == StepStatus.COMPLETED)
        bill_denied = sum(1 for s in bill_steps if s.status == StepStatus.FAILED)
        claim_acceptance = bill_accepted / bill_done if bill_done else 0.0
        denial_rate = bill_denied / bill_done if bill_done else 0.0

        # --- Avg time-to-completion per workflow type ---
        type_durations: dict[str, list[float]] = defaultdict(list)
        for wf in workflows:
            dur = self._workflow_duration_hours(wf)
            if dur is not None:
                type_durations[wf.workflow_type].append(dur)
        avg_by_type = {
            wtype: round(sum(ds) / len(ds), 1)
            for wtype, ds in type_durations.items()
        }

        # --- Volume metrics ---
        total_wf = len(workflows)

        kpis = {
            "period": period,
            "generated_at": now.isoformat(),
            "efficiency_metrics": {
                "avg_task_completion_time_hours": round(avg_step_h, 1),
                "avg_workflow_completion_time_hours": round(avg_wf_h, 1),
                "first_pass_resolution_rate": round(first_pass_rate, 3),
                "avg_completion_hours_by_type": avg_by_type,
            },
            "quality_metrics": {
                "sla_compliance_rate": round(max(sla_compliance, 0.0), 3),
                "claim_acceptance_rate": round(claim_acceptance, 3),
                "denial_rate": round(denial_rate, 3),
                "prior_auth_approval_rate": round(pa_approval_rate, 3),
                "referral_completion_rate": round(ref_rate, 3),
                "insurance_verification_avg_hours": round(iv_avg_h, 1),
            },
            "volume_metrics": {
                "total_workflows": total_wf,
                "total_steps": total_steps,
                "total_prior_auths": len(pa_steps),
                "total_referrals": ref_total,
                "total_billing_claims": len(bill_steps),
                "total_insurance_verifications": len(iv_steps),
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=kpis,
            confidence=0.85,
            rationale=(
                f"KPI report ({period}): "
                f"SLA {kpis['quality_metrics']['sla_compliance_rate']:.1%}, "
                f"prior-auth approval {kpis['quality_metrics']['prior_auth_approval_rate']:.1%}, "
                f"claim acceptance {kpis['quality_metrics']['claim_acceptance_rate']:.1%}"
            ),
        )

    def _analyze_trends(self, input_data: AgentInput) -> AgentOutput:
        """Analyze operational trends over time from real workflow data."""
        ctx = input_data.context
        org_id = ctx.get("org_id")
        lookback_days = ctx.get("lookback_days", 30)
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=lookback_days)
        workflows = self._get_workflows(org_id)

        # --- Bucket workflows by day ---
        daily_created: dict[str, int] = defaultdict(int)
        daily_completed: dict[str, int] = defaultdict(int)
        daily_failed: dict[str, int] = defaultdict(int)
        daily_step_failures: dict[str, int] = defaultdict(int)
        daily_steps_total: dict[str, int] = defaultdict(int)
        daily_sla_ok: dict[str, int] = defaultdict(int)
        daily_sla_total: dict[str, int] = defaultdict(int)

        for wf in workflows:
            if wf.created_at < cutoff:
                continue
            day_key = wf.created_at.strftime("%Y-%m-%d")
            daily_created[day_key] += 1
            if wf.status == WorkflowStatus.COMPLETED and wf.completed_at:
                comp_day = wf.completed_at.strftime("%Y-%m-%d")
                daily_completed[comp_day] += 1
            elif wf.status == WorkflowStatus.FAILED:
                daily_failed[day_key] += 1

            for step in wf.steps:
                daily_steps_total[day_key] += 1
                if step.status == StepStatus.FAILED:
                    daily_step_failures[day_key] += 1
                # SLA check for completed/in-progress steps
                if step.status in (StepStatus.COMPLETED, StepStatus.SKIPPED):
                    daily_sla_total[day_key] += 1
                    deadline = wf.created_at + timedelta(hours=step.sla_hours)
                    finished = step.completed_at or now
                    if finished <= deadline:
                        daily_sla_ok[day_key] += 1
                elif step.status in (StepStatus.READY, StepStatus.IN_PROGRESS):
                    daily_sla_total[day_key] += 1
                    deadline = wf.created_at + timedelta(hours=step.sla_hours)
                    if now <= deadline:
                        daily_sla_ok[day_key] += 1

        # --- Build daily time series ---
        all_days = sorted(
            set(daily_created.keys())
            | set(daily_completed.keys())
            | set(daily_failed.keys())
        )

        daily_series: list[dict[str, Any]] = []
        for day in all_days:
            sla_t = daily_sla_total.get(day, 0)
            sla_ok = daily_sla_ok.get(day, 0)
            step_t = daily_steps_total.get(day, 0)
            step_f = daily_step_failures.get(day, 0)
            daily_series.append({
                "date": day,
                "workflows_created": daily_created.get(day, 0),
                "workflows_completed": daily_completed.get(day, 0),
                "workflows_failed": daily_failed.get(day, 0),
                "sla_compliance": round(sla_ok / sla_t, 3) if sla_t else None,
                "step_failure_rate": round(step_f / step_t, 3) if step_t else None,
            })

        # --- Aggregate weekly buckets ---
        weekly_series: list[dict[str, Any]] = []
        week_buckets: dict[str, dict[str, Any]] = defaultdict(
            lambda: {"created": 0, "completed": 0, "failed": 0, "sla_ok": 0, "sla_total": 0}
        )
        for day in all_days:
            dt = datetime.strptime(day, "%Y-%m-%d")
            week_key = dt.strftime("%G-W%V")
            week_buckets[week_key]["created"] += daily_created.get(day, 0)
            week_buckets[week_key]["completed"] += daily_completed.get(day, 0)
            week_buckets[week_key]["failed"] += daily_failed.get(day, 0)
            week_buckets[week_key]["sla_ok"] += daily_sla_ok.get(day, 0)
            week_buckets[week_key]["sla_total"] += daily_sla_total.get(day, 0)

        for week_key in sorted(week_buckets.keys()):
            wb = week_buckets[week_key]
            weekly_series.append({
                "week": week_key,
                "workflows_created": wb["created"],
                "workflows_completed": wb["completed"],
                "workflows_failed": wb["failed"],
                "sla_compliance": round(wb["sla_ok"] / wb["sla_total"], 3) if wb["sla_total"] else None,
            })

        # --- Compute throughput ---
        num_days = max((now - cutoff).days, 1)
        total_completed = sum(daily_completed.values())
        throughput_per_day = round(total_completed / num_days, 2)

        # --- Auto-generated insights ---
        insights: list[str] = []

        if len(weekly_series) >= 2:
            last = weekly_series[-1]
            prev = weekly_series[-2]
            if last["sla_compliance"] is not None and prev["sla_compliance"] is not None:
                delta = last["sla_compliance"] - prev["sla_compliance"]
                direction = "improved" if delta > 0 else "declined"
                insights.append(
                    f"SLA compliance {direction} by {abs(delta):.1%} "
                    f"({prev['week']} -> {last['week']})"
                )
            if last["workflows_completed"] and prev["workflows_completed"]:
                pct_change = (last["workflows_completed"] - prev["workflows_completed"]) / prev["workflows_completed"]
                direction = "increased" if pct_change > 0 else "decreased"
                insights.append(
                    f"Weekly throughput {direction} {abs(pct_change):.1%} "
                    f"({prev['workflows_completed']} -> {last['workflows_completed']})"
                )

        total_wf_in_period = sum(daily_created.values())
        total_failed = sum(daily_failed.values())
        if total_wf_in_period:
            fail_pct = total_failed / total_wf_in_period
            insights.append(
                f"Overall failure rate: {fail_pct:.1%} "
                f"({total_failed}/{total_wf_in_period} workflows)"
            )

        insights.append(f"Average throughput: {throughput_per_day} workflows completed/day")

        trends = {
            "analyzed_at": now.isoformat(),
            "lookback_days": lookback_days,
            "daily_data": daily_series,
            "weekly_data": weekly_series,
            "throughput_per_day": throughput_per_day,
            "total_workflows_in_period": total_wf_in_period,
            "total_completed_in_period": total_completed,
            "insights": insights,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=trends,
            confidence=0.80,
            rationale=(
                f"Trend analysis ({lookback_days}d): {len(insights)} insights, "
                f"{throughput_per_day} workflows/day throughput"
            ),
        )
