"""
Eminence HealthOS -- Email Notification Service (SendGrid)

Async SendGrid integration with HTML template support,
Django-style fallback, and delivery tracking.
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)


class EmailService:
    """Async SendGrid email adapter with graceful fallback."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> None:
        self._api_key = api_key or os.getenv("SENDGRID_API_KEY", "")
        self._from_email = from_email or os.getenv(
            "DEFAULT_FROM_EMAIL", "notifications@healthos.eminence.care"
        )
        self._client: Any = None
        self._init_client()

    def _init_client(self) -> None:
        """Lazily initialise the SendGrid client."""
        if not self._api_key:
            logger.warning(
                "sendgrid.no_api_key",
                msg="SENDGRID_API_KEY not set -- emails will be logged only",
            )
            return
        try:
            import sendgrid  # noqa: F811

            self._client = sendgrid.SendGridAPIClient(api_key=self._api_key)
        except ImportError:
            logger.warning(
                "sendgrid.not_installed",
                msg="sendgrid package not installed -- emails will be logged only",
            )
        except Exception as exc:
            logger.error("sendgrid.init_failed", error=str(exc))

    async def send(
        self,
        recipient: str,
        subject: str,
        body: str,
        *,
        html: bool = True,
        metadata: Optional[dict[str, Any]] = None,
        template_id: Optional[str] = None,
        template_data: Optional[dict[str, Any]] = None,
    ) -> tuple[bool, str]:
        """
        Send an email via SendGrid.

        Returns ``(success, external_message_id | error_message)``.
        """
        if not self._client:
            logger.info(
                "email.mock_send",
                recipient=recipient,
                subject=subject,
                body_preview=body[:120],
            )
            return True, f"mock_email_{recipient.replace('@', '_at_')}"

        try:
            from sendgrid.helpers.mail import Content, Mail, To

            content_type = "text/html" if html else "text/plain"
            rendered_body = f"<div style='font-family:sans-serif'>{body}</div>" if html else body

            message = Mail(
                from_email=self._from_email,
                to_emails=To(recipient),
                subject=subject,
                html_content=Content(content_type, rendered_body),
            )

            # Dynamic template support
            if template_id:
                message.template_id = template_id
                if template_data:
                    from sendgrid.helpers.mail import DynamicTemplateData
                    message.dynamic_template_data = template_data

            # Custom metadata as SendGrid categories
            if metadata:
                from sendgrid.helpers.mail import Category
                for key, val in list(metadata.items())[:10]:
                    message.add_category(Category(f"{key}:{val}"))

            response = self._client.send(message)
            message_id = response.headers.get("X-Message-Id", "")
            logger.info(
                "email.sent",
                recipient=recipient,
                message_id=message_id,
                status_code=response.status_code,
            )
            return True, message_id

        except ImportError:
            # Last-resort: log the email
            logger.info(
                "email.fallback_log",
                recipient=recipient,
                subject=subject,
                body_preview=body[:200],
            )
            return True, "logged_email"

        except Exception as exc:
            logger.error(
                "email.send_failed",
                recipient=recipient,
                error=str(exc),
            )
            return False, str(exc)

    async def send_batch(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        **kwargs: Any,
    ) -> list[tuple[bool, str]]:
        """Send the same email to multiple recipients."""
        results: list[tuple[bool, str]] = []
        for recipient in recipients:
            result = await self.send(recipient, subject, body, **kwargs)
            results.append(result)
        return results
