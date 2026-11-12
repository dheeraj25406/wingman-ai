import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from simulator.telemetry.buffer import telemetry_buffer
from backend.app.services.correlation_engine import SERVICE_DEPENDENCY_GRAPH, UPSTREAM_MAP


class GetMetricsInput(BaseModel):
    service_id: str = Field(..., description="Target service identifier (e.g. 'order-service', 'checkout-service')")
    limit: int = Field(default=30, ge=1, le=100, description="Number of recent metric sample points")


class SearchLogsInput(BaseModel):
    service_id: Optional[str] = Field(default=None, description="Optional target service identifier")
    level: Optional[str] = Field(default=None, description="Log level filter: 'INFO', 'WARN', 'ERROR'")
    query: Optional[str] = Field(default=None, description="Keyword search string in message or details")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum number of log entries to retrieve")


class GetTraceInput(BaseModel):
    trace_id: str = Field(..., description="Hex trace ID (e.g. 'tr-...')")


class CompareBaselineInput(BaseModel):
    service_id: str = Field(..., description="Target service identifier")


class DiagnosticTools:
    """
    Controlled, read-only diagnostic tools exposed to the agent and MCP server.
    Ensures safe, bounded observability lookups without shell or filesystem access.
    """

    @staticmethod
    def get_service_metrics(service_id: str, limit: int = 30) -> Dict[str, Any]:
        """Retrieves recent sliding window metrics for a specific service."""
        points = telemetry_buffer.get_service_metrics(service_id, limit=limit)
        if not points:
            return {"service_id": service_id, "data_points": [], "count": 0, "status": "NO_DATA"}

        latest = points[-1]
        return {
            "service_id": service_id,
            "data_points": points,
            "count": len(points),
            "latest_summary": {
                "cpu_utilization": latest["cpu_utilization"],
                "memory_utilization": latest["memory_utilization"],
                "request_rate": latest["request_rate"],
                "error_rate": latest["error_rate"],
                "latency_p95": latest["latency_p95"],
                "db_connections": latest["db_connections"],
                "queue_depth": latest["queue_depth"],
                "timeout_rate": latest["timeout_rate"],
            },
            "status": "OK"
        }

    @staticmethod
    def search_logs(service_id: Optional[str] = None, level: Optional[str] = None, query: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
        """Searches structured application logs with optional level and keyword filters."""
        logs = telemetry_buffer.search_logs(service_id=service_id, level=level, query=query, limit=limit)
        return {
            "service_id": service_id,
            "level_filter": level,
            "query_filter": query,
            "count": len(logs),
            "logs": logs,
        }

    @staticmethod
    def get_recent_traces(service_id: Optional[str] = None, has_error: Optional[bool] = None, limit: int = 10) -> Dict[str, Any]:
        """Fetches recent distributed traces across services."""
        traces = telemetry_buffer.get_recent_traces(service_id=service_id, has_error=has_error, limit=limit)
        return {
            "service_id": service_id,
            "count": len(traces),
            "traces": traces,
        }

    @staticmethod
    def get_trace(trace_id: str) -> Dict[str, Any]:
        """Fetches distributed trace span hierarchy and error details."""
        spans = telemetry_buffer.get_trace(trace_id)
        if not spans:
            return {"trace_id": trace_id, "status": "NOT_FOUND", "spans": []}
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "spans": spans,
            "has_error": any(s["status"] == "ERROR" for s in spans),
        }

    @staticmethod
    def get_service_map() -> Dict[str, Any]:
        """Returns the full service dependency topology and upstream/downstream maps."""
        return {
            "dependencies": SERVICE_DEPENDENCY_GRAPH,
            "upstream_dependencies": UPSTREAM_MAP,
            "services": list(SERVICE_DEPENDENCY_GRAPH.keys()),
        }

    @staticmethod
    def get_recent_deployments(service_id: Optional[str] = None, lookback_minutes: int = 60) -> Dict[str, Any]:
        """Simulated recent deployment events for services."""
        # Realistic deployment log
        deployments = [
            {
                "service_id": "user-service",
                "version": "v2.4.1",
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "author": "ci-release-bot@wingman.internal",
                "commit_hash": "a4f89d1",
                "status": "DEPLOYED",
                "changelog": "Update JWT token decoding logic and refresh dependencies",
                "env_vars_changed": ["JWT_EXPIRY_SECONDS", "JWT_SECRET_KEY"]
            },
            {
                "service_id": "checkout-service",
                "version": "v3.1.0",
                "deployed_at": datetime.now(timezone.utc).isoformat(),
                "author": "alex.chen@wingman.internal",
                "commit_hash": "7b2e10c",
                "status": "DEPLOYED",
                "changelog": "Enable parallel checkout validation",
                "env_vars_changed": []
            }
        ]
        if service_id:
            deployments = [d for d in deployments if d["service_id"] == service_id]
        return {
            "service_id": service_id,
            "deployments": deployments,
            "count": len(deployments)
        }

    @staticmethod
    def compare_service_baseline(service_id: str) -> Dict[str, Any]:
        """Compares current service telemetry against established baseline thresholds."""
        metrics = telemetry_buffer.get_service_metrics(service_id, limit=5)
        if not metrics:
            return {"service_id": service_id, "status": "NO_DATA"}

        curr = metrics[-1]
        from simulator.services.mesh import ServiceMesh
        baseline = ServiceMesh.SERVICE_BASELINES.get(service_id, {"cpu": 20.0, "latency_p95": 50.0, "db_conn": 15.0})

        deviations = {
            "cpu_delta": round(curr["cpu_utilization"] - baseline.get("cpu", 20.0), 2),
            "latency_p95_delta_ms": round(curr["latency_p95"] - baseline.get("latency_p95", 50.0), 2),
            "db_conn_delta": round(curr["db_connections"] - baseline.get("db_conn", 15.0), 2),
            "error_rate": curr["error_rate"],
        }
        return {
            "service_id": service_id,
            "current": curr,
            "baseline": baseline,
            "deviations": deviations,
        }

    @staticmethod
    def get_incident_history(service_id: str, limit: int = 5) -> Dict[str, Any]:
        """Retrieves past incidents for the specified service."""
        return {
            "service_id": service_id,
            "recent_incidents": [],
            "count": 0
        }


diagnostic_tools = DiagnosticTools()
