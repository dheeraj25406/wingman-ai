import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app
from backend.app.core.config import settings
from backend.app.core.security import rate_limiter


@pytest.mark.asyncio
async def test_security_headers_applied():
    """Verify enterprise security headers are injected on all HTTP responses."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/health")
        assert resp.status_code == 200
        assert resp.headers.get("X-Content-Type-Options") == "nosniff"
        assert resp.headers.get("X-Frame-Options") == "DENY"
        assert resp.headers.get("X-XSS-Protection") == "1; mode=block"
        assert "X-RateLimit-Remaining" in resp.headers


@pytest.mark.asyncio
async def test_public_endpoints_accessible_without_auth():
    """Verify telemetry & discovery endpoints are accessible in read-only mode."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for path in ["/api/health", "/api/health/ready", "/api/services", "/api/metrics/overview", "/api/incidents"]:
            resp = await client.get(path)
            assert resp.status_code == 200, f"Endpoint {path} failed: {resp.status_code}"


@pytest.mark.asyncio
async def test_admin_authorization_gate():
    """Verify ADMIN_API_KEY protects sensitive mutations when configured."""
    original_key = settings.ADMIN_API_KEY
    try:
        # Enforce admin authentication
        settings.ADMIN_API_KEY = "test_super_secret_admin_key"

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # Attempt approval without header -> Must be 401 Unauthorized
            unauth_resp = await client.post(
                "/api/incidents/inc-test/approve",
                json={"proposal_id": "rem-1", "operator_notes": "Attempt without token"},
            )
            assert unauth_resp.status_code == 401

            # Attempt approval with invalid header -> Must be 401 Unauthorized
            wrong_resp = await client.post(
                "/api/incidents/inc-test/approve",
                headers={"X-Wingman-Auth": "wrong_token"},
                json={"proposal_id": "rem-1", "operator_notes": "Attempt with wrong token"},
            )
            assert wrong_resp.status_code == 401

            # Attempt with valid header -> Authenticated (will be 404 for nonexistent incident, not 401)
            auth_resp = await client.post(
                "/api/incidents/inc-test/approve",
                headers={"X-Wingman-Auth": "test_super_secret_admin_key"},
                json={"proposal_id": "rem-1", "operator_notes": "Attempt with valid token"},
            )
            assert auth_resp.status_code == 404
    finally:
        settings.ADMIN_API_KEY = original_key


@pytest.mark.asyncio
async def test_rate_limiting_enforcement():
    """Verify client IP rate limiter throttles excessive requests."""
    client_ip = "192.168.1.100"
    rate_limiter.sensitive_requests.clear()

    # Fill bucket to sensitive limit (20 req/min)
    for _ in range(settings.RATE_LIMIT_SENSITIVE_PER_MINUTE):
        allowed, remaining, _ = rate_limiter.is_allowed(client_ip, is_sensitive=True)
        assert allowed is True

    # 21st request must be denied with retry_after
    allowed, remaining, retry_after = rate_limiter.is_allowed(client_ip, is_sensitive=True)
    assert allowed is False
    assert remaining == 0
    assert retry_after > 0


@pytest.mark.asyncio
async def test_production_fail_closed_without_admin_key():
    """Verify that in production mode, missing ADMIN_API_KEY fails closed (HTTP 500 config error)."""
    orig_env = settings.ENVIRONMENT
    orig_key = settings.ADMIN_API_KEY
    orig_demo = settings.PUBLIC_DEMO_MODE
    try:
        settings.ENVIRONMENT = "production"
        settings.ADMIN_API_KEY = ""
        settings.PUBLIC_DEMO_MODE = False

        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/incidents/inc-test/approve",
                json={"proposal_id": "rem-1", "operator_notes": "Attempt in unconfigured prod"},
            )
            assert resp.status_code == 500
            assert "Administrator authentication key is not configured" in resp.json()["detail"]
    finally:
        settings.ENVIRONMENT = orig_env
        settings.ADMIN_API_KEY = orig_key
        settings.PUBLIC_DEMO_MODE = orig_demo


@pytest.mark.asyncio
async def test_destructive_admin_authorization_blocked_in_demo_mode():
    """Verify that updating API keys is strictly blocked in unauthenticated demo mode."""
    orig_key = settings.ADMIN_API_KEY
    try:
        settings.ADMIN_API_KEY = ""
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            resp = await client.post(
                "/api/settings/api-key",
                json={"api_key": "fake_gemini_api_key_test_token"},
            )
            assert resp.status_code == 403
            assert "disabled in unauthenticated demo mode" in resp.json()["detail"]
    finally:
        settings.ADMIN_API_KEY = orig_key


@pytest.mark.asyncio
async def test_rate_limit_reverse_proxy_x_real_ip():
    """Verify rate limiter extracts client IP from trusted X-Real-IP reverse proxy header."""
    transport = ASGITransport(app=app)
    proxy_ip = "203.0.113.195"
    rate_limiter.sensitive_requests.clear()

    async with AsyncClient(transport=transport, base_url="http://test") as client:
        for _ in range(settings.RATE_LIMIT_SENSITIVE_PER_MINUTE):
            resp = await client.post(
                "/api/faults/inject",
                headers={"X-Real-IP": proxy_ip},
                json={"fault_type": "db_pool_exhaustion", "target_service_id": "order-service", "intensity": 0.5, "duration_seconds": 10},
            )
            assert resp.status_code in (200, 400)

        # Next request must be throttled by IP from X-Real-IP
        throttled = await client.post(
            "/api/faults/inject",
            headers={"X-Real-IP": proxy_ip},
            json={"fault_type": "db_pool_exhaustion", "target_service_id": "order-service", "intensity": 0.5, "duration_seconds": 10},
        )
        assert throttled.status_code == 429
        assert "Retry-After" in throttled.headers


@pytest.mark.asyncio
async def test_stop_all_faults_and_investigate_protected():
    """Verify stop-all faults and incident investigation endpoints are protected by admin auth."""
    original_key = settings.ADMIN_API_KEY
    try:
        settings.ADMIN_API_KEY = "test_admin_auth_token_secret"
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            # 1. stop-all without auth
            res_stop = await client.post("/api/faults/stop-all")
            assert res_stop.status_code == 401

            # 2. investigate without auth
            res_inv = await client.post("/api/incidents/inc-test-123/investigate")
            assert res_inv.status_code == 401

            # 3. stop-all with valid auth
            res_stop_auth = await client.post(
                "/api/faults/stop-all",
                headers={"X-Wingman-Auth": "test_admin_auth_token_secret"},
            )
            assert res_stop_auth.status_code == 200

            # 4. investigate with valid auth (404 because inc-test-123 doesn't exist, but passes auth)
            res_inv_auth = await client.post(
                "/api/incidents/inc-test-123/investigate",
                headers={"X-Wingman-Auth": "test_admin_auth_token_secret"},
            )
            assert res_inv_auth.status_code == 404
    finally:
        settings.ADMIN_API_KEY = original_key
