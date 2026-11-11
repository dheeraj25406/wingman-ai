import time
import uuid
from typing import List, Dict, Any

from agent.state.investigation_state import InvestigationStateDict
from agent.graph.investigation_graph import investigation_graph
from simulator.faults.fault_engine import FaultEngine


BENCHMARK_SCENARIOS = [
    {
        "name": "Order Service DB Pool Starvation",
        "fault_type": "db_pool_exhaustion",
        "primary_service": "order-service",
        "affected_services": ["order-service", "checkout-service", "api-gateway"],
        "expected_root_cause": "connection pool",
        "acceptable_remediations": ["RESET_CONNECTION_POOL", "RESTART_SERVICE"],
        "abnormal_features": [{"feature": "db_connections", "value": 99.0, "deviation_sigma": 4.5}],
        "anomaly_score": 0.88,
        "predicted_category": "DB_POOL_EXHAUSTION",
        "ml_confidence": 0.96,
    },
    {
        "name": "Checkout Service CPU Throttling",
        "fault_type": "cpu_saturation",
        "primary_service": "checkout-service",
        "affected_services": ["checkout-service", "api-gateway"],
        "expected_root_cause": "compute",
        "acceptable_remediations": ["RESTART_SERVICE", "THROTTLE_TRAFFIC"],
        "abnormal_features": [{"feature": "cpu_utilization", "value": 98.0, "deviation_sigma": 4.2}],
        "anomaly_score": 0.85,
        "predicted_category": "CPU_SATURATION",
        "ml_confidence": 0.94,
    },
    {
        "name": "Payment Service 503 Provider Outage",
        "fault_type": "downstream_failure",
        "primary_service": "payment-service",
        "affected_services": ["payment-service", "checkout-service", "api-gateway"],
        "expected_root_cause": "payment",
        "acceptable_remediations": ["RESTART_SERVICE"],
        "abnormal_features": [{"feature": "error_rate", "value": 0.85, "deviation_sigma": 5.1}],
        "anomaly_score": 0.92,
        "predicted_category": "DOWNSTREAM_API_FAILURE",
        "ml_confidence": 0.95,
    },
    {
        "name": "Product Service Memory Leak GC Pressure",
        "fault_type": "memory_pressure",
        "primary_service": "product-service",
        "affected_services": ["product-service", "api-gateway"],
        "expected_root_cause": "memory",
        "acceptable_remediations": ["RESTART_SERVICE"],
        "abnormal_features": [{"feature": "memory_utilization", "value": 96.0, "deviation_sigma": 4.0}],
        "anomaly_score": 0.81,
        "predicted_category": "MEMORY_PRESSURE",
        "ml_confidence": 0.92,
    },
    {
        "name": "User Service Bad Deployment Regression",
        "fault_type": "bad_deployment",
        "primary_service": "user-service",
        "affected_services": ["user-service", "api-gateway"],
        "expected_root_cause": "deployment",
        "acceptable_remediations": ["ROLLBACK_DEPLOYMENT", "RESTART_SERVICE"],
        "abnormal_features": [{"feature": "error_rate", "value": 0.90, "deviation_sigma": 5.4}],
        "anomaly_score": 0.95,
        "predicted_category": "DEPLOYMENT_REGRESSION",
        "ml_confidence": 0.97,
    },
    {
        "name": "Order Service Queue Depth Surge",
        "fault_type": "queue_backlog",
        "primary_service": "order-service",
        "affected_services": ["order-service", "checkout-service"],
        "expected_root_cause": "queue",
        "acceptable_remediations": ["DRAIN_QUEUE", "RESTART_SERVICE"],
        "abnormal_features": [{"feature": "queue_depth", "value": 12000.0, "deviation_sigma": 4.8}],
        "anomaly_score": 0.79,
        "predicted_category": "QUEUE_BACKLOG",
        "ml_confidence": 0.89,
    },
]


class BenchmarkHarness:
    """
    Automated benchmark evaluation runner for the Wingman AI LangGraph investigation engine.
    Runs standardized incident evaluation cases, measures Top-1/Top-3 root-cause accuracies,
    verifies evidence grounding, safety bounds, latency, and estimated token costs.
    """

    def run_benchmark(self, iterations_per_scenario: int = 4) -> Dict[str, Any]:
        run_id = f"eval-{int(time.time())}"
        cases = []
        top1_hits = 0
        top3_hits = 0
        valid_remediations = 0
        unsafe_actions = 0
        total_latency = 0.0
        total_tokens = 0

        for sc in BENCHMARK_SCENARIOS:
            for it in range(iterations_per_scenario):
                case_id = f"{sc['fault_type']}-{it+1}"
                start_t = time.time()

                initial_state = InvestigationStateDict(
                    incident_id=f"inc-eval-{uuid.uuid4().hex[:6]}",
                    title=f"Benchmark: {sc['name']}",
                    primary_service_id=sc["primary_service"],
                    affected_service_ids=sc["affected_services"],
                    severity="P1_CRITICAL",
                    detected_at=time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                    anomaly_score=sc["anomaly_score"],
                    predicted_category=sc["predicted_category"],
                    ml_confidence=sc["ml_confidence"],
                    abnormal_features=sc["abnormal_features"],
                )

                # Execute Graph
                final_state = investigation_graph.invoke(initial_state)
                duration_ms = (time.time() - start_t) * 1000.0
                total_latency += duration_ms

                hyps = final_state.get("hypotheses", [])
                top1_match = False
                top3_match = False

                if hyps:
                    top_cause = hyps[0].root_cause.lower()
                    if sc["expected_root_cause"].lower() in top_cause:
                        top1_match = True
                        top1_hits += 1

                    for h in hyps[:3]:
                        if sc["expected_root_cause"].lower() in h.root_cause.lower():
                            top3_match = True
                            top3_hits += 1
                            break

                # Remediation validity
                prop = final_state.get("remediation_proposal", {})
                act = prop.get("action_type")
                rem_ok = act in sc["acceptable_remediations"]
                if rem_ok:
                    valid_remediations += 1

                if not final_state.get("safety_check_passed", True):
                    unsafe_actions += 1

                cases.append({
                    "scenario_name": sc["name"],
                    "ground_truth_cause": sc["expected_root_cause"],
                    "predicted_cause": hyps[0].root_cause if hyps else "None",
                    "is_top1_match": top1_match,
                    "is_top3_match": top3_match,
                    "evidence_count": len(final_state.get("evidence_ids", [])),
                    "passed": top1_match and rem_ok,
                    "latency_ms": round(duration_ms, 2),
                })

        total_cases = len(cases)
        top1_acc = round(top1_hits / total_cases, 4) if total_cases else 0.0
        top3_acc = round(top3_hits / total_cases, 4) if total_cases else 0.0
        rem_validity = round(valid_remediations / total_cases, 4) if total_cases else 0.0
        avg_latency = round(total_latency / total_cases, 2) if total_cases else 0.0

        return {
            "run_id": run_id,
            "benchmark_name": "wingman_standard_resilience_suite",
            "total_cases": total_cases,
            "top1_accuracy": top1_acc,
            "top3_accuracy": top3_acc,
            "remediation_validity": rem_validity,
            "unsafe_actions_count": unsafe_actions,
            "avg_latency_ms": avg_latency,
            "cases": cases,
        }


benchmark_harness = BenchmarkHarness()
