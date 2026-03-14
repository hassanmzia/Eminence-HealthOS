"""
Care Plan Generator Agent — Tier 4 (Intervention).

Generates AI-assisted care plans based on patient risk scores,
conditions, and agent pipeline outputs. Uses LLM for personalized
plan generation with rule-based fallback. Requires HITL approval.
"""

import json
import logging
from datetime import datetime, timezone

from healthos_platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)
from healthos_platform.ml.llm.router import LLMRequest, llm_router

logger = logging.getLogger("healthos.agent.care_plan_generator")

CARE_PLAN_SYSTEM_PROMPT = """\
You are a clinical decision-support assistant specializing in remote patient \
monitoring care plans. You generate evidence-based, individualized care plans \
that a clinician will review before activation.

You MUST respond with valid JSON only — no markdown fences, no commentary \
outside the JSON object.

The JSON schema you must follow:

{
  "goals": [
    {
      "description": "<specific, measurable clinical goal>",
      "priority": "high" | "medium" | "low",
      "target_date_offset_days": <integer days from today>
    }
  ],
  "activities": [
    {
      "type": "monitoring" | "consultation" | "education" | "medication" | "lifestyle",
      "description": "<actionable intervention>",
      "frequency": "<e.g. daily, twice_daily, weekly, q4h>"
    }
  ],
  "monitoring": {
    "vitals": "<frequency, e.g. q4h, q8h, daily, weekly>",
    "labs": "<frequency, e.g. daily, twice_weekly, weekly, monthly>",
    "provider_review": "<frequency>"
  },
  "review_interval_days": <integer>
}

Guidelines:
- Tailor goals and interventions to the patient's specific conditions, risk \
level, active alerts, and current medications.
- Higher-risk patients need more frequent monitoring and shorter review cycles.
- Include at least one goal per active condition when clinically appropriate.
- Always include a general monitoring-adherence goal.
- Set realistic target date offsets (days from today).
- Keep descriptions concise and clinically precise.
"""


