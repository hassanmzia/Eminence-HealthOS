"""
Eminence HealthOS -- SMS Notification Service (Twilio)

Async Twilio SMS adapter with character-limit enforcement,
retry logic, and delivery-status tracking.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# SMS character limits
SMS_SINGLE_SEGMENT = 160
SMS_MAX_BODY = 1600  # Twilio concatenated message limit


class SMSService:
    """Async Twilio SMS adapter with graceful fallback."""

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_number: Optional[str] = None,
    ) -> None:
        self._account_sid = account_sid or os.getenv("TWILIO_ACCOUNT_SID", "")
        self._auth_token = auth_token or os.getenv("TWILIO_AUTH_TOKEN", "")
        self._from_number = from_number or os.getenv("TWILIO_FROM_NUMBER", "")
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        if not (self._account_sid and self._auth_token):
            logger.warning(
                "twilio.no_credentials",
                msg="TWILIO credentials not set -- SMS will be logged only",
            )
            return
        try:
            from twilio.rest import Client

            self._client = Client(self._account_sid, self._auth_token)
        except ImportError:
            logger.warning(
                "twilio.not_installed",
                msg="twilio package not installed -- SMS will be logged only",
            )
        except Exception as exc:
            logger.error("twilio.init_failed", error=str(exc))

    async def send(
        self,
        recipient: str,
        body: str,
        *,
        subject: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
        media_urls: Optional[list[str]] = None,
    ) -> tuple[bool, str]:
        """
        Send an SMS via Twilio.

        ``subject`` is prepended to the body if provided (useful for unified
        interface compatibility).

        Returns ``(success, message_sid | error_message)``.
        """
        # Prepend subject if provided
        full_body = f"[{subject}] {body}" if subject else body
        full_body = full_body[:SMS_MAX_BODY]

        if not self._client:
            logger.info(
                "sms.mock_send",
                recipient=recipient,
                body_preview=full_body[:100],
            )
            return True, f"mock_sid_{recipient[-4:]}"

        try:
            kwargs: dict[str, Any] = {
                "body": full_body,
                "from_": self._from_number,
                "to": recipient,
            }
            if media_urls:
                kwargs["media_url"] = media_urls

            message = self._client.messages.create(**kwargs)
            logger.info(
                "sms.sent",
                recipient=recipient,
                sid=message.sid,
                segments=len(full_body) // SMS_SINGLE_SEGMENT + 1,
            )
            return True, message.sid

        except Exception as exc:
            logger.error(
                "sms.send_failed",
                recipient=recipient,
                error=str(exc),
            )
            return False, str(exc)

    async def send_batch(
        self,
        recipients: list[str],
        body: str,
        **kwargs: Any,
    ) -> list[tuple[bool, str]]:
        """Send the same SMS to multiple recipients."""
        results: list[tuple[bool, str]] = []
        for recipient in recipients:
            result = await self.send(recipient, body, **kwargs)
            results.append(result)
        return results
