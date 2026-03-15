"""
Eminence HealthOS — Security Headers Middleware
Adds OWASP-recommended security headers to all responses.
"""

from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


# Security headers for healthcare/HIPAA compliance
SECURITY_HEADERS = {
    # Prevent XSS reflection
    "X-Content-Type-Options": "nosniff",
    # Prevent clickjacking
    "X-Frame-Options": "DENY",
    # XSS filter (legacy browsers)
    "X-XSS-Protection": "1; mode=block",
    # Referrer policy — don't leak patient URLs
    "Referrer-Policy": "strict-origin-when-cross-origin",
    # Permissions policy — disable unnecessary browser features
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
    # Content Security Policy
    "Content-Security-Policy": (
        "default-src 'self'; "
        "script-src 'self'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:; "
        "font-src 'self'; "
        "connect-src 'self'; "
        "frame-ancestors 'none'; "
        "base-uri 'self'; "
        "form-action 'self'"
    ),
    # HSTS — enforce HTTPS (1 year, include subdomains)
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains; preload",
    # Prevent MIME-type sniffing
    "Cache-Control": "no-store, no-cache, must-revalidate, private",
    # Prevent caching of PHI responses
    "Pragma": "no-cache",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Adds OWASP security headers to all API responses."""

    def __init__(self, app, extra_headers: dict[str, str] | None = None):
        super().__init__(app)
        self.headers = {**SECURITY_HEADERS}
        if extra_headers:
            self.headers.update(extra_headers)

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint
    ) -> Response:
        response = await call_next(request)

        for header, value in self.headers.items():
            response.headers[header] = value

        # Remove server identification header
        if "server" in response.headers:
            del response.headers["server"]

        return response
