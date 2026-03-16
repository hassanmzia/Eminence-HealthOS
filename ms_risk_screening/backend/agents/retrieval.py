"""Retrieval agent -- identifies candidate patients for MS screening."""
import logging
from typing import Any, Dict, List

import pandas as pd

from .base import AgentOutput, BaseAgent, AgentRegistry

logger = logging.getLogger('agents')


class RetrievalAgent(BaseAgent):
    """
    Scans the full patient population and returns a set of candidate
    patient IDs that meet the minimum evidence bar for further
    phenotyping.

    Inclusion criteria (all must be true):
        1. mri_lesions == True
        2. note_has_ms_terms == True
        3. At least 2 of the core symptom columns are True
        4. visit_count >= 6
    """

    name = "retrieval"

    # Core symptom columns used for the >=2-symptom gate
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

    def execute(self, patients_df: pd.DataFrame) -> AgentOutput:
        """
        Parameters
        ----------
        patients_df : pd.DataFrame
            DataFrame with at least the columns: patient_id, mri_lesions,
            note_has_ms_terms, visit_count, and the SYMPTOM_COLS above.

        Returns
        -------
        AgentOutput with payload containing candidate_ids list and counts.
        """
        df = patients_df.copy()

        # --- Gate 1: MRI lesions ---
        mask_mri = df['mri_lesions'].astype(bool)

        # --- Gate 2: Clinical note contains MS-related terms ---
        mask_notes = df['note_has_ms_terms'].astype(bool)

        # --- Gate 3: At least 2 core symptoms ---
        available_symptoms = [c for c in self.SYMPTOM_COLS if c in df.columns]
        symptom_count = df[available_symptoms].astype(bool).sum(axis=1)
        mask_symptoms = symptom_count >= 2

        # --- Gate 4: Sufficient visit history ---
        mask_visits = df['visit_count'] >= 6

        # Combine all gates
        candidate_mask = mask_mri & mask_notes & mask_symptoms & mask_visits
        candidate_ids = df.loc[candidate_mask, 'patient_id'].tolist()

        logger.info(
            f"RetrievalAgent: {len(candidate_ids)} candidates out of "
            f"{len(df)} patients passed all gates."
        )

        payload = {
            'candidate_ids': candidate_ids,
            'total_patients': len(df),
            'candidates_count': len(candidate_ids),
            'gate_counts': {
                'mri_lesions': int(mask_mri.sum()),
                'note_has_ms_terms': int(mask_notes.sum()),
                'symptoms_gte_2': int(mask_symptoms.sum()),
                'visits_gte_6': int(mask_visits.sum()),
            },
        }

        return AgentOutput(
            agent=self.name,
            patient_id='ALL',
            payload=payload,
        )


# Register singleton
retrieval_agent = RetrievalAgent()
AgentRegistry.register(retrieval_agent)
