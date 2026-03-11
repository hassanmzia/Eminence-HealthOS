"""
Telehealth session service layer.

Manages session state, provider matching, and visit workflow.
"""

import logging
from typing import Optional

logger = logging.getLogger("healthos.telehealth.session_service")


class TelehealthSessionService:
    """Business logic for telehealth sessions."""

    def __init__(self, redis=None):
        self._redis = redis
        self._sessions: dict[str, dict] = {}  # In-memory fallback

    async def create_session(self, session_data: dict) -> dict:
        """Store session state."""
        session_id = session_data["session_id"]

        if self._redis:
            import json
            await self._redis.set(
                f"telehealth:session:{session_id}",
                json.dumps(session_data),
                ex=7200,  # 2 hour expiry
            )
        else:
            self._sessions[session_id] = session_data

        return session_data

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session state."""
        if self._redis:
            import json
            data = await self._redis.get(f"telehealth:session:{session_id}")
            return json.loads(data) if data else None
        return self._sessions.get(session_id)

    async def update_session_status(self, session_id: str, status: str) -> Optional[dict]:
        """Update session status."""
        session = await self.get_session(session_id)
        if not session:
            return None
        session["status"] = status

        if self._redis:
            import json
            await self._redis.set(
                f"telehealth:session:{session_id}",
                json.dumps(session),
                ex=7200,
            )
        else:
            self._sessions[session_id] = session

        return session

    async def get_waiting_room(self, tenant_id: str) -> list[dict]:
        """Get all sessions in waiting status for a tenant."""
        # In production, this would query Redis with pattern matching
        waiting = []
        for sid, session in self._sessions.items():
            if session.get("status") == "waiting" and session.get("tenant_id") == tenant_id:
                waiting.append(session)
        return sorted(waiting, key=lambda s: s.get("created_at", ""))