class CarePlanGeneratorAgent(HealthOSAgent):
    """Generates structured care plans from clinical data and agent outputs."""

    def __init__(self):
        super().__init__(
            name="care_plan_generator",
            tier=AgentTier.INTERVENTION,
            description="Generates AI-assisted care plans with goals and activities",
            version="0.2.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.CARE_PLAN_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        prior_outputs = agent_input.context.get("prior_outputs", [])

        # Extract risk information from prior agents
        risk_data = {}
        alerts = []
        for output in prior_outputs:
            if isinstance(output, dict):
                if output.get("agent") == "risk_scorer":
                    risk_data = output.get("data", {})
                elif output.get("decision", "").endswith("_alert"):
                    alerts.append(output)

        risk_level = risk_data.get("risk_level", data.get("risk_level", "UNKNOWN"))
        conditions = data.get("conditions", [])
        medications = data.get("medications", [])

        # Attempt LLM-based care plan generation; fall back to rules on failure.
        care_plan = await self._generate_care_plan_via_llm(
            risk_level, conditions, alerts, medications,
        )

        if care_plan is None:
            logger.warning("LLM care-plan generation failed — using rule-based fallback")
            care_plan = self._generate_care_plan_rules(risk_level, conditions, alerts)

        # Stamp metadata onto the plan
        care_plan.update({
            "status": "draft",
            "intent": "plan",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "risk_level": risk_level,
        })

        goals = care_plan.get("goals", [])

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision="care_plan_generated",
            rationale=(
                f"Generated care plan for {risk_level} risk patient with "
                f"{len(conditions)} conditions and {len(goals)} goals"
            ),
            confidence=0.75,
            data=care_plan,
            feature_contributions=[
                {"feature": "risk_level", "contribution": 0.4, "value": risk_level},
                {"feature": "conditions", "contribution": 0.3, "value": len(conditions)},
                {"feature": "active_alerts", "contribution": 0.2, "value": len(alerts)},
                {"feature": "prior_agents", "contribution": 0.1, "value": len(prior_outputs)},
            ],
            requires_hitl=True,  # Care plans always require clinician approval
            alternatives=[
                {"option": "conservative", "description": "Minimal intervention with close monitoring"},
                {"option": "aggressive", "description": "Intensive intervention with frequent follow-up"},
            ],
        )

    # ------------------------------------------------------------------
    # LLM-based generation
    # ------------------------------------------------------------------

    async def _generate_care_plan_via_llm(
        self,
        risk_level: str,
        conditions: list,
        alerts: list,
        medications: list,
    ) -> dict | None:
        """Call the LLM to produce a personalized care plan.

        Returns the parsed plan dict, or ``None`` if the call fails or the
        response cannot be parsed as valid JSON.
        """
        prompt = self._build_prompt(risk_level, conditions, alerts, medications)

        try:
            response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": prompt}],
                    system=CARE_PLAN_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=4096,
                )
            )

            plan = json.loads(response.content)

            # Basic structural validation
            if not isinstance(plan, dict):
                logger.error("LLM returned non-dict care plan")
                return None
            if "goals" not in plan or "activities" not in plan:
                logger.error("LLM care plan missing required keys (goals/activities)")
                return None

            return plan

        except json.JSONDecodeError:
            logger.exception("Failed to parse LLM care-plan response as JSON")
            return None
        except Exception:
            logger.exception("LLM care-plan generation encountered an error")
            return None

    @staticmethod
    def _build_prompt(
        risk_level: str,
        conditions: list,
        alerts: list,
        medications: list,
    ) -> str:
        alert_summaries = []
        for a in alerts:
            decision = a.get("decision", "unknown_alert")
            rationale = a.get("rationale", "")
            alert_summaries.append(f"- {decision}: {rationale}")

        sections = [
            f"Risk level: {risk_level}",
            f"Active conditions: {', '.join(str(c) for c in conditions) if conditions else 'None reported'}",
            f"Current medications: {', '.join(str(m) for m in medications) if medications else 'None reported'}",
        ]

        if alert_summaries:
            sections.append("Recent alerts:\n" + "\n".join(alert_summaries))
        else:
            sections.append("Recent alerts: None")

        patient_summary = "\n".join(sections)

        return (
            "Generate a personalized care plan for the following patient.\n\n"
            f"{patient_summary}\n\n"
            "Produce the care plan as a single JSON object matching the schema "
            "described in your system instructions."
        )

    # ------------------------------------------------------------------
    # Rule-based fallback (original logic)
    # ------------------------------------------------------------------

    def _generate_care_plan_rules(
        self, risk_level: str, conditions: list, alerts: list,
    ) -> dict:
        """Deterministic rule-based care plan used when the LLM is unavailable."""
        return {
            "goals": self._generate_goals(risk_level, conditions, alerts),
            "activities": self._generate_activities(risk_level, conditions, alerts),
            "monitoring": self._generate_monitoring_plan(risk_level),
            "review_interval_days": self._review_interval(risk_level),
        }

    def _generate_goals(self, risk_level: str, conditions: list, alerts: list) -> list:
        goals = []

        if risk_level in ("HIGH", "CRITICAL"):
            goals.append({
                "description": "Stabilize clinical status within 24-48 hours",
                "priority": "high",
                "target_date_offset_days": 2,
            })

        if any("diabetes" in str(c).lower() for c in conditions):
            goals.append({
                "description": "Achieve HbA1c < 7.0% within 3 months",
                "priority": "medium",
                "target_date_offset_days": 90,
            })

        if any("hypertension" in str(c).lower() for c in conditions):
            goals.append({
                "description": "Maintain blood pressure < 140/90 mmHg",
                "priority": "medium",
                "target_date_offset_days": 30,
            })

        # Default monitoring goal
        goals.append({
            "description": "Complete all scheduled vital sign monitoring",
            "priority": "medium",
            "target_date_offset_days": 7,
        })

        return goals

    def _generate_activities(self, risk_level: str, conditions: list, alerts: list) -> list:
        activities = []

        activities.append({
            "type": "monitoring",
            "description": "Daily vital signs collection",
            "frequency": "daily" if risk_level in ("HIGH", "CRITICAL") else "weekly",
        })

        if risk_level in ("HIGH", "CRITICAL"):
            activities.append({
                "type": "consultation",
                "description": "Provider review of clinical status",
                "frequency": "daily",
            })

        activities.append({
            "type": "education",
            "description": "Patient education on condition management",
            "frequency": "weekly",
        })

        if any("diabetes" in str(c).lower() for c in conditions):
            activities.append({
                "type": "monitoring",
                "description": "Blood glucose monitoring",
                "frequency": "twice_daily" if risk_level == "CRITICAL" else "daily",
            })

        return activities

    def _generate_monitoring_plan(self, risk_level: str) -> dict:
        freq_map = {
            "CRITICAL": {"vitals": "q4h", "labs": "daily", "provider_review": "q12h"},
            "HIGH": {"vitals": "q8h", "labs": "twice_weekly", "provider_review": "daily"},
            "MEDIUM": {"vitals": "daily", "labs": "weekly", "provider_review": "twice_weekly"},
            "LOW": {"vitals": "weekly", "labs": "monthly", "provider_review": "monthly"},
        }
        return freq_map.get(risk_level, freq_map["MEDIUM"])

    def _review_interval(self, risk_level: str) -> int:
        return {"CRITICAL": 1, "HIGH": 3, "MEDIUM": 7, "LOW": 14}.get(risk_level, 7)
