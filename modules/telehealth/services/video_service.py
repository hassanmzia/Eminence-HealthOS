"""
Eminence HealthOS — Telehealth Video Service

Manages video room lifecycle via Daily.co REST API. Handles room creation,
participant token generation, and session teardown. Falls back to demo
mode when DAILY_API_KEY is not configured.
"""

from __future__ import annotations

import hashlib
import logging
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Optional

import httpx

logger = logging.getLogger("healthos.telehealth.video")

DAILY_API_BASE = "https://api.daily.co/v1"


class VideoService:
    """Manages Daily.co video rooms for telehealth sessions."""

    def __init__(self) -> None:
        self._api_key = os.getenv("DAILY_API_KEY", "")
        self._domain = os.getenv("DAILY_DOMAIN", "")  # e.g. "healthos.daily.co"

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._domain)

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"}

    async def create_room(self, session_id: str, *, exp_minutes: int = 120) -> dict[str, Any]:
        """Create a Daily.co room for a telehealth session."""
        room_name = f"healthos-{session_id}"
        exp = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)

        if not self.is_configured:
            logger.info("Daily.co not configured — returning demo room for session %s", session_id)
            return {
                "room_name": room_name,
                "room_url": f"https://demo.daily.co/{room_name}",
                "provider": "daily",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "expires_at": exp.isoformat(),
                "demo_mode": True,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DAILY_API_BASE}/rooms",
                headers=self._headers(),
                json={
                    "name": room_name,
                    "privacy": "private",
                    "properties": {
                        "exp": int(exp.timestamp()),
                        "enable_recording": "cloud",
                        "enable_chat": True,
                        "enable_screenshare": True,
                        "max_participants": 4,
                        "enable_prejoin_ui": True,
                        "hipaa": True,
                    },
                },
            )
            resp.raise_for_status()
            room = resp.json()

        return {
            "room_name": room.get("name", room_name),
            "room_url": room.get("url", f"https://{self._domain}/{room_name}"),
            "provider": "daily",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "expires_at": exp.isoformat(),
            "demo_mode": False,
        }

    async def generate_token(
        self,
        room_name: str,
        *,
        user_name: str = "Participant",
        user_id: str = "",
        is_owner: bool = False,
        exp_minutes: int = 120,
    ) -> dict[str, Any]:
        """Generate a meeting token for a participant."""
        exp = datetime.now(timezone.utc) + timedelta(minutes=exp_minutes)

        if not self.is_configured:
            # Generate a deterministic demo token
            demo_token = hashlib.sha256(f"{room_name}:{user_id}:{user_name}".encode()).hexdigest()[:32]
            return {
                "token": f"demo_{demo_token}",
                "room_name": room_name,
                "user_name": user_name,
                "is_owner": is_owner,
                "expires_at": exp.isoformat(),
                "demo_mode": True,
            }

        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{DAILY_API_BASE}/meeting-tokens",
                headers=self._headers(),
                json={
                    "properties": {
                        "room_name": room_name,
                        "user_name": user_name,
                        "user_id": user_id,
                        "is_owner": is_owner,
                        "exp": int(exp.timestamp()),
                        "enable_recording": "cloud" if is_owner else None,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json()

        return {
            "token": data.get("token", ""),
            "room_name": room_name,
            "user_name": user_name,
            "is_owner": is_owner,
            "expires_at": exp.isoformat(),
            "demo_mode": False,
        }

    async def delete_room(self, room_name: str) -> bool:
        """Delete a Daily.co room when the session ends."""
        if not self.is_configured:
            logger.info("Daily.co not configured — skipping room deletion for %s", room_name)
            return True

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.delete(
                    f"{DAILY_API_BASE}/rooms/{room_name}",
                    headers=self._headers(),
                )
                return resp.status_code in (200, 204, 404)
        except Exception:
            logger.warning("Failed to delete room %s", room_name, exc_info=True)
            return False


# Module-level singleton
video_service = VideoService()
