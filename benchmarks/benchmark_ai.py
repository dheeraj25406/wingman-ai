import os
import sys
import time
import json
import uuid
import numpy as np
from typing import Dict, Any, List

from agent.state.investigation_state import InvestigationStateDict
from agent.graph.investigation_graph import investigation_graph
from agent.tools.gemini_service import gemini_service
from agent.evaluation.benchmark_harness import BENCHMARK_SCENARIOS


def evaluate_static_heuristic_baseline(scenarios: List[Dict[str, Any]], iterations: int = 5) -> Dict[str, Any]:
    """
    Baseline 1: Static Rule-Based Diagnostic Engine.
    Diagnoses based strictly on observable alert signals (abnormal_features, predicted_category),
    without ground-truth label leakage and without dynamic multi-hop tool execution.
    """
    cases = []
    latencies = []
    top1_hits = 0
    top3_hits = 0

    for sc in scenarios:
        for it in range(iterations):
            t0 = time.perf_counter()
            features = [f["feature"] for f in sc.get("abnormal_features", [])]
            category = sc.get("predicted_category", "")
            service = sc.get("primary_service", "")

            # Realistic heuristic decision logic on observable signals (no ground truth sc["fault_type"] access)
            if "db_connections" in features or category == "DB_POOL_EXHAUSTION":
                predicted_cause = f"Database connection pool exhaustion on {service}"
            elif "cpu_utilization" in features or category == "CPU_SATURATION":
                predicted_cause = f"CPU compute saturation on {service}"
            elif "memory_utilization" in features or category == "MEMORY_PRESSURE":
                predicted_cause = f"Memory pressure and leak on {service}"
            elif "queue_depth" in features or category == "QUEUE_BACKLOG":
                predicted_cause = f"Worker queue backlog on {service}"
            elif "error_rate" in features:
                # Ambiguous signal: without deployment query or traces, rule engine assumes generic dependency failure
                predicted_cause = f"Downstream dependency error on {service}"
            else:
                predicted_cause = f"Unknown anomaly on {service}"

            duration_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(duration_ms)

            match = sc["expected_root_cause"].lower() in predicted_cause.lower()
            if match:
                top1_hits += 1
                top3_hits += 1

            cases.append({
                "scenario": sc["name"],
                "top1_match": match,
                "evidence_count": 0,  # Rules gather no dynamic evidence
                "latency_ms": round(duration_ms, 4),
            })

    total = len(cases)
    return {
        "model": "Static Rule-Based Baseline",
        "total_trials": total,
        "top1_accuracy": round(top1_hits / total, 4) if total else 0.0,
        "top3_accuracy": round(top3_hits / total, 4) if total else 0.0,
        "evidence_coverage_avg": 0.0,
        "hallucination_rate": 0.0,
        "latency_ms": {
            "mean": round(float(np.mean(latencies)), 4),
            "p50": round(float(np.percentile(latencies, 50)), 4),
            "p95": round(float(np.percentile(latencies, 95)), 4),
            "p99": round(float(np.percentile(latencies, 99)), 4),
        },
    }


def evaluate_single_shot_llm_baseline(scenarios: List[Dict[str, Any]], iterations: int = 5) -> Dict[str, Any]:
    """
    Baseline 2: Single-Shot LLM Prompt.
    Passes raw alert context directly to Gemini without diagnostic tool gathering or multi-step graph verification.
    Directly invokes gemini-3.5-flash-lite and measures true end-to-end API response latency.
    """
    cases = []
    latencies = []
    top1_hits = 0
    top3_hits = 0
    hallucinations = 0

    for sc in scenarios:
        for it in range(iterations):
            prompt = (
                f"Incident alert on {sc['primary_service']}. Affected: {sc['affected_services']}. "
                f"Anomaly score: {sc['anomaly_score']}. Category: {sc['predicted_category']}. "
                f"Features: {sc['abnormal_features']}. Identify root cause in one short phrase."
            )

            predicted_cause = ""
            duration_ms = 0.0
            if gemini_service.is_configured:
                for attempt in range(1, 4):
                    try:
                        t0 = time.perf_counter()
                        res_text = gemini_service.generate_text(prompt=prompt)
                        duration_ms = (time.perf_counter() - t0) * 1000.0
                        predicted_cause = res_text.lower()
                        break
                    except Exception as e:
                        time.sleep(1.0 * attempt)
                        duration_ms = (time.perf_counter() - t0) * 1000.0

            if not predicted_cause:
                predicted_cause = f"Unresolved prompt error on {sc['primary_service']}"

            latencies.append(duration_ms)

            match = sc["expected_root_cause"].lower() in predicted_cause
            if match:
                top1_hits += 1
                top3_hits += 1

            # Check if LLM cited hallucinated specific evidence (since no tool data was provided)
            has_hallucination = "log" in predicted_cause or "metric" in predicted_cause
            if has_hallucination:
                hallucinations += 1

            cases.append({
                "scenario": sc["name"],
                "top1_match": match,
                "evidence_count": 0,
                "latency_ms": round(duration_ms, 2),
            })

    total = len(cases)
    return {
        "model": "Single-Shot Unstructured LLM Prompt (Gemini 3.5 Flash-Lite)",
        "total_trials": total,
        "top1_accuracy": round(top1_hits / total, 4) if total else 0.0,
        "top3_accuracy": round(top3_hits / total, 4) if total else 0.0,
        "evidence_coverage_avg": 0.0,
        "hallucination_rate": round(hallucinations / total, 4) if total else 0.0,
        "latency_ms": {
            "mean": round(float(np.mean(latencies)), 4),
            "p50": round(float(np.percentile(latencies, 50)), 4),
            "p95": round(float(np.percentile(latencies, 95)), 4),
            "p99": round(float(np.percentile(latencies, 99)), 4),
        },
    }


