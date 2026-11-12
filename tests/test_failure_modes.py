from datetime import datetime, timezone
import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch, AsyncMock
from sqlalchemy.ext.asyncio import AsyncEngine

from backend.app.main import app
from agent.tools.gemini_service import gemini_service
from agent.graph.investigation_graph import node_hypothesis_generation
from agent.state.investigation_state import InvestigationStateDict


@pytest.mark.asyncio
async def test_health_and_readiness_probes():
    """Verify liveness and readiness endpoints return appropriate HTTP status codes."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Liveness Probe
        live_res = await client.get("/api/health/live")
        assert live_res.status_code == 200
        assert live_res.json()["status"] == "healthy"

        # 2. Readiness Probe (healthy DB)
        ready_res = await client.get("/api/health/ready")
        assert ready_res.status_code == 200
        assert ready_res.json()["status"] == "ready"
        assert ready_res.json()["database"] == "connected"


@pytest.mark.asyncio
async def test_readiness_probe_database_failure():
    """Verify readiness returns HTTP 503 when database connectivity is severed."""
    transport = ASGITransport(app=app)
    with patch.object(AsyncEngine, "connect", side_effect=Exception("Database connection timeout")):
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            ready_res = await client.get("/api/health/ready")
            assert ready_res.status_code == 503
            assert ready_res.json()["status"] == "not_ready"
            assert ready_res.json()["database"] == "disconnected"


def test_gemini_api_failure_fallback():
    """Verify that an investigation never fails even if Gemini API throws an exception or network outage occurs."""
    mock_state = InvestigationStateDict(
        incident_id="inc-mock-fail",
        title="Mock Anomaly for Failure Mode Test",
        severity="P1_CRITICAL",
        primary_service_id="order-service",
        affected_service_ids=["order-service"],
        anomaly_score=0.92,
        predicted_category="DB_POOL_EXHAUSTION",
        ml_confidence=0.95,
        detected_at=datetime.now(timezone.utc).isoformat(),
        abnormal_features=[{"feature": "db_connections", "value": 99.0}],
        evidence_ids=["ev-test-1"],
    )

    # Force generate_structured_hypotheses to throw a network/timeout exception
    with patch.object(gemini_service, "generate_structured_hypotheses", side_effect=RuntimeError("Google API 503 Service Unavailable")):
        result = node_hypothesis_generation(mock_state)
        assert "hypotheses" in result
        assert len(result["hypotheses"]) > 0
        top_hyp = result["hypotheses"][0]
        assert "PostgreSQL database connection pool exhaustion" in top_hyp.root_cause
        assert top_hyp.confidence_score >= 0.85
        assert result["current_node"] == "HYPOTHESIS_GENERATION"


@pytest.mark.asyncio
async def test_duplicate_remediation_approval_and_rejection():
    """Verify that duplicate approval or rejection of an executed/resolved incident is rejected with HTTP 400."""
    from backend.app.api.incidents import INCIDENT_REGISTRY
    from backend.app.database.session import init_db

    await init_db()

    inc_id = "inc-dup-test-01"
    INCIDENT_REGISTRY[inc_id] = {
        "id": inc_id,
        "title": "Duplicate Approval Failure Test",
        "severity": "P1_CRITICAL",
        "status": "IDENTIFIED",
        "primary_service_id": "order-service",
        "affected_service_ids": ["order-service"],
        "detection_source": "ISOLATION_FOREST",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "summary": "Testing duplicate approval rejection",
        "timeline": [],
        "evidence": [],
        "hypotheses": [],
        "remediation_proposal": {
            "id": "prop-dup-01",
            "action_type": "RESET_CONNECTION_POOL",
            "target_service_id": "order-service",
            "parameters": {},
            "status": "PENDING",
            "justification": "Test proposal",
        },
    }

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # First approval succeeds
        app_res1 = await client.post(
            f"/api/incidents/{inc_id}/approve",
            json={"proposal_id": "prop-dup-01", "operator_notes": "First approval"},
        )
        assert app_res1.status_code == 200
        assert app_res1.json()["status"] == "success"

        # Second approval must fail with 400 Bad Request
        app_res2 = await client.post(
            f"/api/incidents/{inc_id}/approve",
            json={"proposal_id": "prop-dup-01", "operator_notes": "Duplicate approval attempt"},
        )
        assert app_res2.status_code == 400
        assert "already been approved/executed" in app_res2.json()["detail"]

        # Rejection of already resolved/executed proposal must also fail with 400 Bad Request
        rej_res = await client.post(
            f"/api/incidents/{inc_id}/reject",
            json={"proposal_id": "prop-dup-01", "operator_notes": "Attempt to reject resolved"},
        )
        assert rej_res.status_code == 400
        assert "already been decided" in rej_res.json()["detail"]
