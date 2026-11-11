from fastapi import APIRouter, Query
from typing import Dict, Any

from simulator.telemetry.buffer import telemetry_buffer
from backend.app.services.correlation_engine import SERVICE_DEPENDENCY_GRAPH

router = APIRouter(prefix="/metrics", tags=["Metrics"])


@router.get("/overview")
async def get_metrics_overview() -> Dict[str, Any]:
    latest = telemetry_buffer.get_all_latest_metrics()
    total = len(latest)
    if total == 0:
        return {
            "status": "success",
            "data": {
                "total_services": 6,
                "healthy_services": 6,
                "degraded_services": 0,
                "critical_services": 0,
                "global_error_rate": 0.002,
                "avg_latency_p95": 45.2,
                "total_throughput_rps": 10.0,
                "active_incidents_count": 0,
            }
        }

    err_sum = sum(m.get("error_rate", 0.0) for m in latest.values())
    p95_sum = sum(m.get("latency_p95", 0.0) for m in latest.values())
    rps_sum = sum(m.get("request_rate", 0.0) for m in latest.values())

    critical_count = sum(1 for m in latest.values() if m.get("error_rate", 0.0) > 0.4 or m.get("latency_p95", 0.0) > 1500.0)
    degraded_count = sum(1 for m in latest.values() if (0.05 < m.get("error_rate", 0.0) <= 0.4) or (500.0 < m.get("latency_p95", 0.0) <= 1500.0))
    healthy_count = total - critical_count - degraded_count

    return {
        "status": "success",
        "data": {
            "total_services": total,
            "healthy_services": max(0, healthy_count),
            "degraded_services": degraded_count,
            "critical_services": critical_count,
            "global_error_rate": round(err_sum / total, 4),
            "avg_latency_p95": round(p95_sum / total, 2),
            "total_throughput_rps": round(rps_sum, 2),
            "active_incidents_count": critical_count,
        }
    }


@router.get("/services/{service_id}")
async def get_service_metrics(service_id: str, limit: int = Query(default=30, ge=5, le=120)) -> Dict[str, Any]:
    metrics = telemetry_buffer.get_service_metrics(service_id, limit=limit)
    return {"status": "success", "data": metrics}
