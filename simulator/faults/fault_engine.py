import asyncio
import time
from datetime import datetime
from typing import Dict, Optional, List, Any
from dataclasses import dataclass, field


@dataclass
class ActiveFault:
    id: str
    fault_type: str
    target_service_id: str
    intensity: float  # 0.1 to 1.0
    duration_seconds: int
    started_at: float  # unix epoch
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_root_cause: str = ""
    expected_affected_services: List[str] = field(default_factory=list)
    incident_id: Optional[str] = None

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.started_at) > self.duration_seconds


class FaultEngine:
    """
    Central coordinator for safe, controlled fault injections in the simulator.
    Tracks active faults, injects delays, errors, and resource exhaustion without external shell calls.
    """

    FAULT_DEFINITIONS = {
        "db_pool_exhaustion": {
            "name": "Database Connection Pool Exhaustion",
            "default_service": "order-service",
            "expected_cause": "Database connection pool saturated (max_connections reached) causing query timeouts",
            "affected": ["order-service", "checkout-service", "api-gateway"],
            "severity": "P1_CRITICAL"
        },
        "cpu_saturation": {
            "name": "CPU Saturation / Compute Starvation",
            "default_service": "checkout-service",
            "expected_cause": "CPU starvation due to unoptimized recursive cryptographic computation",
            "affected": ["checkout-service", "api-gateway"],
            "severity": "P2_HIGH"
        },
        "memory_pressure": {
            "name": "Memory Pressure / Heap Exhaustion",
            "default_service": "product-service",
            "expected_cause": "Memory leak causing high heap pressure and frequent GC pause degradation",
            "affected": ["product-service", "api-gateway"],
            "severity": "P2_HIGH"
        },
        "downstream_latency": {
            "name": "Downstream Payment Gateway Latency",
            "default_service": "payment-service",
            "expected_cause": "External 3rd-party banking partner API latency spike exceeding 3500ms timeout",
            "affected": ["payment-service", "checkout-service", "api-gateway"],
            "severity": "P2_HIGH"
        },
        "downstream_failure": {
            "name": "Downstream Service Outage (503 Service Unavailable)",
            "default_service": "payment-service",
            "expected_cause": "Payment provider authentication gateway throwing HTTP 503 Service Unavailable",
            "affected": ["payment-service", "checkout-service", "api-gateway"],
            "severity": "P1_CRITICAL"
        },
        "queue_backlog": {
            "name": "Asynchronous Order Processing Queue Backlog",
            "default_service": "order-service",
            "expected_cause": "Worker thread deadlocks causing order ingestion queue backlog > 10,000 items",
            "affected": ["order-service", "checkout-service"],
            "severity": "P3_MEDIUM"
        },
        "bad_deployment": {
            "name": "Bad Deployment / Missing Config Variable Regression",
            "default_service": "user-service",
            "expected_cause": "Deployment v2.4.1 introduced null-pointer exception on missing JWT_SECRET_KEY env var",
            "affected": ["user-service", "api-gateway"],
            "severity": "P1_CRITICAL"
        }
    }

    def __init__(self):
        self._active_faults: Dict[str, ActiveFault] = {}
        self._history: List[ActiveFault] = []

    def inject_fault(
        self,
        fault_type: str,
        target_service_id: Optional[str] = None,
        intensity: float = 0.8,
        duration_seconds: int = 180,
        parameters: Optional[Dict[str, Any]] = None,
    ) -> ActiveFault:
        if fault_type not in self.FAULT_DEFINITIONS:
            raise ValueError(f"Unknown fault type: {fault_type}. Supported: {list(self.FAULT_DEFINITIONS.keys())}")

        definition = self.FAULT_DEFINITIONS[fault_type]
        svc_id = target_service_id or definition["default_service"]
        fault_id = f"fault-{int(time.time())}-{fault_type[:6]}"

        fault = ActiveFault(
            id=fault_id,
            fault_type=fault_type,
            target_service_id=svc_id,
            intensity=max(0.1, min(1.0, intensity)),
            duration_seconds=duration_seconds,
            started_at=time.time(),
            parameters=parameters or {},
            expected_root_cause=definition["expected_cause"],
            expected_affected_services=definition["affected"],
        )

        self._active_faults[fault_id] = fault
        self._history.append(fault)
        return fault

    def stop_fault(self, fault_id: str) -> Optional[ActiveFault]:
        fault = self._active_faults.pop(fault_id, None)
        return fault

    def stop_all_faults(self) -> List[ActiveFault]:
        stopped = list(self._active_faults.values())
        self._active_faults.clear()
        return stopped

    def get_active_faults(self) -> List[ActiveFault]:
        # Filter out expired faults
        active = []
        for fid, fault in list(self._active_faults.items()):
            if fault.is_expired:
                self._active_faults.pop(fid, None)
            else:
                active.append(fault)
        return active

    def get_fault_for_service(self, service_id: str) -> Optional[ActiveFault]:
        for fault in self.get_active_faults():
            if fault.target_service_id == service_id:
                return fault
        return None

    def get_history(self, limit: int = 50) -> List[ActiveFault]:
        return list(reversed(self._history[-limit:]))


# Global Singleton
fault_engine = FaultEngine()
