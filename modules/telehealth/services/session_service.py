"""
Telehealth session service layer.

Manages session state, provider matching, and visit workflow.
Supports DB persistence (primary), Redis cache, and in-memory fallback.
"""

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from shared.models.telehealth_session import TelehealthSession
from modules.telehealth.events import TelehealthEventPublisher

logger = logging.getLogger("healthos.telehealth.session_service")

# Maps status strings to the corresponding publisher method name.
_STATUS_EVENT_METHOD: dict[str, str] = {
    "started": "session_started",
    "in_progress": "session_started",
    "ended": "session_ended",
    "completed": "session_ended",
    "cancelled": "session_cancelled",
}


class TelehealthSessionService:
    """Business logic for telehealth sessions."""

    def __init__(
        self,
        redis=None,
        db: Optional[AsyncSession] = None,
        event_publisher: Optional[TelehealthEventPublisher] = None,
    ):
        self._redis = redis
        self._db = db
        self._sessions: dict[str, dict] = {}  # In-memory fallback
        self._events = event_publisher or TelehealthEventPublisher()

    # ── DB-backed methods ─────────────────────────────────────────────────

    async def create_session_db(self, session_data: dict) -> TelehealthSession:
        """Persist a new telehealth session to PostgreSQL and warm the cache."""
        if not self._db:
            raise RuntimeError("Database session not available")

        model = TelehealthSession(
            session_id=session_data["session_id"],
            tenant_id=session_data["tenant_id"],
            patient_id=session_data["patient_id"],
            provider_id=session_data.get("provider_id"),
            visit_type=session_data.get("visit_type", "on_demand"),
            urgency=session_data.get("urgency", "routine"),
            status=session_data.get("status", "waiting"),
            chief_complaint=session_data.get("chief_complaint"),
            symptoms=session_data.get("symptoms"),
            estimated_wait_minutes=session_data.get("estimated_wait_minutes"),
            start_time=session_data.get("start_time"),
            end_time=session_data.get("end_time"),
            encounter_id=session_data.get("encounter_id"),
        )
        self._db.add(model)
        await self._db.flush()

        # Warm Redis cache
        if self._redis:
            await self._redis.set(
                f"telehealth:session:{model.session_id}",
                json.dumps(session_data, default=str),
                ex=7200,
            )

        logger.info("Created telehealth session %s in DB", model.session_id)
        return model

    async def get_session_db(self, session_id: str) -> Optional[TelehealthSession]:
        """Retrieve a session from the database."""
        if not self._db:
            raise RuntimeError("Database session not available")

        result = await self._db.execute(
            select(TelehealthSession).where(TelehealthSession.session_id == session_id)
        )
        return result.scalars().first()

    async def update_status_db(
        self, session_id: str, status: str
    ) -> Optional[TelehealthSession]:
        """Update session status in PostgreSQL and invalidate the cache."""
        if not self._db:
            raise RuntimeError("Database session not available")

        now = datetime.now(timezone.utc)
        values: dict = {"status": status, "updated_at": now}

        if status == "in_progress":
            values["start_time"] = now
        elif status in ("completed", "cancelled"):
            values["end_time"] = now

        await self._db.execute(
            update(TelehealthSession)
            .where(TelehealthSession.session_id == session_id)
            .values(**values)
        )
        await self._db.flush()

        # Invalidate Redis so next read hits DB for fresh data
        if self._redis:
            await self._redis.delete(f"telehealth:session:{session_id}")

        logger.info("Updated session %s status to %s", session_id, status)

        # Emit the corresponding lifecycle event
        updated = await self.get_session_db(session_id)
        await self._emit_status_event(session_id, status, updated)

        return updated

    # ── Original in-memory / Redis methods (backward compat) ──────────────

    async def create_session(self, session_data: dict) -> dict:
        """Store session state (in-memory / Redis)."""
        session_id = session_data["session_id"]

        if self._redis:
            await self._redis.set(
                f"telehealth:session:{session_id}",
                json.dumps(session_data),
                ex=7200,  # 2 hour expiry
            )
        else:
            self._sessions[session_id] = session_data

        return session_data

    async def get_session(self, session_id: str) -> Optional[dict]:
        """Retrieve session state (Redis → in-memory → DB fallback)."""
        if self._redis:
            data = await self._redis.get(f"telehealth:session:{session_id}")
            if data:
                return json.loads(data)

        if session_id in self._sessions:
            return self._sessions[session_id]

        # Fall through to DB if available
        if self._db:
            model = await self.get_session_db(session_id)
            if model:
                return self._model_to_dict(model)

        return None

    async def update_session_status(self, session_id: str, status: str) -> Optional[dict]:
        """Update session status."""
        session = await self.get_session(session_id)
        if not session:
            return None
        session["status"] = status

        if self._redis:
            await self._redis.set(
                f"telehealth:session:{session_id}",
                json.dumps(session),
                ex=7200,
            )
        else:
            self._sessions[session_id] = session

        # Emit the corresponding lifecycle event
        await self._emit_status_event(session_id, status, session)

        return session

    async def get_waiting_room(self, tenant_id: str) -> list[dict]:
        """Get all sessions in waiting status for a tenant."""
        # If DB is available, prefer it for complete results
        if self._db:
            result = await self._db.execute(
                select(TelehealthSession)
                .where(
                    TelehealthSession.tenant_id == tenant_id,
                    TelehealthSession.status == "waiting",
                )
                .order_by(TelehealthSession.created_at)
            )
            return [self._model_to_dict(m) for m in result.scalars().all()]

        # In-memory fallback
        waiting = []
        for sid, session in self._sessions.items():
            if session.get("status") == "waiting" and session.get("tenant_id") == tenant_id:
                waiting.append(session)
        return sorted(waiting, key=lambda s: s.get("created_at", ""))

    # ── Escalation ─────────────────────────────────────────────────────────

    async def escalate(
        self,
        session_id: str,
        reason: str,
        severity: str = "high",
    ) -> None:
        """Flag a session for clinical escalation and emit an event."""
        session = await self.get_session(session_id)
        patient_id = ""
        tenant_id = "default"
        if session:
            patient_id = str(session.get("patient_id", ""))
            tenant_id = session.get("tenant_id", "default")

        logger.warning(
            "Escalation triggered for session %s — reason=%s severity=%s",
            session_id,
            reason,
            severity,
        )
        await self._events.escalation_triggered(
            session_id=session_id,
            patient_id=patient_id,
            reason=reason,
            severity=severity,
            tenant_id=tenant_id,
        )

    # ── Event helpers ─────────────────────────────────────────────────────

    async def _emit_status_event(
        self, session_id: str, status: str, session_data: Optional[dict] = None
    ) -> None:
        """Publish a lifecycle event matching the new *status*, if mapped."""
        method_name = _STATUS_EVENT_METHOD.get(status)
        if not method_name:
            return

        patient_id = ""
        tenant_id = "default"
        if session_data:
            patient_id = str(session_data.get("patient_id", ""))
            tenant_id = session_data.get("tenant_id", "default")
        elif isinstance(session_data, TelehealthSession):
            patient_id = str(session_data.patient_id)
            tenant_id = session_data.tenant_id or "default"

        method = getattr(self._events, method_name)
        await method(
            session_id=session_id,
            patient_id=patient_id,
            tenant_id=tenant_id,
            data={"status": status},
        )

    # ── Helpers ───────────────────────────────────────────────────────────

    @staticmethod
    def _model_to_dict(model: TelehealthSession) -> dict:
        """Convert a TelehealthSession ORM instance to a plain dict."""
        return {
            "id": str(model.id),
            "session_id": model.session_id,
            "tenant_id": model.tenant_id,
            "patient_id": str(model.patient_id),
            "provider_id": str(model.provider_id) if model.provider_id else None,
            "visit_type": model.visit_type,
            "urgency": model.urgency,
            "status": model.status,
            "chief_complaint": model.chief_complaint,
            "symptoms": model.symptoms,
            "estimated_wait_minutes": model.estimated_wait_minutes,
            "start_time": model.start_time.isoformat() if model.start_time else None,
            "end_time": model.end_time.isoformat() if model.end_time else None,
            "encounter_id": str(model.encounter_id) if model.encounter_id else None,
            "created_at": model.created_at.isoformat() if model.created_at else None,
            "updated_at": model.updated_at.isoformat() if model.updated_at else None,
        }
