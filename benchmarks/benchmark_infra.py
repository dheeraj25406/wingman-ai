import os
import sys
import time
import json
import subprocess
import numpy as np
import asyncio
from typing import Dict, Any, List

from backend.app.database.session import async_session_factory
from backend.app.database.incident_repository import get_incident_from_db, load_incidents_from_db
from backend.app.models.models import IncidentModel, ServiceModel
from sqlalchemy import select


def get_docker_stats() -> Dict[str, Any]:
    """Retrieves live CPU and RAM consumption for running Docker containers."""
    try:
        res = subprocess.run(
            ["docker", "stats", "--no-stream", "--format", "{{json .}}"],
            capture_output=True,
            text=True,
            check=True,
        )
        lines = res.stdout.strip().split("\n")
        containers = {}
        for line in lines:
            if line:
                data = json.loads(line)
                name = data.get("Name", "unknown")
                if "wingman" in name:
                    containers[name] = {
                        "cpu_percentage": data.get("CPUPerc", "0.0%"),
                        "memory_usage": data.get("MemUsage", "0MiB"),
                        "memory_percentage": data.get("MemPerc", "0.0%"),
                        "network_io": data.get("NetIO", "0B/0B"),
                        "block_io": data.get("BlockIO", "0B/0B"),
                    }
        return containers
    except Exception as e:
        return {"error": str(e)}


async def benchmark_database_query_latencies(iterations: int = 40) -> Dict[str, Any]:
    """
    Measures PostgreSQL query latency percentiles over 40 iterations.
    1. Single-row key lookup
    2. Deep eager-loaded relational query
    3. Transactional write & rollback
    """
    single_lookup_latencies = []
    eager_load_latencies = []
    write_latencies = []

    # Get sample incident ID
    async with async_session_factory() as session:
        stmt = select(IncidentModel.id).limit(1)
        res = await session.execute(stmt)
        sample_id = res.scalar_one_or_none() or "inc-20261111-001"

    for _ in range(iterations):
        # 1. Single lookup
        t0 = time.perf_counter()
        _ = await get_incident_from_db(sample_id)
        single_lookup_latencies.append((time.perf_counter() - t0) * 1000.0)

        # 2. Deep eager loading
        t0 = time.perf_counter()
        _ = await load_incidents_from_db()
        eager_load_latencies.append((time.perf_counter() - t0) * 1000.0)

        # 3. Transaction write with rollback
        t0 = time.perf_counter()
        async with async_session_factory() as session:
            async with session.begin():
                temp_model = IncidentModel(
                    id=f"temp-bench-{time.time_ns()}",
                    title="Benchmark Temp Write",
                    severity="P4_LOW",
                    status="CLOSED",
                    primary_service_id="order-service",
                )
                session.add(temp_model)
                await session.flush()
                await session.rollback()
        write_latencies.append((time.perf_counter() - t0) * 1000.0)

    def stats(arr):
        return {
            "mean_ms": round(float(np.mean(arr)), 3),
            "p50_ms": round(float(np.percentile(arr, 50)), 3),
            "p95_ms": round(float(np.percentile(arr, 95)), 3),
            "p99_ms": round(float(np.percentile(arr, 99)), 3),
        }

    return {
        "iterations": iterations,
        "single_row_lookup": stats(single_lookup_latencies),
        "eager_loaded_history_query": stats(eager_load_latencies),
        "transactional_write_rollback": stats(write_latencies),
    }


async def run_infra_benchmark(output_filename: str = "infra_benchmark_baseline.json") -> Dict[str, Any]:
    print("=" * 70)
    print(" EXECUTING INFRASTRUCTURE & DATABASE RESOURCE BENCHMARK SUITE")
    print("=" * 70)

    print("\n[1/2] Capturing Docker Container Resource Utilization (CPU, RAM, Net I/O)...")
    container_stats = get_docker_stats()
    for name, st in container_stats.items():
        print(f" {name:20} -> CPU: {st['cpu_percentage']:6} | Memory: {st['memory_usage']:16} ({st['memory_percentage']})")

    print("\n[2/2] Measuring PostgreSQL Query Latencies (40 iterations)...")
    db_stats = await benchmark_database_query_latencies(iterations=40)
    print(f" Single-Row Lookup (p50/p95):       {db_stats['single_row_lookup']['p50_ms']:5.2f}ms / {db_stats['single_row_lookup']['p95_ms']:5.2f}ms")
    print(f" Eager-Loaded History (p50/p95):     {db_stats['eager_loaded_history_query']['p50_ms']:5.2f}ms / {db_stats['eager_loaded_history_query']['p95_ms']:5.2f}ms")
    print(f" Transaction Write & Rollback (p50): {db_stats['transactional_write_rollback']['p50_ms']:5.2f}ms / {db_stats['transactional_write_rollback']['p95_ms']:5.2f}ms")

    final_results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "host_os": sys.platform,
        },
        "container_resources": container_stats,
        "database_latencies": db_stats,
    }

    os.makedirs("benchmarks/results", exist_ok=True)
    out_path = os.path.join("benchmarks/results", output_filename)
    with open(out_path, "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"\n[OK] Machine-readable infrastructure benchmark saved to {out_path}")
    return final_results


if __name__ == "__main__":
    out_f = sys.argv[1] if len(sys.argv) > 1 else "infra_benchmark_baseline.json"
    asyncio.run(run_infra_benchmark(out_f))
