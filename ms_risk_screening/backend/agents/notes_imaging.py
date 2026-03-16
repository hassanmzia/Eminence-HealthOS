"""Notes & Imaging agent -- extracts MS-relevant signals from clinical notes."""
import logging
from typing import Any, Dict, List

from .base import AgentOutput, BaseAgent, AgentRegistry

logger = logging.getLogger('agents')

# ---------------------------------------------------------------------------
# Phrase lists
# ---------------------------------------------------------------------------

MS_NOTE_PHRASES: List[str] = [
    "demyelinating",
    "periventricular lesions",
    "oligoclonal bands",
    "optic neuritis",
    "relapsing symptoms",
    "neurology referral",
    "MRI brain w/wo contrast",
]

NON_MS_NOTE_PHRASES: List[str] = [
    "tension headache",
    "vitamin deficiency",
    "stress-related",
    "poor sleep",
    "peripheral neuropathy",
    "viral illness",
    "benign positional vertigo",
]


class NotesImagingAgent(BaseAgent):
    """
    Scans a patient's clinical note text for MS-suggestive and
    non-MS-suggestive phrases.  Returns boolean flags and a short
    excerpt of the first matching MS phrase in context.
    """

    name = "notes_imaging"

    def execute(self, patient_data: Dict[str, Any]) -> AgentOutput:
        """
        Parameters
        ----------
        patient_data : dict
            Must contain 'patient_id' and 'note_text'.

        Returns
        -------
        AgentOutput with payload keys:
            note_ms_terms_flag    -- bool
            note_nonms_terms_flag -- bool
            note_excerpt          -- str (up to 200 chars around first MS hit)
            ms_terms_found        -- list[str]
            nonms_terms_found     -- list[str]
        """
        patient_id = patient_data.get('patient_id', 'UNKNOWN')
        note_text = str(patient_data.get('note_text', ''))
        note_lower = note_text.lower()

        # Search for MS-suggestive phrases
        ms_terms_found: List[str] = []
        first_ms_pos: int = -1
        for phrase in MS_NOTE_PHRASES:
            pos = note_lower.find(phrase.lower())
            if pos != -1:
                ms_terms_found.append(phrase)
                if first_ms_pos == -1 or pos < first_ms_pos:
                    first_ms_pos = pos

        # Search for non-MS phrases
        nonms_terms_found: List[str] = []
        for phrase in NON_MS_NOTE_PHRASES:
            if phrase.lower() in note_lower:
                nonms_terms_found.append(phrase)

        note_ms_terms_flag = len(ms_terms_found) > 0
        note_nonms_terms_flag = len(nonms_terms_found) > 0

        # Build excerpt around first MS match
        note_excerpt = ""
        if first_ms_pos != -1:
            start = max(0, first_ms_pos - 60)
            end = min(len(note_text), first_ms_pos + 140)
            note_excerpt = note_text[start:end].strip()
            if start > 0:
                note_excerpt = "..." + note_excerpt
            if end < len(note_text):
                note_excerpt = note_excerpt + "..."

        logger.info(
            f"NotesImagingAgent: {patient_id} | "
            f"ms_terms={len(ms_terms_found)} nonms_terms={len(nonms_terms_found)}"
        )

        payload = {
            'note_ms_terms_flag': note_ms_terms_flag,
            'note_nonms_terms_flag': note_nonms_terms_flag,
            'note_excerpt': note_excerpt,
            'ms_terms_found': ms_terms_found,
            'nonms_terms_found': nonms_terms_found,
        }

        return AgentOutput(
            agent=self.name,
            patient_id=patient_id,
            payload=payload,
        )


# Register singleton
notes_imaging_agent = NotesImagingAgent()
AgentRegistry.register(notes_imaging_agent)
