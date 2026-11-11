import pytest
from httpx import AsyncClient, ASGITransport
from backend.app.main import app


@pytest.mark.asyncio
async def test_health_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "components" in data


@pytest.mark.asyncio
async def test_services_endpoint():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/services")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 5


@pytest.mark.asyncio
async def test_metrics_overview():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/metrics/overview")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "total_services" in data["data"]


@pytest.mark.asyncio
async def test_incidents_list():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/api/incidents")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 1


@pytest.mark.asyncio
async def test_fault_injection_lifecycle():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        # 1. Inject fault
        inject_res = await ac.post("/api/faults/inject", json={
            "fault_type": "db_pool_exhaustion",
            "target_service_id": "order-service",
            "intensity": 0.8,
            "duration_seconds": 60,
        })
        assert inject_res.status_code == 200
        fault_id = inject_res.json()["data"]["fault_id"]

        # 2. Check active faults
        list_res = await ac.get("/api/faults")
        assert list_res.status_code == 200
        active_ids = [f["id"] for f in list_res.json()["data"]["active_faults"]]
        assert fault_id in active_ids

        # 3. Stop fault
        stop_res = await ac.post(f"/api/faults/{fault_id}/stop")
        assert stop_res.status_code == 200