def evaluate_langgraph_investigation(scenarios: List[Dict[str, Any]], iterations: int = 5) -> Dict[str, Any]:
    """
    Proposed: Full 16-Node LangGraph Investigation Engine.
    Executes multi-hop diagnostic retrieval, evidence validation, hypothesis ranking, safety checks, and remediation.
    """
    cases = []
    latencies = []
    top1_hits = 0
    top3_hits = 0
    valid_evidence_counts = []
    valid_remediations = 0
    safety_passes = 0

    for sc in scenarios:
        for it in range(iterations):
            t0 = time.perf_counter()

            initial_state = InvestigationStateDict(
                incident_id=f"inc-bench-{uuid.uuid4().hex[:6]}",
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

            # Invoke Graph
            final_state = investigation_graph.invoke(initial_state)
            duration_ms = (time.perf_counter() - t0) * 1000.0
            latencies.append(duration_ms)

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

            ev_ids = final_state.get("evidence_ids", [])
            valid_evidence_counts.append(len(ev_ids))

            prop = final_state.get("remediation_proposal", {})
            if prop.get("action_type") in sc["acceptable_remediations"]:
                valid_remediations += 1

            if final_state.get("safety_check_passed", True):
                safety_passes += 1

            cases.append({
                "scenario": sc["name"],
                "top1_match": top1_match,
                "top3_match": top3_match,
                "evidence_count": len(ev_ids),
                "remediation": prop.get("action_type"),
                "latency_ms": round(duration_ms, 2),
            })

    total = len(cases)
    return {
        "model": "16-Node Multi-Hop LangGraph Agent (Wingman AI)",
        "total_trials": total,
        "top1_accuracy": round(top1_hits / total, 4) if total else 0.0,
        "top3_accuracy": round(top3_hits / total, 4) if total else 0.0,
        "evidence_coverage_avg": round(float(np.mean(valid_evidence_counts)), 2) if valid_evidence_counts else 0.0,
        "remediation_validity_rate": round(valid_remediations / total, 4) if total else 0.0,
        "safety_compliance_rate": round(safety_passes / total, 4) if total else 0.0,
        "latency_ms": {
            "mean": round(float(np.mean(latencies)), 2),
            "p50": round(float(np.percentile(latencies, 50)), 2),
            "p95": round(float(np.percentile(latencies, 95)), 2),
            "p99": round(float(np.percentile(latencies, 99)), 2),
        },
        "sample_cases": cases[:5],
    }


def run_ai_benchmark(output_filename: str = "ai_benchmark_baseline.json") -> Dict[str, Any]:
    print("=" * 70)
    print(" EXECUTING AI INVESTIGATION WORKFLOW BENCHMARK SUITE")
    print("=" * 70)
    print(f"Scenarios: {len(BENCHMARK_SCENARIOS)} distinct incident archetypes (5 iterations each = 30 trials)")

    print("\n[1/3] Benchmarking Static Heuristic Diagnostic Engine...")
    base1 = evaluate_static_heuristic_baseline(BENCHMARK_SCENARIOS, iterations=5)

    print("\n[2/3] Benchmarking Single-Shot Unstructured LLM Baseline...")
    base2 = evaluate_single_shot_llm_baseline(BENCHMARK_SCENARIOS, iterations=5)

    print("\n[3/3] Benchmarking Full 16-Node LangGraph Investigation Workflow...")
    langgraph_res = evaluate_langgraph_investigation(BENCHMARK_SCENARIOS, iterations=5)

    final_results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_scenarios": len(BENCHMARK_SCENARIOS),
            "trials_per_scenario": 5,
            "total_trials_per_approach": 30,
        },
        "approaches": {
            "static_rule_engine": base1,
            "single_shot_llm": base2,
            "langgraph_investigation": langgraph_res,
        }
    }

    os.makedirs("benchmarks/results", exist_ok=True)
    out_path = os.path.join("benchmarks/results", output_filename)
    with open(out_path, "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"\n[OK] Machine-readable AI benchmark saved to {out_path}")
    return final_results


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "ai_benchmark_baseline.json"
    run_ai_benchmark(out_file)
