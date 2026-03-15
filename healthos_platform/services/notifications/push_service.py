"""
Eminence HealthOS -- Push Notification Service (FCM / WebSocket)

Firebase Cloud Messaging push adapter and in-app real-time alert
delivery via Redis Pub/Sub (for WebSocket consumers).
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional

import structlog

logger = structlog.get_logger(__name__)

# FCM body character limit
PUSH_BODY_MAX = 200


class PushService:
    """Firebase Cloud Messaging push notification adapter."""

    def __init__(self, firebase_credentials_path: Optional[str] = None) -> None:
        self._credentials_path = firebase_credentials_path or os.getenv(
            "GOOGLE_APPLICATION_CREDENTIALS", ""
        )
        self._firebase_app: Any = None
        self._init_firebase()

    def _init_firebase(self) -> None:
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                if self._credentials_path and os.path.exists(self._credentials_path):
                    cred = credentials.Certificate(self._credentials_path)
                    self._firebase_app = firebase_admin.initialize_app(cred)
                else:
                    # Attempt default credential discovery (GCP environments)
                    self._firebase_app = firebase_admin.initialize_app()
            else:
                self._firebase_app = firebase_admin.get_app()
        except ImportError:
            logger.warning(
                "firebase.not_installed",
                msg="firebase-admin not installed -- push notifications will be logged only",
            )
        except Exception as exc:
            logger.warning("firebase.init_skipped", error=str(exc))

    async def send(
        self,
        device_token: str,
        subject: str,
        body: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
        image_url: Optional[str] = None,
        priority: str = "high",
    ) -> tuple[bool, str]:
        """
        Send a push notification to a single device via FCM.

        Returns ``(success, fcm_message_id | error_message)``.
        """
        if not self._firebase_app:
            logger.info(
                "push.mock_send",
                device_token=device_token[:12] + "...",
                subject=subject,
                body_preview=body[:80],
            )
            return True, f"mock_push_{device_token[:8]}"

        try:
            from firebase_admin import messaging

            notification = messaging.Notification(
                title=subject,
                body=body[:PUSH_BODY_MAX],
                image=image_url,
            )

            data_payload = {k: str(v) for k, v in (metadata or {}).items()}

            android_config = messaging.AndroidConfig(
                priority=priority,
                notification=messaging.AndroidNotification(
                    click_action="OPEN_NOTIFICATION",
                ),
            )

            apns_config = messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(badge=1, sound="default"),
                ),
            )

            message = messaging.Message(
                notification=notification,
                token=device_token,
                data=data_payload,
                android=android_config,
                apns=apns_config,
            )

            response = messaging.send(message)
            logger.info("push.sent", response=response)
            return True, response

        except Exception as exc:
            logger.error("push.send_failed", error=str(exc))
            return False, str(exc)

    async def send_multicast(
        self,
        device_tokens: list[str],
        subject: str,
        body: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
    ) -> tuple[int, int]:
        """
        Send a push notification to multiple devices.

        Returns ``(success_count, failure_count)``.
        """
        if not self._firebase_app or not device_tokens:
            logger.info(
                "push.mock_multicast",
                token_count=len(device_tokens),
                subject=subject,
            )
            return len(device_tokens), 0

        try:
            from firebase_admin import messaging

            notification = messaging.Notification(
                title=subject,
                body=body[:PUSH_BODY_MAX],
            )
            data_payload = {k: str(v) for k, v in (metadata or {}).items()}

            message = messaging.MulticastMessage(
                notification=notification,
                tokens=device_tokens,
                data=data_payload,
            )

            response = messaging.send_each_for_multicast(message)
            logger.info(
                "push.multicast_sent",
                success=response.success_count,
                failure=response.failure_count,
            )
            return response.success_count, response.failure_count

        except Exception as exc:
            logger.error("push.multicast_failed", error=str(exc))
            return 0, len(device_tokens)


class EHRAlertService:
    """
    In-app EHR alert delivery via Redis Pub/Sub.

    Publishes to a Redis channel that WebSocket consumers subscribe to for
    real-time notification delivery within the HealthOS web/mobile app.
    """

    def __init__(self, redis_url: Optional[str] = None) -> None:
        self._redis_url = redis_url or os.getenv("REDIS_URL", "redis://localhost:6379/0")

    async def send(
        self,
        patient_id: str,
        subject: str,
        body: str,
        *,
        metadata: Optional[dict[str, Any]] = None,
        notification_type: str = "alert",
    ) -> tuple[bool, str]:
        """
        Publish an in-app alert to the patient's Redis channel.

        Returns ``(success, channel_key | error_message)``.
        """
        try:
            import redis.asyncio as aioredis

            r = aioredis.from_url(self._redis_url, decode_responses=True)
            channel = f"ehr_alerts:{patient_id}"
            payload = json.dumps(
                {
                    "type": notification_type,
                    "subject": subject,
                    "body": body,
                    "metadata": metadata or {},
                }
            )
            await r.publish(channel, payload)
            await r.aclose()

            logger.info("ehr_alert.published", patient_id=patient_id, channel=channel)
            return True, f"ehr_pubsub_{patient_id}"

        except Exception as exc:
            logger.error("ehr_alert.publish_failed", error=str(exc))
            return False, str(exc)
