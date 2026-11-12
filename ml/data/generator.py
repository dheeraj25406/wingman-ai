import numpy as np
import pandas as pd
from typing import Tuple, List, Dict, Any

from ml.features.extractor import FEATURE_NAMES, feature_extractor
from ml.classification.classifier import REV_CLASS_MAPPING


def generate_experiment_dataset(num_runs_per_class: int = 15, samples_per_run: int = 20, random_seed: int = 42) -> pd.DataFrame:
    """
    Generates a realistic, reproducible dataset of telemetry telemetry windows.
    Data is organized into distinct experiment runs with run_id, enabling group-aware splits.
    """
    np.random.seed(random_seed)
    rows = []

    services = ["order-service", "checkout-service", "payment-service", "user-service", "product-service"]

    # Class 0: NORMAL
    for run_idx in range(num_runs_per_class):
        run_id = f"run-normal-{run_idx:03d}"
        for s in range(samples_per_run):
            svc = np.random.choice(services)
            cpu = np.random.normal(20.0, 3.0)
            mem = np.random.normal(35.0, 4.0)
            rps = np.random.normal(15.0, 2.0)
            err = np.random.exponential(0.002)
            p50 = np.random.normal(25.0, 4.0)
            p95 = np.random.normal(55.0, 8.0)
            p99 = np.random.normal(85.0, 12.0)
            db_conn = np.random.normal(15.0, 3.0)
            queue = np.random.normal(5.0, 2.0)
            timeout = 0.0

            row = {
                "run_id": run_id,
                "service_id": svc,
                "cpu_utilization": np.clip(cpu, 5.0, 100.0),
                "memory_utilization": np.clip(mem, 10.0, 100.0),
                "request_rate": max(1.0, rps),
                "error_rate": np.clip(err, 0.0, 1.0),
                "latency_p50": max(5.0, p50),
                "latency_p95": max(10.0, p95),
                "latency_p99": max(15.0, p99),
                "db_connections": np.clip(db_conn, 0.0, 100.0),
                "queue_depth": max(0.0, queue),
                "timeout_rate": timeout,
                "label": 0,
                "label_name": "NORMAL",
            }
            rows.append(row)

    # Fault Classes 1 to 6
    fault_classes = [
        ("DB_POOL_EXHAUSTION", 1, "order-service"),
        ("CPU_SATURATION", 2, "checkout-service"),
        ("MEMORY_PRESSURE", 3, "product-service"),
        ("DOWNSTREAM_API_FAILURE", 4, "payment-service"),
        ("QUEUE_BACKLOG", 5, "order-service"),
        ("DEPLOYMENT_REGRESSION", 6, "user-service"),
    ]

    for class_name, label_id, primary_svc in fault_classes:
        for run_idx in range(num_runs_per_class):
            run_id = f"run-{class_name.lower()}-{run_idx:03d}"
            intensity = np.random.uniform(0.6, 1.0)

            for s in range(samples_per_run):
                # Baseline
                cpu = np.random.normal(22.0, 3.0)
                mem = np.random.normal(35.0, 4.0)
                rps = np.random.normal(15.0, 2.0)
                err = np.random.exponential(0.003)
                p50 = np.random.normal(25.0, 4.0)
                p95 = np.random.normal(55.0, 8.0)
                p99 = np.random.normal(85.0, 12.0)
                db_conn = np.random.normal(15.0, 3.0)
                queue = np.random.normal(5.0, 2.0)
                timeout = 0.0

                # Injected signatures
                if label_id == 1:  # DB_POOL_EXHAUSTION
                    db_conn = np.random.normal(98.0, 1.5)
                    err = np.random.uniform(0.4, 0.8) * intensity
                    p95 = np.random.normal(2600.0, 250.0) * intensity
                    p99 = p95 + 800.0
                    timeout = np.random.uniform(0.2, 0.5) * intensity
                elif label_id == 2:  # CPU_SATURATION
                    cpu = np.random.normal(96.0, 2.0)
                    p95 = np.random.normal(1500.0, 200.0) * intensity
                    p99 = p95 + 700.0
                elif label_id == 3:  # MEMORY_PRESSURE
                    mem = np.random.normal(95.0, 2.0)
                    p95 = np.random.normal(1200.0, 150.0) * intensity
                    err = np.random.uniform(0.1, 0.3) * intensity
                elif label_id == 4:  # DOWNSTREAM_API_FAILURE
                    err = np.random.uniform(0.7, 0.95) * intensity
                    p95 = np.random.normal(3200.0, 300.0) * intensity
                    timeout = np.random.uniform(0.3, 0.6) * intensity
                elif label_id == 5:  # QUEUE_BACKLOG
                    queue = np.random.normal(11000.0, 1200.0) * intensity
                    p95 = np.random.normal(900.0, 100.0) * intensity
                elif label_id == 6:  # DEPLOYMENT_REGRESSION
                    err = np.random.uniform(0.85, 0.99) * intensity
                    p95 = np.random.normal(45.0, 6.0)

                row = {
                    "run_id": run_id,
                    "service_id": primary_svc,
                    "cpu_utilization": np.clip(cpu, 0.0, 100.0),
                    "memory_utilization": np.clip(mem, 0.0, 100.0),
                    "request_rate": max(1.0, rps),
                    "error_rate": np.clip(err, 0.0, 1.0),
                    "latency_p50": max(5.0, p50),
                    "latency_p95": max(10.0, p95),
                    "latency_p99": max(15.0, p99),
                    "db_connections": np.clip(db_conn, 0.0, 100.0),
                    "queue_depth": max(0.0, queue),
                    "timeout_rate": np.clip(timeout, 0.0, 1.0),
                    "label": label_id,
                    "label_name": class_name,
                }
                rows.append(row)

    df_raw = pd.DataFrame(rows)
    return df_raw
