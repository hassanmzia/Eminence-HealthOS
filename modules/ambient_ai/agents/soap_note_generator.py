"""
Eminence HealthOS — SOAP Note Generator Agent (#43)
Layer 3 (Decisioning): Generates structured clinical SOAP notes (Subjective,
Objective, Assessment, Plan) from diarized transcripts.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

import structlog

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = structlog.get_logger()

# SOAP section templates
SOAP_SECTIONS = ["subjective", "objective", "assessment", "plan"]

# ── System Prompts ───────────────────────────────────────────────────────────

SOAP_SYSTEM_PROMPT = """\
You are a clinical documentation specialist AI. You generate structured SOAP \
notes from clinical encounter transcripts. Follow these rules strictly:

1. Use standard medical terminology and accepted abbreviations.
2. Be concise but thorough — do not fabricate information not present in the transcript.
3. If information for a section is missing from the transcript, state "Not documented" \
rather than inventing details.
4. For the Assessment, list differential diagnoses with ICD-10 codes when inferable.
5. For the Plan, categorize items (medication, lab_order, imaging, referral, follow_up, education).
6. Return your response as valid JSON matching the schema provided in the user message.
"""

ENTITY_EXTRACTION_SYSTEM_PROMPT = """\
You are a clinical NLP system that extracts structured medical entities from \
clinical text. Extract the following entity types:

- medications: name, action (prescribed/discontinued/continued/causing_adverse_effect), RxNorm code if known
- vitals: type, value, unit, status (normal/elevated/low/critical)
- symptoms: symptom name, duration if mentioned, SNOMED code if known
- diagnoses: name, ICD-10 code if inferable

