import time
import logging
import secrets
from collections import defaultdict
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse, Response

from backend.app.core.config import settings

logger = logging.getLogger("wingman.security")


class InMemoryRateLimiter:
    """
    Sliding window in-memory rate limiter per client IP address.
    Tracks general requests and sensitive mutating endpoints separately.
    """

    def __init__(self):
        # Maps client_ip -> list of epoch timestamps
        self.general_requests: Dict[str, List[float]] = defaultdict(list)
        self.sensitive_requests: Dict[str, List[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str, is_sensitive: bool = False) -> Tuple[bool, int, int]:
        """
        Returns (is_allowed, remaining_limit, retry_after_seconds).
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, 999, 0

        now = time.time()
        window_start = now - 60.0

        limit = (
            settings.RATE_LIMIT_SENSITIVE_PER_MINUTE
            if is_sensitive
            else settings.RATE_LIMIT_PER_MINUTE
        )
        bucket = (
            self.sensitive_requests[client_ip]
            if is_sensitive
            else self.general_requests[client_ip]
        )

        # Evict timestamps older than 60 seconds
        valid_timestamps = [t for t in bucket if t > window_start]
        bucket.clear()
        bucket.extend(valid_timestamps)

        if len(bucket) >= limit:
            oldest = bucket[0]
            retry_after = max(1, int(60.0 - (now - oldest)))
            return False, 0, retry_after

        bucket.append(now)
        remaining = max(0, limit - len(bucket))
        return True, remaining, 0


rate_limiter = InMemoryRateLimiter()


class SecurityMiddleware(BaseHTTPMiddleware):
    """
    Applies security response headers and IP-based rate limiting behind reverse proxies.
    """

    SENSITIVE_PREFIXES = (
        "/api/incidents/",  # /approve, /reject, /investigate
        "/api/faults/inject",
        "/api/settings/api-key",
        "/api/settings/safety",
        "/api/settings/traffic",
        "/api/models/train",
        "/api/evaluations/run",
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        # 1. Skip rate limiting for static assets or OpenAPI documentation
        path = request.url.path
        if not path.startswith("/api"):
            response = await call_next(request)
            self._apply_security_headers(response)
            return response

        # 2. Extract trusted client IP (prefer X-Real-IP set by Nginx reverse proxy)
        real_ip = request.headers.get("X-Real-IP")
        forwarded = request.headers.get("X-Forwarded-For")
        client_ip = (
            real_ip.strip()
            if real_ip
            else (forwarded.split(",")[0].strip() if forwarded else (request.client.host if request.client else "unknown"))
        )

        is_sensitive = (
            request.method in ("POST", "PUT", "DELETE")
            and any(path.startswith(prefix) for prefix in self.SENSITIVE_PREFIXES)
        )

        allowed, remaining, retry_after = rate_limiter.is_allowed(client_ip, is_sensitive=is_sensitive)
        if not allowed:
            logger.warning(f"Rate limit exceeded for IP {client_ip} on {path}")
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "status": "error",
                    "detail": "Rate limit exceeded. Please wait before making more requests.",
                    "retry_after_seconds": retry_after,
                },
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Remaining": "0",
                },
            )

        response: Response = await call_next(request)

        # 3. Apply standard enterprise security headers
        self._apply_security_headers(response)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response

    def _apply_security_headers(self, response: Response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        if settings.ENVIRONMENT == "production":
            response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"


def _extract_token(request: Request) -> str:
    auth_header = request.headers.get("Authorization", "")
    custom_header = request.headers.get("X-Wingman-Auth", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    if custom_header:
        return custom_header.strip()
    return ""


async def verify_admin_authorization(request: Request):
    """
    Validates administrative authentication.
    - In production: Fails closed. Mandatory ADMIN_API_KEY unless PUBLIC_DEMO_MODE=True.
    - Constant-time secret comparison prevents timing attacks.
    """
    admin_key = settings.ADMIN_API_KEY.strip() if settings.ADMIN_API_KEY else ""

    # In production mode without demo flag, admin key is strictly required
    if settings.ENVIRONMENT == "production" and not settings.PUBLIC_DEMO_MODE and not admin_key:
        logger.error("Production server configuration error: ADMIN_API_KEY is not configured.")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Server configuration error: Administrator authentication key is not configured.",
        )

    # In public demo mode or local dev without configured key, allow safe demo actions
    if not admin_key and (settings.PUBLIC_DEMO_MODE or settings.ENVIRONMENT != "production"):
        return True

    # If key is configured, strictly enforce constant-time check
    token = _extract_token(request)
    if not token or not secrets.compare_digest(token, admin_key):
        logger.warning(f"Unauthorized administrative access attempt on {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid authorization token (X-Wingman-Auth or Authorization: Bearer <key>) required.",
        )

    return True


async def verify_destructive_admin_authorization(request: Request):
    """
    Strictly requires ADMIN_API_KEY for destructive changes (e.g. updating Gemini keys),
    even in public demo mode.
    """
    admin_key = settings.ADMIN_API_KEY.strip() if settings.ADMIN_API_KEY else ""
    if not admin_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Destructive administrative operations are disabled in unauthenticated demo mode.",
        )

    token = _extract_token(request)
    if not token or not secrets.compare_digest(token, admin_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Valid administrator key required for this operation.",
        )

    return True
