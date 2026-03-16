"""Safety & Governance agent -- pre-action safety checks."""
import logging
import re
from typing import Any, Dict, List

from .base import AgentOutput, BaseAgent, AgentRegistry

logger = logging.getLogger('agents')


class SafetyGovernanceAgent(BaseAgent):
    """
    Runs safety / governance checks before any autonomous action is taken.

    Flags
    -----
    PHI_DETECTED
        The clinical note appears to contain a patient name
        (heuristic: matches ``name:`` prefix).
    LOW_EVIDENCE_CASE
        The patient has fewer than 2 positive core symptoms.
    MINOR_PATIENT
        The patient's age is below 18.
    HIGH_RISK_LOW_EVIDENCE
        Contradictory situation: the risk score is >= 0.80 but the
        evidence base is thin (LOW_EVIDENCE also triggered).
    """

    name = "safety_governance"

    # Core symptom columns checked for the LOW_EVIDENCE gate
    SYMPTOM_COLS = [
        'optic_neuritis',
        'paresthesia',
        'weakness',
        'gait_instability',
        'vertigo',
        'fatigue',
        'bladder_issues',
        'cognitive_fog',
    ]

    # Simple regex for detecting an embedded name pattern in note text
    _PHI_RE = re.compile(r'\bname\s*:', re.IGNORECASE)

    def execute(
        self,
        patient_data: Dict[str, Any],
        risk_score: float,
    ) -> AgentOutput:
        """
        Parameters
        ----------
        patient_data : dict
            Full patient record dict (must include note_text, age, and
            the symptom flag columns).
        risk_score : float
            The phenotyping risk score for this patient.

        Returns
        -------
        AgentOutput with payload keys:
            flags      -- list[str]   safety flag codes
            flag_count -- int
        """
        patient_id = patient_data.get('patient_id', 'UNKNOWN')
        flags: List[str] = []

        # --- Check 1: PHI in clinical note ---
        note_text = str(patient_data.get('note_text', ''))
        if self._PHI_RE.search(note_text):
            flags.append('PHI_DETECTED')

        # --- Check 2: Low evidence (fewer than 2 symptoms) ---
        symptom_count = sum(
            1 for col in self.SYMPTOM_COLS
            if bool(patient_data.get(col, False))
        )
        low_evidence = symptom_count < 2
        if low_evidence:
            flags.append('LOW_EVIDENCE_CASE')

        # --- Check 3: Minor patient ---
        age = patient_data.get('age', None)
        if age is not None:
            try:
                if float(age) < 18:
                    flags.append('MINOR_PATIENT')
            except (ValueError, TypeError):
                pass

        # --- Check 4: High risk but low evidence (contradiction) ---
        if risk_score >= 0.80 and low_evidence:
            flags.append('HIGH_RISK_LOW_EVIDENCE')

        logger.info(
            f"SafetyGovernanceAgent: {patient_id} | "
            f"flags={flags} risk_score={risk_score:.3f}"
        )

        payload = {
            'flags': flags,
            'flag_count': len(flags),
        }

        return AgentOutput(
            agent=self.name,
            patient_id=patient_id,
            payload=payload,
        )


# Register singleton
safety_governance_agent = SafetyGovernanceAgent()
AgentRegistry.register(safety_governance_agent)
