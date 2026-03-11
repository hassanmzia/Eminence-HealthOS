"""
Medication Safety Agent — Tier 2 (Diagnostic).

Checks for drug-drug interactions, contraindications, dosage issues,
and duplicate therapies. Critical safety gate in the clinical workflow.
"""

import logging
from platform.agents.base import (
    AgentCapability,
    AgentInput,
    AgentOutput,
    AgentTier,
    HealthOSAgent,
)

logger = logging.getLogger("healthos.agent.medication_checker")

# Simplified interaction database (production would use full RxNorm/DrugBank)
KNOWN_INTERACTIONS = {
    ("warfarin", "aspirin"): {
        "severity": "HIGH",
        "description": "Increased bleeding risk with concurrent anticoagulant and antiplatelet therapy",
        "recommendation": "Monitor INR closely, consider alternative",
    },
    ("metformin", "contrast_dye"): {
        "severity": "HIGH",
        "description": "Risk of lactic acidosis with iodinated contrast",
        "recommendation": "Hold metformin 48h before and after contrast administration",
    },
    ("lisinopril", "potassium"): {
        "severity": "MEDIUM",
        "description": "ACE inhibitor + potassium supplement may cause hyperkalemia",
        "recommendation": "Monitor serum potassium levels",
    },
    ("simvastatin", "amiodarone"): {
        "severity": "HIGH",
        "description": "Increased risk of rhabdomyolysis",
        "recommendation": "Limit simvastatin to 20mg/day or switch statin",
    },
    ("ssri", "maoi"): {
        "severity": "CRITICAL",
        "description": "Risk of serotonin syndrome — potentially fatal",
        "recommendation": "Contraindicated combination — do not co-prescribe",
    },
}

DRUG_CLASSES = {
    "warfarin": ["anticoagulant"], "aspirin": ["antiplatelet", "nsaid"],
    "metformin": ["antidiabetic"], "lisinopril": ["ace_inhibitor"],
    "simvastatin": ["statin"], "amiodarone": ["antiarrhythmic"],
    "fluoxetine": ["ssri"], "sertraline": ["ssri"],
    "phenelzine": ["maoi"], "ibuprofen": ["nsaid"],
}


class MedicationCheckerAgent(HealthOSAgent):
    """Checks medication safety — interactions, contraindications, duplicates."""

    def __init__(self):
        super().__init__(
            name="medication_checker",
            tier=AgentTier.DIAGNOSTIC,
            description="Checks drug interactions, contraindications, and medication safety",
            version="0.1.0",
        )

    @property
    def capabilities(self) -> list[AgentCapability]:
        return [AgentCapability.DRUG_INTERACTION, AgentCapability.ALERT_GENERATION]

    async def process(self, agent_input: AgentInput) -> AgentOutput:
        data = agent_input.data
        new_medication = data.get("medication", "").lower()
        current_medications = [m.lower() for m in data.get("current_medications", [])]

        if not new_medication:
            return AgentOutput(
                agent_name=self.name,
                agent_tier=self.tier.value,
                decision="no_medication",
                rationale="No medication specified for checking",
                confidence=1.0,
            )

        interactions = []
        duplicates = []
        max_severity = "LOW"

        # Check interactions
        for current in current_medications:
            interaction = self._check_interaction(new_medication, current)
            if interaction:
                interactions.append(interaction)
                if self._severity_rank(interaction["severity"]) > self._severity_rank(max_severity):
                    max_severity = interaction["severity"]

        # Check duplicate therapy
        new_classes = self._get_drug_classes(new_medication)
        for current in current_medications:
            current_classes = self._get_drug_classes(current)
            overlap = set(new_classes) & set(current_classes)
            if overlap and new_medication != current:
                duplicates.append({
                    "drug": current,
                    "shared_classes": list(overlap),
                })

        # Build decision
        if interactions or duplicates:
            issues = []
            if interactions:
                issues.append(f"{len(interactions)} interaction(s)")
            if duplicates:
                issues.append(f"{len(duplicates)} duplicate therapy(ies)")

            decision = "safety_concern"
            rationale = f"Medication safety check for {new_medication}: {', '.join(issues)} detected"
            requires_hitl = max_severity in ("HIGH", "CRITICAL")
        else:
            decision = "safe"
            rationale = f"No interactions or duplicates found for {new_medication}"
            requires_hitl = False

        return AgentOutput(
            agent_name=self.name,
            agent_tier=self.tier.value,
            decision=decision,
            rationale=rationale,
            confidence=0.85 if interactions else 0.90,
            data={
                "medication": new_medication,
                "interactions": interactions,
                "duplicates": duplicates,
                "max_severity": max_severity,
            },
            feature_contributions=[
                {"feature": "drug_interactions", "contribution": 0.5, "value": len(interactions)},
                {"feature": "duplicate_therapy", "contribution": 0.3, "value": len(duplicates)},
                {"feature": "medication_classes", "contribution": 0.2, "value": new_classes},
            ],
            requires_hitl=requires_hitl,
            safety_flags=[f"interaction_{i['severity'].lower()}" for i in interactions],
            risk_level=max_severity.lower(),
        )

    def _check_interaction(self, drug_a: str, drug_b: str) -> dict | None:
        # Direct match
        key = tuple(sorted([drug_a, drug_b]))
        if key in KNOWN_INTERACTIONS:
            return {**KNOWN_INTERACTIONS[key], "drugs": list(key)}

        # Class-based match
        classes_a = self._get_drug_classes(drug_a)
        classes_b = self._get_drug_classes(drug_b)
        for ca in classes_a:
            for cb in classes_b:
                key = tuple(sorted([ca, cb]))
                if key in KNOWN_INTERACTIONS:
                    return {
                        **KNOWN_INTERACTIONS[key],
                        "drugs": [drug_a, drug_b],
                        "via_classes": list(key),
                    }
        return None

    def _get_drug_classes(self, drug: str) -> list[str]:
        return DRUG_CLASSES.get(drug, [])

    def _severity_rank(self, severity: str) -> int:
        return {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}.get(severity, 0)
