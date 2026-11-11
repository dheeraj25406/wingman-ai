import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from collections import deque
from dataclasses import dataclass, field, asdict


@dataclass
class ServiceMetricPoint:
    timestamp: str
    epoch: float
    service_id: str
    cpu_utilization: float
    memory_utilization: float
    request_rate: float
    error_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    db_connections: float
    queue_depth: float
    timeout_rate: float


@dataclass
class LogRecord:
    id: str
    timestamp: str
    epoch: float
    service_id: str
    level: str  # INFO, WARN, ERROR
    message: str
    trace_id: Optional[str] = None
    span_id: Optional[str] = None
    error_type: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SpanRecord:
    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    service_id: str
    operation: str
    start_time: float
    duration_ms: float
    status: str  # OK, ERROR
    http_status: int
    error_message: Optional[str] = None


class TelemetryBuffer:
    """
    In-memory, high-performance circular telemetry buffer for simulator metrics, logs, and traces.
    Keeps a sliding window of historical telemetry for ML feature extraction and incident investigation.
    """

    SERVICES = [
        "api-gateway",
        "user-service",
        "product-service",
        "checkout-service",
        "payment-service",
        "order-service",
    ]

    def __init__(self, max_metric_points: int = 1200, max_logs: int = 5000, max_traces: int = 1000):
        self._metrics: Dict[str, deque] = {svc: deque(maxlen=max_metric_points) for svc in self.SERVICES}
        self._logs: deque = deque(maxlen=max_logs)
        self._traces: Dict[str, List[SpanRecord]] = {}
        self._trace_order: deque = deque(maxlen=max_traces)

    def record_metric(self, point: ServiceMetricPoint):
        if point.service_id in self._metrics:
            self._metrics[point.service_id].append(point)

    def record_log(self, log: LogRecord):
        self._logs.append(log)

    def record_span(self, span: SpanRecord):
        if span.trace_id not in self._traces:
            self._traces[span.trace_id] = []
            self._trace_order.append(span.trace_id)
        self._traces[span.trace_id].append(span)

        # Evict old traces if buffer exceeds capacity
        while len(self._traces) > self._trace_order.maxlen:
            oldest = self._trace_order.popleft()
            self._traces.pop(oldest, None)

    def get_service_metrics(self, service_id: str, limit: int = 60) -> List[Dict[str, Any]]:
        if service_id not in self._metrics:
            return []
        points = list(self._metrics[service_id])[-limit:]
        return [asdict(p) for p in points]

    def get_all_latest_metrics(self) -> Dict[str, Dict[str, Any]]:
        latest = {}
        for svc, dq in self._metrics.items():
            if dq:
                latest[svc] = asdict(dq[-1])
        return latest

    def search_logs(
        self,
        service_id: Optional[str] = None,
        level: Optional[str] = None,
        query: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        results = []
        for log in reversed(self._logs):
            if service_id and log.service_id != service_id:
                continue
            if level and log.level.upper() != level.upper():
                continue
            if query and query.lower() not in log.message.lower() and query.lower() not in str(log.details).lower():
                continue
            results.append(asdict(log))
            if len(results) >= limit:
                break
        return results

    def get_trace(self, trace_id: str) -> Optional[List[Dict[str, Any]]]:
        spans = self._traces.get(trace_id)
        if not spans:
            return None
        return [asdict(s) for s in spans]

    def get_recent_traces(self, service_id: Optional[str] = None, has_error: Optional[bool] = None, limit: int = 20) -> List[Dict[str, Any]]:
        summaries = []
        for tid in reversed(self._trace_order):
            spans = self._traces.get(tid, [])
            if not spans:
                continue
            if service_id and not any(s.service_id == service_id for s in spans):
                continue
            any_error = any(s.status == "ERROR" for s in spans)
            if has_error is not None and any_error != has_error:
                continue

            root_span = spans[0]
            total_duration = max(s.duration_ms for s in spans)
            summaries.append({
                "trace_id": tid,
                "root_operation": root_span.operation,
                "root_service": root_span.service_id,
                "span_count": len(spans),
                "duration_ms": round(total_duration, 2),
                "has_error": any_error,
                "start_time": datetime.fromtimestamp(root_span.start_time, tz=timezone.utc).isoformat(),
            })
            if len(summaries) >= limit:
                break
        return summaries


# Global Singleton
telemetry_buffer = TelemetryBuffer()
