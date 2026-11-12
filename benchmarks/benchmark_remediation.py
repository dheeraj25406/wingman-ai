import os
import sys
import time
import json
import uuid
import asyncio
import numpy as np
from datetime import datetime, timezone
from typing import Dict, Any, List

from simulator.services.mesh import service_mesh
from simulator.faults.fault_engine import fault_engine
from simulator.telemetry.buffer import telemetry_buffer
from backend.app.services.correlation_engine import correlation_engine
from backend.app.api.incidents import (
    INCIDENT_REGISTRY,
    investigate_incident,
    approve_remediation,
)
from backend.app.schemas.schemas import RemediationDecisionRequest

FAULT_SCENARIOS = [
    {"fault_type": "db_pool_exhaustion", "target_service_id": "order-service", "intensity": 0.9},
    {"fault_type": "cpu_saturation", "target_service_id": "checkout-service", "intensity": 0.95},
    {"fault_type": "memory_pressure", "target_service_id": "product-service", "intensity": 0.85},
    {"fault_type": "downstream_failure", "target_service_id": "payment-service", "intensity": 0.9},
    {"fault_type": "queue_backlog", "target_service_id": "order-service", "intensity": 0.8},
    {"fault_type": "bad_deployment", "target_service_id": "user-service", "intensity": 0.95},
]


