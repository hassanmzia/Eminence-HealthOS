"""Phenotyping agents -- weighted scoring models for MS risk."""
import logging
from typing import Any, Dict, Tuple

from .base import AgentOutput, BaseAgent, AgentRegistry

logger = logging.getLogger('agents')


class PhenotypingAgent(BaseAgent):
    """
    V1 weighted scoring model.

    Computes a 0-1 risk score from symptom flags, MRI findings, and
    clinical-note terms, then subtracts look-alike condition penalties.
    """

    name = "phenotyping"

    # ---- Feature weights (sum to ~1.0 before penalties) ----
    FEATURE_WEIGHTS: Dict[str, float] = {
        'optic_neuritis': 0.22,
        'paresthesia': 0.14,
        'weakness': 0.13,
        'gait_instability': 0.10,
        'vertigo': 0.08,
        'fatigue': 0.06,
        'bladder_issues': 0.05,
        'cognitive_fog': 0.04,
        'mri_lesions': 0.18,
        'note_has_ms_terms': 0.12,
    }

    # ---- Look-alike condition penalties ----
    LOOKALIKE_PENALTIES: Dict[str, float] = {
        'migraine': -0.08,
        'b12_deficiency': -0.10,
        'anxiety': -0.05,
        'fibromyalgia': -0.07,
        'stroke_TIA': -0.12,
        'none': 0.0,
    }

    def score(self, patient_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Compute risk score and per-feature contribution dict.

        Parameters
        ----------
        patient_data : dict
            Must contain boolean/numeric keys matching FEATURE_WEIGHTS
            and a 'lookalike_condition' key.

        Returns
        -------
        (risk_score, feature_contributions)
        """
        contributions: Dict[str, float] = {}
        raw = 0.0

        for feature, weight in self.FEATURE_WEIGHTS.items():
            value = patient_data.get(feature, False)
            flag = bool(value) if not isinstance(value, (int, float)) else (value > 0)
            contrib = weight if flag else 0.0
            contributions[feature] = round(contrib, 4)
            raw += contrib

        # Apply look-alike penalty
        lookalike = patient_data.get('lookalike_condition', 'none')
        penalty = self.LOOKALIKE_PENALTIES.get(str(lookalike), 0.0)
        contributions['lookalike_penalty'] = round(penalty, 4)
        raw += penalty

        risk_score = max(0.0, min(1.0, round(raw, 4)))
        return risk_score, contributions

    def execute(self, patient_data: Dict[str, Any]) -> AgentOutput:
        patient_id = patient_data.get('patient_id', 'UNKNOWN')
        risk_score, contributions = self.score(patient_data)

        logger.info(f"PhenotypingAgent V1: {patient_id} -> score={risk_score:.3f}")

        return AgentOutput(
            agent=self.name,
            patient_id=patient_id,
            payload={
                'risk_score': risk_score,
                'feature_contributions': contributions,
                'model_version': 'v1',
            },
        )


class PhenotypingAgentV2(BaseAgent):
    """
    V2 weighted scoring model with extended feature set.

    Adds bonus signals from vitamin-D status, mono history,
    SmartForm neuro score, and PATHS-like functional score.
    """

    name = "phenotyping_v2"

    # ---- Base feature weights (same as V1) ----
    FEATURE_WEIGHTS: Dict[str, float] = {
        'optic_neuritis': 0.22,
        'paresthesia': 0.14,
        'weakness': 0.13,
        'gait_instability': 0.10,
        'vertigo': 0.08,
        'fatigue': 0.06,
        'bladder_issues': 0.05,
        'cognitive_fog': 0.04,
        'mri_lesions': 0.18,
        'note_has_ms_terms': 0.12,
    }

    # ---- Look-alike condition penalties ----
    LOOKALIKE_PENALTIES: Dict[str, float] = {
        'migraine': -0.08,
        'b12_deficiency': -0.10,
        'anxiety': -0.05,
        'fibromyalgia': -0.07,
        'stroke_TIA': -0.12,
        'none': 0.0,
    }

    # ---- V2 bonus parameters ----
    VITAMIN_D_DEFICIENT_BONUS = 0.06
    INFECTIOUS_MONO_HISTORY_BONUS = 0.05
    SMARTFORM_NEURO_PER_POINT = 0.02
    PATHS_LIKE_FUNCTION_LOW_THRESHOLD = 70
    PATHS_LIKE_FUNCTION_LOW_BONUS = 0.04

    def score(self, patient_data: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
        """
        Compute V2 risk score with extended features.

        Returns
        -------
        (risk_score, feature_contributions)
        """
        contributions: Dict[str, float] = {}
        raw = 0.0

        # ---- Base features ----
        for feature, weight in self.FEATURE_WEIGHTS.items():
            value = patient_data.get(feature, False)
            flag = bool(value) if not isinstance(value, (int, float)) else (value > 0)
            contrib = weight if flag else 0.0
            contributions[feature] = round(contrib, 4)
            raw += contrib

        # ---- Look-alike penalty ----
        lookalike = patient_data.get('lookalike_condition', 'none')
        penalty = self.LOOKALIKE_PENALTIES.get(str(lookalike), 0.0)
        contributions['lookalike_penalty'] = round(penalty, 4)
        raw += penalty

        # ---- V2 extended signals ----

        # Vitamin D deficiency bonus
        vitamin_d_deficient = bool(patient_data.get('vitamin_d_deficient', False))
        vd_bonus = self.VITAMIN_D_DEFICIENT_BONUS if vitamin_d_deficient else 0.0
        contributions['vitamin_d_deficient'] = round(vd_bonus, 4)
        raw += vd_bonus

        # Infectious mononucleosis history bonus
        mono_history = bool(patient_data.get('infectious_mono_history', False))
        mono_bonus = self.INFECTIOUS_MONO_HISTORY_BONUS if mono_history else 0.0
        contributions['infectious_mono_history'] = round(mono_bonus, 4)
        raw += mono_bonus

        # SmartForm neuro score (per-point bonus)
        smartform_neuro = int(patient_data.get('smartform_neuro', 0))
        sf_bonus = smartform_neuro * self.SMARTFORM_NEURO_PER_POINT
        contributions['smartform_neuro'] = round(sf_bonus, 4)
        raw += sf_bonus

        # PATHS-like functional score bonus (low score = higher risk)
        paths_like_function = patient_data.get('paths_like_function', None)
        if paths_like_function is not None:
            try:
                paths_val = float(paths_like_function)
                paths_bonus = (
                    self.PATHS_LIKE_FUNCTION_LOW_BONUS
                    if paths_val < self.PATHS_LIKE_FUNCTION_LOW_THRESHOLD
                    else 0.0
                )
            except (ValueError, TypeError):
                paths_bonus = 0.0
        else:
            paths_bonus = 0.0
        contributions['paths_like_function_low'] = round(paths_bonus, 4)
        raw += paths_bonus

        risk_score = max(0.0, min(1.0, round(raw, 4)))
        return risk_score, contributions

    def execute(self, patient_data: Dict[str, Any]) -> AgentOutput:
        patient_id = patient_data.get('patient_id', 'UNKNOWN')
        risk_score, contributions = self.score(patient_data)

        logger.info(f"PhenotypingAgentV2: {patient_id} -> score={risk_score:.3f}")

        return AgentOutput(
            agent=self.name,
            patient_id=patient_id,
            payload={
                'risk_score': risk_score,
                'feature_contributions': contributions,
                'model_version': 'v2',
            },
        )


# Register singletons
phenotyping_agent = PhenotypingAgent()
AgentRegistry.register(phenotyping_agent)

phenotyping_agent_v2 = PhenotypingAgentV2()
AgentRegistry.register(phenotyping_agent_v2)
