"""
Request tracing middleware.

Assigns trace IDs and records request timing for observability.
"""

import logging
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("healthos.middleware.tracing")


class TracingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Response-Time-Ms"] = str(duration_ms)

        if not request.url.path.startswith(("/docs", "/openapi", "/health")):
            logger.info(
                "%s %s %d %dms tenant=%s trace=%s",
                request.method,
                request.url.path,
                response.status_code,
                duration_ms,
                getattr(request.state, "tenant_id", "?"),
                trace_id[:12],
            )

        return response
