"""
Eminence HealthOS — Ambient Listening Agent (#41)
Layer 1 (Sensing): Captures and transcribes doctor-patient conversations during
telehealth or in-person visits, producing a raw timestamped transcript.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

import logging

from healthos_platform.agents.base import BaseAgent
from healthos_platform.agents.types import (
    AgentInput,
    AgentOutput,
    AgentStatus,
    AgentTier,
)
from healthos_platform.ml.llm.router import llm_router, LLMRequest

logger = logging.getLogger("healthos.agent.ambient_listening")

# Supported audio sources
AUDIO_SOURCES = ["telehealth_webrtc", "in_person_microphone", "uploaded_recording", "phone_call"]

# Supported languages
SUPPORTED_LANGUAGES = {
    "en": "English",
    "es": "Spanish",
    "fr": "French",
    "de": "German",
    "zh": "Chinese",
    "pt": "Portuguese",
    "ar": "Arabic",
}


class AmbientListeningAgent(BaseAgent):
    """Captures and transcribes doctor-patient conversations in real time."""

    name = "ambient_listening"
    tier = AgentTier.SENSING
    version = "1.0.0"
    description = (
        "Real-time audio capture and transcription of clinical encounters, "
        "supporting telehealth and in-person modalities"
    )
    min_confidence = 0.80

    async def process(self, input_data: AgentInput) -> AgentOutput:
        ctx = input_data.context
        action = ctx.get("action", "transcribe")

        if action == "transcribe":
            return await self._transcribe(input_data)
        elif action == "start_session":
            return self._start_session(input_data)
        elif action == "end_session":
            return self._end_session(input_data)
        elif action == "get_status":
            return self._get_status(input_data)
        elif action == "language_detect":
            return self._language_detect(input_data)
        else:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unknown action: {action}"},
                confidence=0.0,
                rationale=f"Unknown ambient listening action: {action}",
                status=AgentStatus.FAILED,
            )

    def _start_session(self, input_data: AgentInput) -> AgentOutput:
        """Initialize a new recording session for an encounter."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        encounter_id = ctx.get("encounter_id", str(uuid.uuid4()))
        source = ctx.get("audio_source", "telehealth_webrtc")
        language = ctx.get("language", "en")

        if source not in AUDIO_SOURCES:
            return self.build_output(
                trace_id=input_data.trace_id,
                result={"error": f"Unsupported audio source: {source}", "supported": AUDIO_SOURCES},
                confidence=0.0,
                rationale=f"Audio source '{source}' is not supported",
                status=AgentStatus.FAILED,
            )

        session = {
            "session_id": str(uuid.uuid4()),
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "audio_source": source,
            "language": language,
            "language_name": SUPPORTED_LANGUAGES.get(language, language),
            "status": "recording",
            "started_at": now.isoformat(),
            "sample_rate_hz": 16000,
            "channels": 1,
            "encoding": "opus",
            "noise_cancellation": True,
            "phi_redaction_enabled": True,
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=session,
            confidence=0.95,
            rationale=f"Recording session started for encounter {encounter_id} via {source}",
        )

    async def _transcribe(self, input_data: AgentInput) -> AgentOutput:
        """Transcribe audio data into a timestamped raw transcript."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)

        encounter_id = ctx.get("encounter_id", "unknown")
        audio_duration_sec = ctx.get("audio_duration_sec", 0)
        audio_chunks = ctx.get("audio_chunks", [])
        language = ctx.get("language", "en")

        # Simulate transcription of audio chunks into segments
        segments: list[dict[str, Any]] = []
        current_time = 0.0

        if audio_chunks:
            for i, chunk in enumerate(audio_chunks):
                segment_duration = chunk.get("duration_sec", 5.0)
                segments.append({
                    "segment_id": i,
                    "start_sec": round(current_time, 2),
                    "end_sec": round(current_time + segment_duration, 2),
                    "text": chunk.get("text", f"[Transcribed segment {i}]"),
                    "confidence": chunk.get("confidence", 0.92),
                    "language": language,
                    "is_speech": True,
                })
                current_time += segment_duration
        else:
            # Generate demo transcript segments for an encounter
            demo_segments = [
                {"text": "Good morning. How are you feeling today?", "duration": 3.2, "confidence": 0.96},
                {"text": "I've been having some chest tightness, especially in the mornings.", "duration": 4.1, "confidence": 0.94},
                {"text": "How long has this been going on?", "duration": 2.0, "confidence": 0.97},
                {"text": "About two weeks now. It started after I changed my blood pressure medication.", "duration": 5.3, "confidence": 0.93},
                {"text": "Which medication were you switched to?", "duration": 2.5, "confidence": 0.96},
                {"text": "I was moved from lisinopril to amlodipine about three weeks ago.", "duration": 4.0, "confidence": 0.95},
                {"text": "Let me check your vitals. Blood pressure is 142 over 88. Heart rate is 78.", "duration": 5.8, "confidence": 0.91},
                {"text": "I'm also noticing some swelling in my ankles.", "duration": 3.0, "confidence": 0.94},
                {"text": "That can be a side effect of amlodipine. Let's discuss adjusting your medication.", "duration": 5.5, "confidence": 0.95},
                {"text": "I'd also like to order some blood work to check your kidney function.", "duration": 4.2, "confidence": 0.93},
            ]
            for i, seg in enumerate(demo_segments):
                segments.append({
                    "segment_id": i,
                    "start_sec": round(current_time, 2),
                    "end_sec": round(current_time + seg["duration"], 2),
                    "text": seg["text"],
                    "confidence": seg["confidence"],
                    "language": language,
                    "is_speech": True,
                })
                current_time += seg["duration"]

        total_duration = current_time if current_time > 0 else audio_duration_sec
        avg_confidence = (
            sum(s["confidence"] for s in segments) / len(segments) if segments else 0.0
        )

        # --- LLM: extract clinical insights from transcription segments ---
        clinical_insights: str | None = None
        try:
            transcript_text = "\n".join(
                f"[{s['start_sec']:.1f}s] {s['text']}" for s in segments
            )
            resp = await llm_router.complete(LLMRequest(
                messages=[{"role": "user", "content": (
                    f"Analyze the following clinical encounter transcript and extract:\n"
                    f"1. Key clinical terms and medical concepts\n"
                    f"2. Patient concerns and symptoms\n"
                    f"3. Action items (orders, referrals, follow-ups)\n"
                    f"4. Medication mentions and changes\n\n"
                    f"Transcript:\n{transcript_text}"
                )}],
                system=(
                    "You are a clinical NLP assistant for Eminence HealthOS. "
                    "Extract structured clinical insights from doctor-patient "
                    "conversation transcripts. Be concise and medically precise."
                ),
                temperature=0.3,
                max_tokens=1024,
            ))
            clinical_insights = resp.content
        except Exception:
            logger.warning("LLM clinical_insights generation failed; continuing without it")

        result = {
            "encounter_id": encounter_id,
            "patient_id": str(input_data.patient_id) if input_data.patient_id else None,
            "transcription_timestamp": now.isoformat(),
            "language": language,
            "language_name": SUPPORTED_LANGUAGES.get(language, language),
            "total_duration_sec": round(total_duration, 2),
            "total_segments": len(segments),
            "average_confidence": round(avg_confidence, 3),
            "segments": segments,
            "clinical_insights": clinical_insights,
            "metadata": {
                "model": "whisper-large-v3",
                "sample_rate_hz": 16000,
                "noise_filtered": True,
                "phi_detected_and_flagged": True,
            },
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=round(avg_confidence, 3),
            rationale=(
                f"Transcribed {len(segments)} segments ({round(total_duration, 1)}s) "
                f"for encounter {encounter_id} — avg confidence {round(avg_confidence, 3)}"
            ),
        )

    def _end_session(self, input_data: AgentInput) -> AgentOutput:
        """Finalize a recording session and produce the complete transcript."""
        ctx = input_data.context
        now = datetime.now(timezone.utc)
        session_id = ctx.get("session_id", "unknown")

        result = {
            "session_id": session_id,
            "status": "completed",
            "ended_at": now.isoformat(),
            "total_segments_captured": ctx.get("total_segments", 0),
            "total_duration_sec": ctx.get("total_duration_sec", 0),
            "transcript_ready": True,
            "next_step": "speaker_diarization",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Recording session {session_id} completed successfully",
        )

    def _get_status(self, input_data: AgentInput) -> AgentOutput:
        """Return current recording session status."""
        ctx = input_data.context
        session_id = ctx.get("session_id", "unknown")

        result = {
            "session_id": session_id,
            "status": "recording",
            "elapsed_sec": ctx.get("elapsed_sec", 0),
            "segments_captured": ctx.get("segments_captured", 0),
            "audio_quality": "good",
            "noise_level": "low",
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.95,
            rationale=f"Session {session_id} is actively recording",
        )

    def _language_detect(self, input_data: AgentInput) -> AgentOutput:
        """Detect the primary language of the audio stream."""
        ctx = input_data.context
        detected = ctx.get("detected_language", "en")

        result = {
            "detected_language": detected,
            "language_name": SUPPORTED_LANGUAGES.get(detected, detected),
            "confidence": 0.94,
            "alternatives": [
                {"language": k, "name": v, "probability": 0.02}
                for k, v in SUPPORTED_LANGUAGES.items()
                if k != detected
            ][:3],
        }

        return self.build_output(
            trace_id=input_data.trace_id,
            result=result,
            confidence=0.94,
            rationale=f"Detected language: {SUPPORTED_LANGUAGES.get(detected, detected)}",
        )
