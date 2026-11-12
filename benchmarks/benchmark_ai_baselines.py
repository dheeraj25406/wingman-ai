import time
import json
import numpy as np
from agent.tools.gemini_service import gemini_service
from agent.evaluation.benchmark_harness import BENCHMARK_SCENARIOS

def evaluate_audited_baselines():
    print("Evaluating Audited Static Rule Baseline (Observable signals only, NO label leakage)...")
    rule_cases = []
    rule_latencies = []
    rule_hits = 0

    for sc in BENCHMARK_SCENARIOS:
        t0 = time.perf_counter()
        features = [f["feature"] for f in sc.get("abnormal_features", [])]
        category = sc.get("predicted_category", "")
        service = sc.get("primary_service", "")

        # Observability-only heuristics
        if "db_connections" in features or category == "DB_POOL_EXHAUSTION":
            predicted_cause = f"Database connection pool exhaustion on {service}"
        elif "cpu_utilization" in features or category == "CPU_SATURATION":
            predicted_cause = f"CPU compute saturation on {service}"
        elif "memory_utilization" in features or category == "MEMORY_PRESSURE":
            predicted_cause = f"Memory pressure and leak on {service}"
        elif "queue_depth" in features or category == "QUEUE_BACKLOG":
            predicted_cause = f"Worker queue backlog on {service}"
        elif "error_rate" in features:
            # Ambiguous: cannot distinguish downstream timeout from bad deployment without git/traces
            predicted_cause = f"Downstream dependency error on {service}"
        else:
            predicted_cause = f"Unknown anomaly on {service}"

        dur = (time.perf_counter() - t0) * 1000.0
        rule_latencies.append(dur)
        match = sc["expected_root_cause"].lower() in predicted_cause.lower()
        if match:
            rule_hits += 1
        rule_cases.append({"scenario": sc["name"], "match": match, "latency_ms": dur})

    rule_acc = rule_hits / len(BENCHMARK_SCENARIOS)
    print(f"Static Rule Baseline Accuracy: {rule_acc:.2%} ({rule_hits}/{len(BENCHMARK_SCENARIOS)}) | Latency p50: {np.median(rule_latencies):.4f}ms")

    print("\nEvaluating Live Single-Shot Gemini Baseline (6 canonical scenarios, paced)...")
    llm_cases = []
    llm_latencies = []
    llm_hits = 0

    for sc in BENCHMARK_SCENARIOS:
        prompt = (
            f"Production incident alert on microservice '{sc['primary_service']}'. "
            f"Affected downstream services: {sc['affected_services']}. "
            f"Anomaly score: {sc['anomaly_score']}. Category: {sc['predicted_category']}. "
            f"Abnormal features: {sc['abnormal_features']}. "
            f"Identify the probable underlying root cause in one concise sentence."
        )

        t0 = time.perf_counter()
        try:
            res_text = gemini_service.generate_text(prompt=prompt)
            dur = (time.perf_counter() - t0) * 1000.0
            llm_latencies.append(dur)
            predicted = res_text.lower()
            match = sc["expected_root_cause"].lower() in predicted
            if match:
                llm_hits += 1
            print(f"[{sc['fault_type'][:18]:18}] Latency: {dur:6.1f}ms | Match: {str(match):5} | Output: {res_text[:65]}...")
            llm_cases.append({"scenario": sc["name"], "match": match, "latency_ms": dur, "output": res_text})
        except Exception as e:
            print(f"[{sc['fault_type'][:18]:18}] ERROR: {e}")
            dur = (time.perf_counter() - t0) * 1000.0
            llm_latencies.append(dur)

        time.sleep(4.5)  # Pace calls to stay strictly under the 15 RPM limit

    llm_acc = llm_hits / len(BENCHMARK_SCENARIOS)
    print(f"\nSingle-Shot Gemini Accuracy: {llm_acc:.2%} ({llm_hits}/{len(BENCHMARK_SCENARIOS)})")
    if llm_latencies:
        print(f"Live Gemini Latency: Mean={np.mean(llm_latencies):.1f}ms | p50={np.median(llm_latencies):.1f}ms | p95={np.percentile(llm_latencies, 95):.1f}ms")

    # Save audited baseline results
    payload = {
        "static_rule_audited": {
            "model": "Static Rule-Based Baseline (Observable Signals Only)",
            "trials": len(BENCHMARK_SCENARIOS),
            "accuracy": round(rule_acc, 4),
            "label_leakage_prevented": True,
            "latency_p50_ms": round(float(np.median(rule_latencies)), 4),
        },
        "single_shot_gemini_audited": {
            "model": "Single-Shot Unstructured Gemini 3.5 Flash-Lite",
            "trials": len(BENCHMARK_SCENARIOS),
            "accuracy": round(llm_acc, 4),
            "latency_ms": {
                "mean": round(float(np.mean(llm_latencies)), 1) if llm_latencies else 0.0,
                "p50": round(float(np.median(llm_latencies)), 1) if llm_latencies else 0.0,
                "p95": round(float(np.percentile(llm_latencies, 95)), 1) if llm_latencies else 0.0,
            },
            "cases": llm_cases,
        }
    }
    with open("benchmarks/results/ai_baselines_audited.json", "w") as f:
        json.dump(payload, f, indent=2)

if __name__ == "__main__":
    evaluate_audited_baselines()
