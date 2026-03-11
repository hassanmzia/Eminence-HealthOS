"""
Eminence HealthOS — Audit Middleware
Logs all API requests for HIPAA compliance.
"""

from __future__ import annotations

import time
import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

logger = structlog.get_logger()


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs every API request with timing, user context, and response status."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        request_id = str(uuid.uuid4())
        start = time.monotonic()

        # Attach request_id to request state for downstream use
        request.state.request_id = request_id

        # Extract user info from Authorization header if present
        user_id = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            try:
                from healthos_platform.security.auth import decode_token
                payload = decode_token(auth_header.split(" ", 1)[1])
                user_id = payload.sub
            except Exception:
                pass

        try:
            response = await call_next(request)
        except Exception as exc:
            duration_ms = int((time.monotonic() - start) * 1000)
            logger.error(
                "api.request.error",
                request_id=request_id,
                method=request.method,
                path=request.url.path,
                user_id=user_id,
                duration_ms=duration_ms,
                error=str(exc),
            )
            raise

        duration_ms = int((time.monotonic() - start) * 1000)

        logger.info(
            "api.request",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            user_id=user_id,
            duration_ms=duration_ms,
            client_ip=request.client.host if request.client else "unknown",
        )

        response.headers["X-Request-ID"] = request_id
        return response