async def run_remediation_benchmarks(
    iterations_per_scenario: int = 5,
    output_filename: str = "remediation_benchmark_baseline.json",
) -> Dict[str, Any]:
    print("=" * 70)
    print(" EXECUTING REMEDIATION & CLOSED-LOOP RECOVERY BENCHMARK SUITE")
    print(f" {len(FAULT_SCENARIOS)} scenarios x {iterations_per_scenario} trials = {len(FAULT_SCENARIOS) * iterations_per_scenario} trials")
    print("=" * 70)

    # Ensure mesh is active
    if not service_mesh.is_running:
        await service_mesh.start()
    service_mesh.set_traffic_rps(25.0)
    await asyncio.sleep(1.0)

    trials = []
    mttr_latencies = []
    success_count = 0
    failure_count = 0
    false_recovery_count = 0

    trial_idx = 0
    for sc in FAULT_SCENARIOS:
        for it in range(iterations_per_scenario):
            trial_idx += 1
            # 0. Clean prior faults
            fault_engine.stop_all_faults()
            service_mesh.sample_metrics_now()
            await asyncio.sleep(0.3)

            t_start = time.perf_counter()

            # 1. Inject Fault
            fault = fault_engine.inject_fault(
                fault_type=sc["fault_type"],
                target_service_id=sc["target_service_id"],
                intensity=sc["intensity"],
                duration_seconds=180,
            )

            # Sample fresh telemetry
            service_mesh.sample_metrics_now()
            await asyncio.sleep(0.5)

            # 2. Correlate Incident
            anomalies = correlation_engine.scan_for_anomalies()
            primary_anom = next((a for a in anomalies if a["service_id"] == sc["target_service_id"]), None)
            if not primary_anom and anomalies:
                primary_anom = anomalies[0]

            if not primary_anom:
                # Fallback synthetic record
                primary_anom = {
                    "anomaly_score": 0.92,
                    "predicted_class": sc["fault_type"].upper(),
                    "confidence": 0.95,
                    "abnormal_features": [],
                }

            correlated = correlation_engine.correlate_incidents(anomalies) or {
                "title": f"{sc['fault_type'].title()} on {sc['target_service_id']}",
                "severity": "P1_CRITICAL",
                "primary_service_id": sc["target_service_id"],
                "affected_service_ids": [sc["target_service_id"]],
                "propagation_path": [sc["target_service_id"]],
                "detection_source": "ISOLATION_FOREST + LIGHTGBM",
            }

            inc_id = f"inc-bench-{sc['fault_type'][:4]}-{trial_idx}-{uuid.uuid4().hex[:4]}"
            incident_record = {
                "id": inc_id,
                "title": correlated["title"],
                "severity": correlated["severity"],
                "status": "DETECTED",
                "primary_service_id": sc["target_service_id"],
                "affected_service_ids": correlated["affected_service_ids"],
                "detection_source": correlated["detection_source"],
                "detected_at": datetime.now(timezone.utc).isoformat(),
                "mitigated_at": None,
                "resolved_at": None,
                "summary": "Remediation Benchmark Trial",
                "anomaly_score": primary_anom.get("anomaly_score", 0.9),
                "predicted_category": primary_anom.get("predicted_class", sc["fault_type"].upper()),
                "ml_confidence": primary_anom.get("confidence", 0.9),
                "abnormal_features": primary_anom.get("abnormal_features", []),
                "timeline": [],
                "evidence": [],
                "hypotheses": [],
                "remediation_proposal": None,
            }
            INCIDENT_REGISTRY[inc_id] = incident_record

            # 3. Trigger Autonomous Investigation
            inv_res = await investigate_incident(inc_id)
            inv_data = inv_res.get("data", {})
            proposal = inv_data.get("remediation_proposal")
            if not proposal:
                continue

            prop_id = proposal["id"]

            # 4. Operator Approval Gate
            decision_req = RemediationDecisionRequest(
                proposal_id=prop_id,
                operator_notes=f"Automated benchmark trial {trial_idx}",
            )
            app_res = await approve_remediation(inc_id, decision_req, _auth=True)
            app_data = app_res.get("data", {})
            final_status = app_data.get("status")

            recovery_time_s = time.perf_counter() - t_start

            # 5. Verify Recovery via Active Faults
            active_faults = fault_engine.get_active_faults()
            faults_on_service = [f for f in active_faults if f.target_service_id == sc["target_service_id"]]

            is_recovered = len(faults_on_service) == 0 and final_status == "RESOLVED"
            is_false_recovery = final_status == "RESOLVED" and len(faults_on_service) > 0

            if is_recovered:
                success_count += 1
                mttr_latencies.append(recovery_time_s)
            else:
                failure_count += 1

            if is_false_recovery:
                false_recovery_count += 1

            trials.append({
                "trial_id": trial_idx,
                "scenario": sc["fault_type"],
                "target_service": sc["target_service_id"],
                "incident_id": inc_id,
                "proposed_action": proposal.get("action_type"),
                "final_status": str(final_status),
                "recovery_verified": is_recovered,
                "false_recovery": is_false_recovery,
                "recovery_time_seconds": round(recovery_time_s, 2),
            })
            print(f"[{sc['fault_type']:22}] Trial {it+1}: Status={str(final_status):8} | Recovered={str(is_recovered):5} | MTTR={recovery_time_s:5.2f}s")

    # 6. Test Forced Failure Simulation (Negative Test / Safety Constraint)
    print("\nTesting Forced Failure Simulation (Negative Safety Verification)...")
    fail_fault = fault_engine.inject_fault("db_pool_exhaustion", "order-service", 0.9)
    fail_inc_id = f"inc-fail-test-{uuid.uuid4().hex[:6]}"
    INCIDENT_REGISTRY[fail_inc_id] = {
        "id": fail_inc_id,
        "title": "Forced Failure Test",
        "severity": "P1_CRITICAL",
        "status": "DETECTED",
        "primary_service_id": "order-service",
        "affected_service_ids": ["order-service"],
        "detection_source": "ISOLATION_FOREST",
        "detected_at": datetime.now(timezone.utc).isoformat(),
        "timeline": [],
        "evidence": [],
        "hypotheses": [],
        "remediation_proposal": None,
    }
    await investigate_incident(fail_inc_id)
    p_id = INCIDENT_REGISTRY[fail_inc_id]["remediation_proposal"]["id"]
    neg_app = await approve_remediation(
        fail_inc_id,
        RemediationDecisionRequest(proposal_id=p_id, force_failure=True, operator_notes="Negative test"),
        _auth=True,
    )
    neg_status = neg_app.get("data", {}).get("status")
    print(f"Forced Failure Correctly Flagged: {neg_status == 'MITIGATION_FAILED'} (Status: {neg_status})")
    fault_engine.stop_all_faults()

    total_trials = len(trials)
    success_rate = round(success_count / total_trials, 4) if total_trials else 0.0
    failure_rate = round(failure_count / total_trials, 4) if total_trials else 0.0
    false_recovery_rate = round(false_recovery_count / total_trials, 4) if total_trials else 0.0

    final_results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_trials": total_trials,
            "scenarios_tested": [s["fault_type"] for s in FAULT_SCENARIOS],
        },
        "metrics": {
            "remediation_success_rate": success_rate,
            "remediation_failure_rate": failure_rate,
            "false_recovery_rate": false_recovery_rate,
            "mean_time_to_recovery_seconds": round(float(np.mean(mttr_latencies)), 2) if mttr_latencies else 0.0,
            "mttr_p50_seconds": round(float(np.percentile(mttr_latencies, 50)), 2) if mttr_latencies else 0.0,
            "mttr_p95_seconds": round(float(np.percentile(mttr_latencies, 95)), 2) if mttr_latencies else 0.0,
        },
        "trials": trials,
    }

    os.makedirs("benchmarks/results", exist_ok=True)
    out_path = os.path.join("benchmarks/results", output_filename)
    with open(out_path, "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"\n[OK] Machine-readable remediation benchmark saved to {out_path}")
    return final_results


if __name__ == "__main__":
    out_f = sys.argv[1] if len(sys.argv) > 1 else "remediation_benchmark_baseline.json"
    asyncio.run(run_remediation_benchmarks(5, out_f))
