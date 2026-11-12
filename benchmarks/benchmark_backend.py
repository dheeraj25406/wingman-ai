import os
import sys
import time
import json
import asyncio
import numpy as np
import httpx
from typing import Dict, Any, List


TARGET_ENDPOINTS = [
    {"name": "health_live", "path": "/api/health/live", "weight": 0.25},
    {"name": "services_list", "path": "/api/services", "weight": 0.25},
    {"name": "metrics_overview", "path": "/api/metrics/overview", "weight": 0.25},
    {"name": "incidents_list", "path": "/api/incidents", "weight": 0.25},
]

CONCURRENCY_LEVELS = [1, 5, 10, 25, 50]
REQUESTS_PER_CONCURRENCY = 1000
REPETITIONS = 3
WARMUP_REQUESTS = 50


async def send_warmup_traffic(base_url: str, count: int = 50):
    """Warm up connection pool, JIT, and in-memory caches before benchmarking."""
    limits = httpx.Limits(max_connections=10, max_keepalive_connections=10)
    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=5.0) as client:
        for i in range(count):
            ep = TARGET_ENDPOINTS[i % len(TARGET_ENDPOINTS)]
            try:
                await client.get(ep["path"], headers={"X-Forwarded-For": f"10.254.0.{(i % 200) + 1}"})
            except Exception:
                pass


