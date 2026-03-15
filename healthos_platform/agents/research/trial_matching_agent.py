"""
Eminence HealthOS — Trial Matching Agent
Matches patients to eligible clinical trials by querying ClinicalTrials.gov
and evaluating eligibility criteria against patient data.
"""

from __future__ import annotations

from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import AgentInput, AgentOutput, AgentTier

logger = structlog.get_logger()

CLINICALTRIALS_API = "https://clinicaltrials.gov/api/v2/studies"


class TrialMatchingAgent(BaseAgent):
    """
    Matches patients to clinical trials using ClinicalTrials.gov API.
    Evaluates eligibility criteria and scores match quality.
    """

    name = "trial_matching_agent"
    tier = AgentTier.INTERPRETATION
    version = "1.0.0"
    description = "Clinical trial matching via ClinicalTrials.gov API"
    min_confidence = 0.60

    async def process(self, input_data: AgentInput) -> AgentOutput:
        context = input_data.context or {}
        conditions = context.get("conditions", [])
        demographics = context.get("demographics", {})
        medications = context.get("medications", [])
        location = context.get("location", {})

        if not conditions:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"trials": [], "match_count": 0},
                confidence=0.30,
                rationale="No conditions provided for trial matching",
            )

        # Search for trials
        trials = await self._search_trials(conditions, location)

        # Score eligibility
        scored_trials = self._score_eligibility(trials, demographics, medications, conditions)

        # Filter eligible trials
        eligible = [t for t in scored_trials if t["eligibility_score"] >= 0.5]
        eligible.sort(key=lambda t: t["eligibility_score"], reverse=True)

        return self.build_output(
            trace_id=input_data.trace_id,
            result={
                "trials": eligible[:10],  # Top 10 matches
                "match_count": len(eligible),
                "total_searched": len(trials),
                "conditions_searched": [c.get("display", "") for c in conditions],
            },
            confidence=0.80 if eligible else 0.40,
            rationale=(
                f"Found {len(eligible)} eligible trials out of "
                f"{len(trials)} searched for {len(conditions)} condition(s)"
            ),
        )

    async def _search_trials(
        self, conditions: list[dict], location: dict
    ) -> list[dict[str, Any]]:
        """Search ClinicalTrials.gov for relevant studies."""
        try:
            import httpx

            search_terms = [c.get("display", "") for c in conditions if c.get("display")]
            query = " OR ".join(search_terms[:3])

            params: dict[str, Any] = {
                "query.cond": query,
                "filter.overallStatus": "RECRUITING",
                "pageSize": 20,
                "format": "json",
            }

            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.get(CLINICALTRIALS_API, params=params)
                resp.raise_for_status()
                data = resp.json()

            studies = data.get("studies", [])
            trials = []

            for study in studies:
                protocol = study.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                eligibility_module = protocol.get("eligibilityModule", {})
                desc_module = protocol.get("descriptionModule", {})

                trials.append({
                    "nct_id": id_module.get("nctId", ""),
                    "title": id_module.get("briefTitle", ""),
                    "status": status_module.get("overallStatus", ""),
                    "phase": ", ".join(protocol.get("designModule", {}).get("phases", [])),
                    "description": desc_module.get("briefSummary", ""),
                    "eligibility_criteria": eligibility_module.get("eligibilityCriteria", ""),
                    "min_age": eligibility_module.get("minimumAge", ""),
                    "max_age": eligibility_module.get("maximumAge", ""),
                    "sex": eligibility_module.get("sex", "ALL"),
                    "url": f"https://clinicaltrials.gov/study/{id_module.get('nctId', '')}",
                })

            return trials

        except Exception as e:
            logger.warning("trial_matching.search_failed", error=str(e))
            return []

    def _score_eligibility(
        self,
        trials: list[dict],
        demographics: dict,
        medications: list[dict],
        conditions: list[dict],
    ) -> list[dict[str, Any]]:
        """Score patient eligibility for each trial."""
        patient_age = demographics.get("age", 0)
        patient_sex = demographics.get("gender", "").upper()

        for trial in trials:
            score = 0.5  # Base score

            # Age eligibility
            min_age = self._parse_age(trial.get("min_age", ""))
            max_age = self._parse_age(trial.get("max_age", ""))

            if min_age and patient_age and patient_age >= min_age:
                score += 0.15
            elif min_age and patient_age and patient_age < min_age:
                score -= 0.30

            if max_age and patient_age and patient_age <= max_age:
                score += 0.10
            elif max_age and patient_age and patient_age > max_age:
                score -= 0.30

            # Sex eligibility
            trial_sex = trial.get("sex", "ALL").upper()
            if trial_sex == "ALL" or trial_sex == patient_sex:
                score += 0.10

            # Condition match
            condition_names = {c.get("display", "").lower() for c in conditions}
            title_lower = trial.get("title", "").lower()
            if any(cn in title_lower for cn in condition_names if cn):
                score += 0.15

            trial["eligibility_score"] = round(min(max(score, 0.0), 1.0), 2)

        return trials

    @staticmethod
    def _parse_age(age_str: str) -> int | None:
        """Parse age string like '18 Years' to integer."""
        if not age_str:
            return None
        try:
            return int(age_str.split()[0])
        except (ValueError, IndexError):
            return None
