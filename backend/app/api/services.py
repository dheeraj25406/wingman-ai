from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any

from simulator.telemetry.buffer import telemetry_buffer
from backend.app.services.correlation_engine import SERVICE_DEPENDENCY_GRAPH
from simulator.faults.fault_engine import fault_engine

router = APIRouter(prefix="/services", tags=["Services"])


@router.get("")
async def list_services() -> Dict[str, Any]:
    latest = telemetry_buffer.get_all_latest_metrics()
    services_list = []

    for svc_id, deps in SERVICE_DEPENDENCY_GRAPH.items():
        if svc_id == "database":
            continue

        active_fault = fault_engine.get_fault_for_service(svc_id)
        metric = latest.get(svc_id, {})
        err_rate = metric.get("error_rate", 0.0)
        p95 = metric.get("latency_p95", 30.0)

        status = "healthy"
        if active_fault or err_rate > 0.3 or p95 > 1000.0:
            status = "critical" if err_rate > 0.5 or p95 > 2000.0 else "degraded"

        services_list.append({
            "id": svc_id,
            "name": svc_id.replace("-", " ").title(),
            "status": status,
            "dependencies": deps,
            "active_fault": active_fault.fault_type if active_fault else None,
            "latest_metrics": {
                "cpu_utilization": metric.get("cpu_utilization", 20.0),
                "memory_utilization": metric.get("memory_utilization", 35.0),
                "error_rate": err_rate,
                "latency_p95": p95,
                "request_rate": metric.get("request_rate", 10.0),
                "db_connections": metric.get("db_connections", 15.0),
            }
        })

    return {"status": "success", "data": services_list}


@router.get("/{service_id}")
async def get_service(service_id: str) -> Dict[str, Any]:
    if service_id not in SERVICE_DEPENDENCY_GRAPH:
        raise HTTPException(status_code=404, detail=f"Service {service_id} not found")

    metrics = telemetry_buffer.get_service_metrics(service_id, limit=30)
    active_fault = fault_engine.get_fault_for_service(service_id)

    return {
        "status": "success",
        "data": {
            "id": service_id,
            "name": service_id.replace("-", " ").title(),
            "dependencies": SERVICE_DEPENDENCY_GRAPH.get(service_id, []),
            "active_fault": active_fault.fault_type if active_fault else None,
            "recent_metrics": metrics,
        }
    }
