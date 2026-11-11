import asyncio
import time
from datetime import datetime, timezone

from simulator.services.mesh import service_mesh
from simulator.faults.fault_engine import fault_engine
from simulator.telemetry.buffer import telemetry_buffer
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier
from backend.app.services.correlation_engine import correlation_engine
from backend.app.api.incidents import INCIDENT_REGISTRY, investigate_incident, approve_remediation
from backend.app.schemas.schemas import RemediationDecisionRequest


async def run_end_to_end_scenario():
    print("=" * 80)
    print(" WINGMAN AI — END-TO-END SYSTEM INTEGRATION VERIFICATION")
    print("=" * 80)

    # 1. Start application simulator & background traffic
    print("\n[STEP 1] Starting application simulator mesh & traffic generator...")
    await service_mesh.start()
    service_mesh.set_traffic_rps(20.0)

    # Wait 2 seconds for initial normal telemetry
    await asyncio.sleep(2.0)
    latest = telemetry_buffer.get_all_latest_metrics()
    print(f"[STEP 1 OK] Telemetry flowing across {len(latest)} services. Normal traffic established.")

    # 2. Inject fault: Database connection pool exhaustion
    print("\n[STEP 2] Injecting Fault: 'db_pool_exhaustion' on order-service (intensity: 0.9)...")
    fault = fault_engine.inject_fault(
        fault_type="db_pool_exhaustion",
        target_service_id="order-service",
        intensity=0.9,
        duration_seconds=120,
    )
    print(f"[STEP 2 OK] Fault active (ID: {fault.id}). Expected cause: {fault.expected_root_cause}")

    # Wait for telemetry to register fault degradation
    await asyncio.sleep(3.0)

    # 3. Anomaly Scan (Isolation Forest)
    print("\n[STEP 3] Running telemetry anomaly scan via Isolation Forest...")
    anomalies = correlation_engine.scan_for_anomalies()
    assert len(anomalies) > 0, "Expected at least one anomaly signal to be detected"
    print(f"[STEP 3 OK] Detected {len(anomalies)} anomalous services. Anomaly score: {anomalies[0]['anomaly_score']:.4f}")

    # 4. LightGBM Supervised Classification
    print("\n[STEP 4] Evaluating LightGBM incident classification...")
    primary_anom = next((a for a in anomalies if a["service_id"] == "order-service"), anomalies[0])
    pred_class = primary_anom["predicted_class"]
    confidence = primary_anom["confidence"]
    print(f"[STEP 4 OK] Predicted incident class: {pred_class} (Confidence: {confidence:.2%})")
    assert pred_class == "DB_POOL_EXHAUSTION"

    # 5. Deterministic Incident Correlation
    print("\n[STEP 5] Deterministic Correlation Engine: graph traversal & alert grouping...")
    correlated = correlation_engine.correlate_incidents(anomalies)
    assert correlated is not None
    print(f"[STEP 5 OK] Correlated Incident: '{correlated['title']}'")
    print(f"         Primary Service: {correlated['primary_service_id']}")
    print(f"         Propagation Path: {' -> '.join(correlated['propagation_path'])}")

    # 6. Incident Creation & LangGraph Autonomous Investigation
    print("\n[STEP 6] Triggering 16-node LangGraph investigation workflow...")
    inc_id = f"inc-e2e-{int(time.time())}"
    incident_record = {
        "id": inc_id,
        "title": correlated["title"],
        "severity": correlated["severity"],
        "status": "DETECTED",
        "primary_service_id": correlated["primary_service_id"],
        "affected_service_ids": correlated["affected_service_ids"],
        "detection_source": correlated["detection_source"],
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "mitigated_at": None,
        "resolved_at": None,
        "summary": "E2E Test Incident",
        "anomaly_score": primary_anom["anomaly_score"],
        "predicted_category": primary_anom["predicted_class"],
        "ml_confidence": primary_anom["confidence"],
        "abnormal_features": primary_anom["abnormal_features"],
        "timeline": [],
        "evidence": [],
        "hypotheses": [],
        "remediation_proposal": None,
    }
    INCIDENT_REGISTRY[inc_id] = incident_record

    investigate_res = await investigate_incident(inc_id)
    inv_data = investigate_res["data"]
    print(f"[STEP 6 OK] LangGraph investigation completed.")
    print(f"         Evidence Collected: {len(inv_data['evidence'])} verified artifacts")
    print(f"         Top Root-Cause Hypothesis: {inv_data['hypotheses'][0]['root_cause']}")
    print(f"         Confidence: {inv_data['hypotheses'][0]['confidence_score']:.2%}")
    print(f"         Supporting Evidence: {inv_data['hypotheses'][0]['supporting_evidence_ids']}")

    # 7. Remediation Proposal & Human Approval Gate
    print("\n[STEP 7] Inspecting proposed remediation and executing Human Approval Gate...")
    proposal = inv_data["remediation_proposal"]
    assert proposal is not None
    print(f"         Action: {proposal['action_type']} on {proposal['target_service_id']}")
    print(f"         Risk Assessment: {proposal['risk_assessment']}")

    decision_req = RemediationDecisionRequest(
        proposal_id=proposal["id"],
        operator_notes="Approved automated recovery procedure in integration verification."
    )
    approve_res = await approve_remediation(inc_id, decision_req)
    resolved_inc = approve_res["data"]
    print(f"[STEP 7 OK] Human operator approval registered. Remediation status: {resolved_inc['status']}")
    assert resolved_inc["status"] == "RESOLVED"

    # 8. Post-Remediation Telemetry Recovery Verification
    print("\n[STEP 8] Verifying post-remediation recovery...")
    active_faults = fault_engine.get_active_faults()
    print(f"[STEP 8 OK] Active faults remaining: {len(active_faults)}")
    assert len(active_faults) == 0

    await service_mesh.stop()
    print("\n" + "=" * 80)
    print(" ALL 8 PHASES OF ACCEPTANCE SCENARIO PASSED SUCCESSFULLY!")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(run_end_to_end_scenario())
