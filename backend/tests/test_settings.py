import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_get_integration_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/settings/integrations")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "gemini" in data["data"]
        assert "observability" in data["data"]
        assert "safety" in data["data"]


@pytest.mark.asyncio
async def test_traffic_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get traffic
        res = await client.get("/api/settings/traffic")
        assert res.status_code == 200

        # Update traffic
        res_post = await client.post("/api/settings/traffic", json={"rps": 18.0})
        assert res_post.status_code == 200
        assert res_post.json()["data"]["target_rps"] == 18.0


@pytest.mark.asyncio
async def test_safety_settings():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/settings/safety")
        assert res.status_code == 200

        res_update = await client.post(
            "/api/settings/safety",
            json={
                "human_approval_required": True,
                "max_remediations_per_hour": 15,
                "allowed_actions": ["RESTART_SERVICE", "RESET_CONNECTION_POOL"],
            },
        )
        assert res_update.status_code == 200
        assert res_update.json()["data"]["max_remediations_per_hour"] == 15


@pytest.mark.asyncio
async def test_system_diagnostics():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.get("/api/settings/system-diagnostics")
        assert res.status_code == 200
        data = res.json()["data"]
        assert "subsystems" in data
        assert len(data["subsystems"]) >= 5


@pytest.mark.asyncio
async def test_reset_demo():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post("/api/settings/reset-demo")
        assert res.status_code == 200
        assert "reset to baseline" in res.json()["message"]
