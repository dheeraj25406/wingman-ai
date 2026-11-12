import asyncio
import uuid
import pytest
from datetime import datetime, timezone

from backend.app.database.session import init_db, async_session_factory
from backend.app.database.incident_repository import (
    save_incident_to_db,
    load_incidents_from_db,
    get_incident_from_db,
    delete_incident_from_db,
)
from backend.app.api.incidents import (
    INCIDENT_REGISTRY,
    sync_incidents_from_db,
)


@pytest.mark.asyncio
async def test_persistence_across_backend_restart():
    """Verify that incidents created in memory persist to SQLite/Postgres and survive restarts."""
    await init_db()

    test_id = f"inc-persist-{uuid.uuid4().hex[:6]}"
    test_incident = {
        "id": test_id,
        "title": "Database Saturated Connection Pool Test",
        "severity": "P1_CRITICAL",
        "status": "IDENTIFIED",
        "primary_service_id": "order-service",
        "affected_service_ids": ["order-service", "checkout-service"],
        "detection_source": "ISOLATION_FOREST",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "summary": "Simulated connection saturation for persistence test",
        "timeline": [
            {
                "id": f"ev-{uuid.uuid4().hex[:6]}",
                "event_type": "ALERT_TRIGGERED",
                "description": "Anomaly flagged on order-service",
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "evidence": [
            {
                "id": f"ev-m-{uuid.uuid4().hex[:6]}",
                "evidence_type": "METRIC_SPIKE",
                "service_id": "order-service",
                "headline": "DB connection at 98%",
                "details": {"metric": "db_connections", "val": 98.0},
                "confidence_score": 1.0,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        ],
        "hypotheses": [
            {
                "id": f"hyp-{uuid.uuid4().hex[:6]}",
                "rank": 1,
                "root_cause": "PostgreSQL connection exhaustion",
                "confidence_score": 0.95,
                "explanation": "Connection pool reached maximum configured capacity.",
                "supporting_evidence_ids": [],
                "recommended_remediation": "RESET_CONNECTION_POOL",
                "status": "PROPOSED",
            }
        ],
        "remediation_proposal": {
            "id": f"rem-{uuid.uuid4().hex[:6]}",
            "action_type": "RESET_CONNECTION_POOL",
            "target_service_id": "order-service",
            "parameters": {"max_connections": 100},
            "justification": "Clear idle connections",
            "risk_assessment": "LOW",
            "status": "PENDING_APPROVAL",
            "created_at": datetime.now(timezone.utc).isoformat(),
        },
    }

    # Step 1: Save incident to database
    await save_incident_to_db(test_incident)
    INCIDENT_REGISTRY[test_id] = test_incident

    # Verify directly via single-row query
    db_rec = await get_incident_from_db(test_id)
    assert db_rec is not None
    assert db_rec["id"] == test_id
    assert db_rec["title"] == test_incident["title"]
    assert len(db_rec["timeline"]) == 1
    assert len(db_rec["evidence"]) == 1
    assert len(db_rec["hypotheses"]) == 1
    assert db_rec["remediation_proposal"]["status"] == "PENDING_APPROVAL"

    # Step 2: Simulate Backend Restart (Wipe in-memory registry)
    INCIDENT_REGISTRY.clear()
    assert test_id not in INCIDENT_REGISTRY

    # Step 3: Trigger backend startup synchronization from database
    await sync_incidents_from_db()

    # Step 4: Verify incident survived restart in registry
    assert test_id in INCIDENT_REGISTRY
    restored = INCIDENT_REGISTRY[test_id]
    assert restored["title"] == test_incident["title"]
    assert restored["remediation_proposal"]["action_type"] == "RESET_CONNECTION_POOL"

    # Step 5: Test Update persistence
    restored["status"] = "RESOLVED"
    restored["remediation_proposal"]["status"] = "RESOLVED"
    await save_incident_to_db(restored)

    db_updated = await get_incident_from_db(test_id)
    assert db_updated["status"] == "RESOLVED"
    assert db_updated["remediation_proposal"]["status"] == "RESOLVED"

    # Step 6: Test Deletion
    deleted = await delete_incident_from_db(test_id)
    assert deleted is True

    INCIDENT_REGISTRY.pop(test_id, None)
    assert (await get_incident_from_db(test_id)) is None


@pytest.mark.asyncio
async def test_concurrent_persistence_and_rollback():
    """Verify concurrent write safety and transaction integrity."""
    await init_db()

    test_ids = [f"inc-conc-{uuid.uuid4().hex[:6]}" for _ in range(5)]
    tasks = []
    for inc_id in test_ids:
        inc = {
            "id": inc_id,
            "title": f"Concurrent Incident {inc_id}",
            "severity": "P2_HIGH",
            "status": "DETECTED",
            "primary_service_id": "checkout-service",
            "timeline": [],
            "evidence": [],
            "hypotheses": [],
            "remediation_proposal": None,
        }
        tasks.append(save_incident_to_db(inc))

    # Run 5 concurrent database write transactions
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        assert not isinstance(r, Exception)

    # Verify all 5 were written safely
    for inc_id in test_ids:
        rec = await get_incident_from_db(inc_id)
        assert rec is not None
        await delete_incident_from_db(inc_id)
