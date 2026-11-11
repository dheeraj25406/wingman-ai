import numpy as np
import pandas as pd
from typing import Dict, List, Any, Optional


FEATURE_NAMES = [
    "cpu_utilization",
    "memory_utilization",
    "request_rate",
    "error_rate",
    "latency_p50",
    "latency_p95",
    "latency_p99",
    "db_connections",
    "queue_depth",
    "timeout_rate",
    "cpu_rolling_mean_ratio",
    "error_rate_delta",
    "latency_baseline_zscore",
]


class FeatureExtractor:
    """
    Transforms raw telemetry time-series points into normalized, 13-dimensional
    feature vectors with rolling statistics and deviation measures.
    """

    DEFAULT_BASELINES = {
        "api-gateway": {"p95_mean": 28.0, "p95_std": 4.0},
        "user-service": {"p95_mean": 20.0, "p95_std": 3.0},
        "product-service": {"p95_mean": 32.0, "p95_std": 5.0},
        "checkout-service": {"p95_mean": 65.0, "p95_std": 8.0},
        "payment-service": {"p95_mean": 90.0, "p95_std": 12.0},
        "order-service": {"p95_mean": 70.0, "p95_std": 10.0},
    }

    def extract_vector(self, current_point: Dict[str, Any], history_points: Optional[List[Dict[str, Any]]] = None) -> np.ndarray:
        history = history_points or []
        service_id = current_point.get("service_id", "unknown")

        cpu = float(current_point.get("cpu_utilization", 20.0))
        mem = float(current_point.get("memory_utilization", 30.0))
        rps = float(current_point.get("request_rate", 10.0))
        err = float(current_point.get("error_rate", 0.001))
        p50 = float(current_point.get("latency_p50", 25.0))
        p95 = float(current_point.get("latency_p95", 50.0))
        p99 = float(current_point.get("latency_p99", 80.0))
        db_conn = float(current_point.get("db_connections", 10.0))
        queue = float(current_point.get("queue_depth", 5.0))
        timeout = float(current_point.get("timeout_rate", 0.0))

        # Rolling statistics
        if len(history) >= 2:
            prev_cpus = [float(p.get("cpu_utilization", cpu)) for p in history[-5:]]
            cpu_mean = np.mean(prev_cpus) if prev_cpus else cpu
            cpu_ratio = cpu / (cpu_mean + 1e-4)

            prev_err = float(history[-1].get("error_rate", err))
            err_delta = err - prev_err
        else:
            cpu_ratio = 1.0
            err_delta = 0.0

        # Z-score baseline deviation
        baseline = self.DEFAULT_BASELINES.get(service_id, {"p95_mean": 50.0, "p95_std": 10.0})
        p95_zscore = (p95 - baseline["p95_mean"]) / (baseline["p95_std"] + 1e-4)

        vector = [
            cpu,
            mem,
            rps,
            err,
            p50,
            p95,
            p99,
            db_conn,
            queue,
            timeout,
            cpu_ratio,
            err_delta,
            p95_zscore,
        ]
        return np.array(vector, dtype=np.float32)

    def extract_dataframe(self, points: List[Dict[str, Any]]) -> pd.DataFrame:
        vectors = []
        for i, pt in enumerate(points):
            hist = points[max(0, i - 5):i]
            vec = self.extract_vector(pt, hist)
            vectors.append(vec)
        return pd.DataFrame(vectors, columns=FEATURE_NAMES)


feature_extractor = FeatureExtractor()
