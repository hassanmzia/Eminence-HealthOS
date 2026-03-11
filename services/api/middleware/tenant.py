"""
Multi-tenant middleware.

Extracts tenant_id from X-Tenant-ID header (or JWT claims) and
injects it into request state for downstream use.
"""

import logging

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from platform.config.settings import get_settings

logger = logging.getLogger("healthos.middleware.tenant")


class TenantMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        settings = get_settings()

        # Extract tenant from header
        tenant_id = request.headers.get(
            settings.tenant_header, settings.default_tenant_id
        )

        # Store in request state for downstream access
        request.state.tenant_id = tenant_id

        response = await call_next(request)
        response.headers["X-Tenant-ID"] = tenant_id
        return response


def get_tenant_id(request: Request) -> str:
    """FastAPI dependency to extract tenant_id from request."""
    return getattr(request.state, "tenant_id", get_settings().default_tenant_id)
