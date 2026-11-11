import time
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set, Tuple, Any

from simulator.telemetry.buffer import telemetry_buffer
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier
from ml.features.extractor import feature_extractor


SERVICE_DEPENDENCY_GRAPH = {
    "api-gateway": ["user-service", "product-service", "checkout-service"],
    "checkout-service": ["payment-service", "order-service"],
    "order-service": ["database"],
    "user-service": [],
    "product-service": [],
    "payment-service": [],
    "database": [],
}

# Reverse mapping: who depends on whom
UPSTREAM_MAP = {
    "user-service": ["api-gateway"],
    "product-service": ["api-gateway"],
    "checkout-service": ["api-gateway"],
    "payment-service": ["checkout-service"],
    "order-service": ["checkout-service"],
    "database": ["order-service"],
    "api-gateway": [],
}


class IncidentCorrelationEngine:
    """
    Deterministic correlation engine that processes telemetry anomaly signals,
    groups alerts within a sliding temporal window, traverses service dependency
    topologies to identify the primary failure source vs propagated degradation,
    and constructs evidence-grounded incident candidates.
    """

    def __init__(self, correlation_window_seconds: int = 180):
        self.correlation_window = correlation_window_seconds
        self._active_incident_cache: Dict[str, Dict[str, Any]] = {}

    def scan_for_anomalies(self) -> List[Dict[str, Any]]:
        """
        Scans all monitored services for telemetry anomalies using Isolation Forest.
        Returns a list of detected anomalous service signals with abnormal features.
        """
        detected_anomalies = []
        latest_metrics = telemetry_buffer.get_all_latest_metrics()

        for service_id, metric_pt in latest_metrics.items():
            history = telemetry_buffer.get_service_metrics(service_id, limit=10)
            vector = feature_extractor.extract_vector(metric_pt, history)

            res = anomaly_detector.predict_anomaly(vector)
            if res["is_anomaly"]:
                # Run supervised classifier to predict category
                class_res = incident_classifier.predict(vector)

                detected_anomalies.append({
                    "service_id": service_id,
                    "timestamp": metric_pt.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "epoch": metric_pt.get("epoch", time.time()),
                    "anomaly_score": res["anomaly_score"],
                    "threshold": res["threshold"],
                    "abnormal_features": res["abnormal_features"],
                    "predicted_class": class_res["predicted_class"],
                    "confidence": class_res["confidence"],
                    "raw_vector": vector.tolist(),
                    "metric_snapshot": metric_pt,
                })

        return detected_anomalies

    def correlate_incidents(self, anomalies: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Groups anomalies that occur within the correlation window and share dependency paths.
        Determines the primary affected service and propagated downstream services.
        """
        if not anomalies:
            return None

        # Sort anomalies by timestamp to find the earliest signal
        anomalies_sorted = sorted(anomalies, key=lambda x: x["epoch"])
        earliest = anomalies_sorted[0]

        all_affected_services = list({a["service_id"] for a in anomalies})

        # Dependency graph traversal to find the root service
        # A service S is more fundamental (root) if other affected services depend on it
        primary_service = earliest["service_id"]

        # If multiple services anomalous, check who is deepest in the dependency DAG
        for candidate in all_affected_services:
            # Does any other affected service depend on candidate?
            dependents = self._get_transitive_dependents(candidate)
            other_affected = set(all_affected_services) - {candidate}
            if dependents.intersection(other_affected):
                primary_service = candidate
                break

        # Compute propagation path
        propagation_path = self._build_propagation_path(primary_service, all_affected_services)

        # Primary classification category
        primary_anomaly = next((a for a in anomalies if a["service_id"] == primary_service), earliest)

        incident_title = f"{primary_anomaly['predicted_class'].replace('_', ' ').title()} on {primary_service}"
        severity = "P1_CRITICAL" if primary_anomaly["predicted_class"] in ["DB_POOL_EXHAUSTION", "DOWNSTREAM_API_FAILURE", "DEPLOYMENT_REGRESSION"] else "P2_HIGH"

        return {
            "title": incident_title,
            "severity": severity,
            "primary_service_id": primary_service,
            "affected_service_ids": all_affected_services,
            "propagation_path": propagation_path,
            "detection_source": "ISOLATION_FOREST + LIGHTGBM",
            "detected_at": datetime.now(timezone.utc).isoformat(),
            "predicted_category": primary_anomaly["predicted_class"],
            "ml_confidence": primary_anomaly["confidence"],
            "anomalies": anomalies_sorted,
        }

    def _get_transitive_dependents(self, service_id: str) -> Set[str]:
        """Finds all services that depend (directly or indirectly) on service_id."""
        dependents = set()
        queue = [service_id]
        while queue:
            curr = queue.pop(0)
            upstreams = UPSTREAM_MAP.get(curr, [])
            for u in upstreams:
                if u not in dependents:
                    dependents.add(u)
                    queue.append(u)
        return dependents

    def _build_propagation_path(self, root_service: str, affected_services: List[str]) -> List[str]:
        path = [root_service]
        curr = root_service
        visited = {root_service}
        while True:
            upstreams = [u for u in UPSTREAM_MAP.get(curr, []) if u in affected_services and u not in visited]
            if not upstreams:
                break
            next_hop = upstreams[0]
            path.append(next_hop)
            visited.add(next_hop)
            curr = next_hop
        return path


correlation_engine = IncidentCorrelationEngine()
