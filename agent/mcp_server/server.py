import asyncio
from typing import Optional, Dict, Any
from mcp.server.mcpserver import MCPServer

from agent.tools.diagnostic_tools import diagnostic_tools


mcp_server = MCPServer(
    name="wingman-diagnostic-server",
    version="1.0.0",
    description="Model Context Protocol Server for Wingman AI Incident Investigation"
)


@mcp_server.tool()
def get_service_metrics(service_id: str, limit: int = 30) -> Dict[str, Any]:
    """Retrieves recent sliding-window telemetry metrics (CPU, Memory, RPS, Errors, Latency, DB connections) for a service."""
    return diagnostic_tools.get_service_metrics(service_id, limit=limit)


@mcp_server.tool()
def search_logs(service_id: Optional[str] = None, level: Optional[str] = None, query: Optional[str] = None, limit: int = 20) -> Dict[str, Any]:
    """Searches structured application logs filtered by service, level (INFO/WARN/ERROR), or keyword query."""
    return diagnostic_tools.search_logs(service_id=service_id, level=level, query=query, limit=limit)


@mcp_server.tool()
def get_recent_traces(service_id: Optional[str] = None, has_error: Optional[bool] = None, limit: int = 10) -> Dict[str, Any]:
    """Fetches recent distributed trace summaries filtered by service or error presence."""
    return diagnostic_tools.get_recent_traces(service_id=service_id, has_error=has_error, limit=limit)


@mcp_server.tool()
def get_trace(trace_id: str) -> Dict[str, Any]:
    """Fetches full distributed trace spans, parent-child relationships, status codes, and error messages for a trace ID."""
    return diagnostic_tools.get_trace(trace_id)


@mcp_server.tool()
def get_service_map() -> Dict[str, Any]:
    """Returns the topology of distributed services and their upstream/downstream dependency relationships."""
    return diagnostic_tools.get_service_map()


@mcp_server.tool()
def get_recent_deployments(service_id: Optional[str] = None, lookback_minutes: int = 60) -> Dict[str, Any]:
    """Retrieves recent deployment release events, version tags, commit hashes, and environment variable changes."""
    return diagnostic_tools.get_recent_deployments(service_id=service_id, lookback_minutes=lookback_minutes)


@mcp_server.tool()
def compare_service_baseline(service_id: str) -> Dict[str, Any]:
    """Compares current service performance against 24-hour historical baseline parameters."""
    return diagnostic_tools.compare_service_baseline(service_id=service_id)


@mcp_server.tool()
def get_incident_history(service_id: str, limit: int = 5) -> Dict[str, Any]:
    """Retrieves past incidents, known root causes, and resolutions for a service."""
    return diagnostic_tools.get_incident_history(service_id=service_id, limit=limit)


if __name__ == "__main__":
    asyncio.run(mcp_server.run_stdio_async())