async def execute_single_run(
    base_url: str,
    concurrency: int,
    total_requests: int,
    repetition_id: int,
) -> Dict[str, Any]:
    """Executes one repetition of total_requests at the given concurrency level."""
    latencies = []
    errors = 0
    endpoint_latencies = {ep["name"]: [] for ep in TARGET_ENDPOINTS}

    limits = httpx.Limits(max_connections=concurrency + 20, max_keepalive_connections=concurrency + 10)
    async with httpx.AsyncClient(base_url=base_url, limits=limits, timeout=15.0) as client:
        semaphore = asyncio.Semaphore(concurrency)

        async def worker(req_idx: int):
            nonlocal errors
            ep = TARGET_ENDPOINTS[req_idx % len(TARGET_ENDPOINTS)]
            # Distinct virtual client IP per batch to avoid rate limiter collisions
            worker_subnet = ((repetition_id * 30) + (req_idx // 30)) % 250 + 1
            worker_host = (req_idx % concurrency) + 1
            worker_ip = f"10.{worker_subnet}.{worker_host}.1"
            headers = {"X-Forwarded-For": worker_ip}

            async with semaphore:
                t0 = time.perf_counter()
                try:
                    res = await client.get(ep["path"], headers=headers)
                    dur_ms = (time.perf_counter() - t0) * 1000.0
                    if res.status_code == 200:
                        latencies.append(dur_ms)
                        endpoint_latencies[ep["name"]].append(dur_ms)
                    else:
                        errors += 1
                except Exception:
                    errors += 1

        t_start = time.perf_counter()
        tasks = [worker(i) for i in range(total_requests)]
        await asyncio.gather(*tasks)
        total_time = time.perf_counter() - t_start

    rps = total_requests / total_time if total_time > 0 else 0.0
    return {
        "duration_seconds": total_time,
        "throughput_rps": rps,
        "errors": errors,
        "latencies": latencies,
        "endpoint_latencies": endpoint_latencies,
    }


async def benchmark_concurrency_level(
    base_url: str,
    concurrency: int,
    total_requests: int = 1000,
    repetitions: int = 3,
) -> Dict[str, Any]:
    """
    Executes multiple repetitions of a load test for a concurrency level
    and aggregates statistical metrics.
    """
    all_latencies = []
    repetition_rps = []
    total_errors = 0
    combined_endpoints = {ep["name"]: [] for ep in TARGET_ENDPOINTS}

    for rep in range(repetitions):
        run_res = await execute_single_run(
            base_url=base_url,
            concurrency=concurrency,
            total_requests=total_requests,
            repetition_id=rep,
        )
        repetition_rps.append(run_res["throughput_rps"])
        all_latencies.extend(run_res["latencies"])
        total_errors += run_res["errors"]
        for ep_name, dlist in run_res["endpoint_latencies"].items():
            combined_endpoints[ep_name].extend(dlist)
        await asyncio.sleep(0.2)  # Brief cooldown between repetitions

    mean_rps = float(np.mean(repetition_rps))
    p50_rps = float(np.median(repetition_rps))
    total_samples = total_requests * repetitions
    err_rate = total_errors / total_samples if total_samples > 0 else 0.0

    return {
        "concurrency": concurrency,
        "total_requests_per_rep": total_requests,
        "repetitions": repetitions,
        "total_requests_evaluated": total_samples,
        "throughput_rps": round(mean_rps, 2),
        "throughput_median_rps": round(p50_rps, 2),
        "repetition_rps": [round(r, 2) for r in repetition_rps],
        "error_count": total_errors,
        "error_rate": round(err_rate, 4),
        "latency_ms": {
            "mean": round(float(np.mean(all_latencies)), 2) if all_latencies else 0.0,
            "p50": round(float(np.percentile(all_latencies, 50)), 2) if all_latencies else 0.0,
            "p95": round(float(np.percentile(all_latencies, 95)), 2) if all_latencies else 0.0,
            "p99": round(float(np.percentile(all_latencies, 99)), 2) if all_latencies else 0.0,
            "max": round(float(np.max(all_latencies)), 2) if all_latencies else 0.0,
        },
        "per_endpoint_p95": {
            k: round(float(np.percentile(v, 95)), 2) if v else 0.0 for k, v in combined_endpoints.items()
        },
    }


async def run_backend_benchmarks(
    base_url: str = "http://localhost:8000",
    output_filename: str = "backend_benchmark_optimized.json",
) -> Dict[str, Any]:
    print("=" * 70)
    print(" EXECUTING EXPANDED BACKEND CONCURRENCY & LATENCY BENCHMARK SUITE")
    print(f" Target: {base_url}")
    print(f" Config: {REQUESTS_PER_CONCURRENCY} requests x {REPETITIONS} reps = {REQUESTS_PER_CONCURRENCY * REPETITIONS} requests per level")
    print("=" * 70)

    # 1. Warm-up
    print(f"Warming up server with {WARMUP_REQUESTS} requests...")
    await send_warmup_traffic(base_url, count=WARMUP_REQUESTS)
    await asyncio.sleep(0.5)

    results = []
    for c in CONCURRENCY_LEVELS:
        print(f"Testing Concurrency = {c:2d} ({REQUESTS_PER_CONCURRENCY} reqs x {REPETITIONS} reps)... ", end="", flush=True)
        res = await benchmark_concurrency_level(
            base_url=base_url,
            concurrency=c,
            total_requests=REQUESTS_PER_CONCURRENCY,
            repetitions=REPETITIONS,
        )
        results.append(res)
        print(f"-> Mean RPS: {res['throughput_rps']:7.1f} | p50: {res['latency_ms']['p50']:5.1f}ms | p95: {res['latency_ms']['p95']:5.1f}ms | Errors: {res['error_count']}")

    full_payload = {
        "metadata": {
            "target_url": base_url,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "concurrency_levels": CONCURRENCY_LEVELS,
            "requests_per_concurrency": REQUESTS_PER_CONCURRENCY,
            "repetitions": REPETITIONS,
            "warmup_requests": WARMUP_REQUESTS,
            "endpoints": [ep["path"] for ep in TARGET_ENDPOINTS],
        },
        "concurrency_benchmarks": results,
    }

    out_path = os.path.join("benchmarks", "results", output_filename)
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(full_payload, f, indent=2)

    print(f"\n[OK] Machine-readable backend benchmark saved to {out_path}")
    return full_payload


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    out_file = sys.argv[2] if len(sys.argv) > 2 else "backend_benchmark_optimized.json"
    asyncio.run(run_backend_benchmarks(target, out_file))