Return your response as valid JSON matching the schema provided in the user message. \
Only extract entities explicitly mentioned in the text — do not infer or fabricate.
"""


class SOAPNoteGeneratorAgent(BaseAgent):
    """Generates structured SOAP clinical notes from diarized encounter transcripts."""

    name = "soap_note_generator"
    tier = AgentTier.DECISIONING
    version = "1.0.0"
    description = (
        "LLM-powered structured SOAP note generation from clinical encounter "
        "transcripts with medical terminology extraction"
    )
    min_confidence = 0.82

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "generate_soap")

        if action == "generate_soap":
            return await self._generate_soap(input_data)
        elif action == "extract_entities":
            return await self._extract_entities(input_data)
        elif action == "generate_section":
            return self._generate_section(input_data)
        elif action == "validate_note":
            return self._validate_note(input_data)
        elif action == "amend_note":
            return self._amend_note(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown SOAP note action: {action}",
                status=AgentStatus.FAILED,
            )

    async def _generate_soap(self, input_data: AgentInput) -> AgentOutput:
        """Generate a complete SOAP note from diarized transcript segments."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        encounter_id = ctx.get("encounter_id", str(uuid.uuid4()))
        segments = ctx.get("segments", [])

        # Build transcript text organised by speaker role
        transcript_lines: list[str] = []
        for seg in segments:
            role = seg.get("role", "unknown").capitalize()
            text = seg.get("text", "")
            transcript_lines.append(f"[{role}]: {text}")

        transcript_text = "\n".join(transcript_lines) if transcript_lines else "(empty transcript)"

        # ── LLM call: generate full SOAP note ───────────────────────────
        user_prompt = (
            "Generate a SOAP note from the following clinical encounter transcript.\n\n"
            f"TRANSCRIPT:\n{transcript_text}\n\n"
            "Return a JSON object with exactly this structure:\n"
            "{\n"
            '  "subjective": {\n'
            '    "chief_complaint": "...",\n'
            '    "history_of_present_illness": "...",\n'
            '    "review_of_systems": { "<system>": "..." },\n'
            '    "narrative": "..."\n'
            "  },\n"
            '  "objective": {\n'
            '    "vitals": { "blood_pressure": "...", "heart_rate": "...", '
            '"respiratory_rate": "...", "temperature": "...", "spo2": "..." },\n'
            '    "physical_exam": "...",\n'
            '    "narrative": "..."\n'
            "  },\n"
            '  "assessment": {\n'
            '    "diagnoses": [{"name": "...", "icd10": "...", "status": "new|existing", '
            '"certainty": "confirmed|probable|possible"}],\n'
            '    "clinical_reasoning": "...",\n'
            '    "narrative": "..."\n'
            "  },\n"
            '  "plan": {\n'
            '    "items": [{"description": "...", "category": '
            '"medication|lab_order|imaging|referral|follow_up|education", "priority": "high|medium|low"}],\n'
            '    "follow_up_interval": "...",\n'
            '    "referrals": [],\n'
            '    "narrative": "..."\n'
            "  },\n"
            '  "clinical_entities": {\n'
            '    "medications": [{"name": "...", "action": "...", "rxnorm": "..."}],\n'
            '    "vitals": [{"type": "...", "value": "...", "unit": "...", "status": "..."}],\n'
            '    "symptoms": [{"symptom": "...", "duration": "...", "snomed": "..."}],\n'
            '    "diagnoses": [{"name": "...", "icd10": "..."}]\n'
            "  }\n"
            "}\n\n"
            "Only include information actually present in the transcript. "
            "Use \"Not documented\" for missing sections. Return ONLY valid JSON, no markdown fences."
        )

        try:
            response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": user_prompt}],
                    system=SOAP_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=4096,
                )
            )
            soap_data = self._parse_json_response(response.content)
            generation_model = response.model
        except Exception as exc:
            logger.error("soap.llm_call_failed", error=str(exc), encounter_id=encounter_id)
            soap_data = self._fallback_soap(segments)
            generation_model = "rule-based-fallback"

        # Normalise structure — guarantee every section has a narrative key
        for section in SOAP_SECTIONS:
            if section not in soap_data:
                soap_data[section] = {"narrative": "Not documented"}
            elif not isinstance(soap_data[section], dict):
                soap_data[section] = {"narrative": str(soap_data[section])}
            elif "narrative" not in soap_data[section]:
                soap_data[section]["narrative"] = "Not documented"

        entities = soap_data.pop("clinical_entities", {})

        note = {
            "note_id": str(uuid.uuid4()),
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "generated_at": now.isoformat(),
            "status": "draft",
            "requires_attestation": True,
            "soap": {
                "subjective": soap_data["subjective"],
                "objective": soap_data["objective"],
                "assessment": soap_data["assessment"],
                "plan": soap_data["plan"],
            },
            "clinical_entities": entities,
            "source_segments": len(segments),
            "generation_model": generation_model,
            "word_count": sum(
                len(soap_data[s].get("narrative", "").split())
                for s in SOAP_SECTIONS
            ),
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=note,
            confidence=0.88,
            rationale=(
                f"Generated SOAP note for encounter {encounter_id} from "
                f"{len(segments)} transcript segments — awaiting provider attestation"
            ),
        )

    async def _extract_entities(self, input_data: AgentInput) -> AgentOutput:
        """Extract clinical entities (diagnoses, medications, vitals) from text."""
        ctx = input_data.context
        text_segments = ctx.get("text_segments", [])
        combined_text = "\n".join(text_segments) if text_segments else "(no text provided)"

        user_prompt = (
            "Extract clinical entities from the following text.\n\n"
            f"TEXT:\n{combined_text}\n\n"
            "Return a JSON object with this structure:\n"
            "{\n"
            '  "medications": [{"name": "...", "action": "prescribed|discontinued|continued|causing_adverse_effect", "rxnorm": "..."}],\n'
            '  "vitals": [{"type": "...", "value": "...", "unit": "...", "status": "normal|elevated|low|critical"}],\n'
            '  "symptoms": [{"symptom": "...", "duration": "...", "snomed": "..."}],\n'
            '  "diagnoses": [{"name": "...", "icd10": "..."}]\n'
            "}\n\n"
            "Only extract entities explicitly stated in the text. Return ONLY valid JSON, no markdown fences."
        )

        try:
            response = await llm_router.complete(
                LLMRequest(
                    messages=[{"role": "user", "content": user_prompt}],
                    system=ENTITY_EXTRACTION_SYSTEM_PROMPT,
                    temperature=0.2,
                    max_tokens=2048,
                )
            )
            entities = self._parse_json_response(response.content)
        except Exception as exc:
            logger.error("entities.llm_call_failed", error=str(exc))
            entities = self._fallback_entities(text_segments)

        # Ensure expected keys exist
        for key in ("medications", "vitals", "symptoms", "diagnoses"):
            if key not in entities or not isinstance(entities[key], list):
                entities[key] = []

        result = {
            "total_entities": sum(len(v) for v in entities.values()),
            "entities": entities,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.87,
            rationale=f"Extracted {result['total_entities']} clinical entities",
        )

    def _generate_section(self, input_data: AgentInput) -> AgentOutput:
        """Generate a single SOAP section."""
        ctx = input_data.context
        section = ctx.get("section", "subjective")
        segments = ctx.get("segments", [])

        if section not in SOAP_SECTIONS:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Invalid section: {section}", "valid": SOAP_SECTIONS},
                confidence=0.0,
                rationale=f"Invalid SOAP section: {section}",
                status=AgentStatus.FAILED,
            )

        all_text = [s.get("text", "") for s in segments]
        provider_text = [s.get("text", "") for s in segments if s.get("role") == "provider"]
        patient_text = [s.get("text", "") for s in segments if s.get("role") == "patient"]

        section_builders = {
            "subjective": lambda: self._build_subjective(patient_text, provider_text),
            "objective": lambda: self._build_objective(provider_text),
            "assessment": lambda: self._build_assessment(patient_text, provider_text),
            "plan": lambda: self._build_plan(provider_text),
        }

        content = section_builders[section]()

        return self.build_output(
            trace_id=input_data.trace_id,
            result={"section": section, "content": content},
            confidence=0.87,
            rationale=f"Generated {section} section from {len(segments)} segments",
        )

    def _validate_note(self, input_data: AgentInput) -> AgentOutput:
        """Validate a SOAP note for completeness and clinical accuracy."""
        ctx = input_data.context
        soap = ctx.get("soap", {})
        now = datetime.now(timezone.utc)

        issues: list[dict[str, Any]] = []

        for section in SOAP_SECTIONS:
            content = soap.get(section, {})
            if not content:
                issues.append({
                    "section": section,
                    "severity": "error",
                    "message": f"Missing {section} section",
                })
            elif not content.get("narrative"):
                issues.append({
                    "section": section,
                    "severity": "warning",
                    "message": f"Empty narrative in {section} section",
                })

        # Check for assessment-plan alignment
        if soap.get("assessment", {}).get("diagnoses") and soap.get("plan", {}).get("items"):
            diagnoses = soap["assessment"]["diagnoses"]
            plan_items = soap["plan"]["items"]
            for dx in diagnoses:
                dx_name = dx.get("name", "").lower()
                addressed = any(dx_name in item.get("description", "").lower() for item in plan_items)
                if not addressed:
                    issues.append({
                        "section": "plan",
                        "severity": "warning",
                        "message": f"Diagnosis '{dx.get('name')}' not addressed in plan",
                    })

        is_valid = not any(i["severity"] == "error" for i in issues)

        result = {
            "is_valid": is_valid,
            "validated_at": now.isoformat(),
            "total_issues": len(issues),
            "errors": [i for i in issues if i["severity"] == "error"],
            "warnings": [i for i in issues if i["severity"] == "warning"],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.90,
            rationale=f"Validation {'passed' if is_valid else 'failed'} — {len(issues)} issues found",
        )

    def _amend_note(self, input_data: AgentInput) -> AgentOutput:
        """Amend a SOAP note with provider corrections."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        note_id = ctx.get("note_id", "unknown")
        amendments = ctx.get("amendments", {})

        amended_sections = list(amendments.keys())

        result = {
            "note_id": note_id,
            "amended_at": now.isoformat(),
            "amended_sections": amended_sections,
            "status": "amended",
            "requires_re_attestation": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Note {note_id} amended in sections: {', '.join(amended_sections)}",
        )

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_json_response(text: str) -> dict[str, Any]:
        """Parse JSON from an LLM response, stripping markdown fences if present."""
        cleaned = text.strip()
        # Strip ```json ... ``` fences
        if cleaned.startswith("```"):
            first_newline = cleaned.index("\n") if "\n" in cleaned else 3
            cleaned = cleaned[first_newline + 1 :]
            if cleaned.endswith("```"):
                cleaned = cleaned[: -3]
            cleaned = cleaned.strip()
        return json.loads(cleaned)

    # ── Rule-based Fallbacks (used when LLM is unavailable) ──────────────────

    @staticmethod
    def _fallback_soap(segments: list[dict[str, Any]]) -> dict[str, Any]:
        """Build a minimal rule-based SOAP note when the LLM call fails."""
        patient_text = [s.get("text", "") for s in segments if s.get("role") == "patient"]
        provider_text = [s.get("text", "") for s in segments if s.get("role") == "provider"]
        all_text = [s.get("text", "") for s in segments]

        chief_complaint = patient_text[0][:120] if patient_text else "Not documented"

        return {
            "subjective": {
                "chief_complaint": chief_complaint,
                "history_of_present_illness": " ".join(patient_text) if patient_text else "Not documented",
                "review_of_systems": {},
                "narrative": f"CC: {chief_complaint}\nHPI: {' '.join(patient_text)}" if patient_text else "Not documented",
            },
            "objective": {
                "vitals": {},
                "physical_exam": " ".join(provider_text) if provider_text else "Not documented",
                "narrative": " ".join(provider_text) if provider_text else "Not documented",
            },
            "assessment": {
                "diagnoses": [],
                "clinical_reasoning": "Auto-generated fallback — requires clinician review.",
                "narrative": "Assessment requires clinician review (LLM unavailable).",
            },
            "plan": {
                "items": [],
                "follow_up_interval": "Not documented",
                "referrals": [],
                "narrative": "Plan requires clinician review (LLM unavailable).",
            },
            "clinical_entities": {
                "medications": [],
                "vitals": [],
                "symptoms": [],
                "diagnoses": [],
            },
        }

    @staticmethod
    def _fallback_entities(text_segments: list[str]) -> dict[str, Any]:
        """Return an empty entity structure when the LLM call fails."""
        return {
            "medications": [],
            "vitals": [],
            "symptoms": [],
            "diagnoses": [],
        }

    # ── Legacy section builders (used by _generate_section) ──────────────────

    @staticmethod
    def _build_subjective(patient_text: list[str], provider_text: list[str]) -> dict[str, Any]:
        chief_complaint = patient_text[0][:120] if patient_text else "Not documented"
        hpi = " ".join(patient_text) if patient_text else "Not documented"
        return {
            "chief_complaint": chief_complaint,
            "history_of_present_illness": hpi,
            "review_of_systems": {},
            "narrative": f"CC: {chief_complaint}\nHPI: {hpi}",
        }

    @staticmethod
    def _build_objective(provider_text: list[str]) -> dict[str, Any]:
        exam = " ".join(provider_text) if provider_text else "Not documented"
        return {
            "vitals": {},
            "physical_exam": exam,
            "narrative": exam,
        }

    @staticmethod
    def _build_assessment(patient_text: list[str], provider_text: list[str]) -> dict[str, Any]:
        combined = " ".join(patient_text + provider_text) if (patient_text or provider_text) else "Not documented"
        return {
            "diagnoses": [],
            "clinical_reasoning": combined,
            "narrative": combined,
        }

    @staticmethod
    def _build_plan(provider_text: list[str]) -> dict[str, Any]:
        combined = " ".join(provider_text) if provider_text else "Not documented"
        return {
            "items": [],
            "follow_up_interval": "Not documented",
            "referrals": [],
            "narrative": combined,
        }
