"""Ambient AI transcription service layer."""

import logging
from typing import Optional

logger = logging.getLogger("healthos.ambient_ai.transcription_service")


class TranscriptionService:
    """Manages ambient listening sessions and transcription."""

    def __init__(self, db=None, redis=None):
        self._db = db
        self._redis = redis
        self._sessions: dict[str, dict] = {}

    async def start_session(self, encounter_id: str, data: dict) -> dict:
        session = {"encounter_id": encounter_id, "status": "recording", **data}
        self._sessions[encounter_id] = session
        logger.info("Started ambient session for encounter %s", encounter_id)
        return session

    async def end_session(self, encounter_id: str) -> Optional[dict]:
        session = self._sessions.get(encounter_id)
        if session:
            session["status"] = "completed"
        logger.info("Ended ambient session for encounter %s", encounter_id)
        return session

    async def get_session(self, encounter_id: str) -> Optional[dict]:
        return self._sessions.get(encounter_id)

    async def store_transcription(self, encounter_id: str, segments: list[dict]) -> dict:
        session = self._sessions.get(encounter_id, {})
        session.setdefault("segments", []).extend(segments)
        return {"encounter_id": encounter_id, "total_segments": len(session.get("segments", []))}
