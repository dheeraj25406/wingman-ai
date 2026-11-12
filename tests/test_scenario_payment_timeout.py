import asyncio
import time
from datetime import datetime, timezone

from simulator.services.mesh import service_mesh
from simulator.faults.fault_engine import fault_engine
from simulator.telemetry.buffer import telemetry_buffer
from backend.app.services.correlation_engine import correlation_engine
from backend.app.api.incidents import INCIDENT_REGISTRY, investigate_incident, approve_remediation
from backend.app.schemas.schemas import RemediationDecisionRequest


async def run_payment_timeout_scenario():
    print("=" * 80)
    print(" WINGMAN AI — PAYMENT GATEWAY TIMEOUT SCENARIO TEST")
    print("=" * 80)

    # 1. Start application simulator & background traffic
    await service_mesh.start()
    service_mesh.set_traffic_rps(15.0)
    await asyncio.sleep(2.0)

    # 2. Inject downstream latency fault on payment-service
    print("\n[STEP 1] Injecting downstream_latency fault on payment-service...")
    fault = fault_engine.inject_fault(
        fault_type="downstream_latency",
        target_service_id="payment-service",
        intensity=0.85,
        duration_seconds=120,
    )
    assert fault is not None
    print(f"Fault active: {fault.id} ({fault.expected_root_cause})")

    # Let telemetry accumulate
    await asyncio.sleep(3.0)

    # 3. Detect anomalies
    print("\n[STEP 2] Running Isolation Forest anomaly detector...")
    anomalies = correlation_engine.scan_for_anomalies()
    print(f"Detected {len(anomalies)} anomalies across mesh.")
    assert len(anomalies) > 0

    # 4. Supervised classification
    payment_anom = next((a for a in anomalies if a["service_id"] == "payment-service"), anomalies[0])
    print(f"Predicted Class: {payment_anom['predicted_class']} (Confidence: {payment_anom['confidence']:.2%})")

    # 5. Correlation
    print("\n[STEP 3] Correlating into single incident...")
    correlated = correlation_engine.correlate_incidents(anomalies)
    assert correlated is not None
    print(f"Incident: {correlated['title']} (Severity: {correlated['severity']})")

    # 6. Autonomous LangGraph Investigation
    print("\n[STEP 4] Executing LangGraph autonomous investigation...")
    inc_id = f"inc-pay-{int(time.time())}"
    INCIDENT_REGISTRY[inc_id] = {
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
        "summary": "Payment Service Degradation",
        "anomaly_score": payment_anom["anomaly_score"],
        "predicted_category": payment_anom["predicted_class"],
        "ml_confidence": payment_anom["confidence"],
        "abnormal_features": payment_anom["abnormal_features"],
        "timeline": [],
        "evidence": [],
        "hypotheses": [],
        "remediation_proposal": None,
    }

    inv_res = await investigate_incident(inc_id)
    inv_data = inv_res["data"]
    top_hyp = inv_data["hypotheses"][0]
    print(f"Top Hypothesis: {top_hyp['root_cause']}")
    print(f"Confidence: {top_hyp['confidence_score']:.2%}")
    print(f"Evidence citations: {top_hyp['supporting_evidence_ids']}")

    # 7. Remediation
    proposal = inv_data["remediation_proposal"]
    assert proposal is not None
    print(f"\n[STEP 5] Proposed Remediation: {proposal['action_type']} on {proposal['target_service_id']}")

    decision = RemediationDecisionRequest(
        proposal_id=proposal["id"],
        operator_notes="Approved payment service circuit breaker & restart.",
    )
    approve_res = await approve_remediation(inc_id, decision)
    assert approve_res["data"]["status"] == "RESOLVED"
    print(f"Incident status after approval: {approve_res['data']['status']}")

    # Clean up
    fault_engine.stop_all_faults()
    await service_mesh.stop()
    print("\n[OK] Payment scenario completed and verified successfully!")


if __name__ == "__main__":
    asyncio.run(run_payment_timeout_scenario())
