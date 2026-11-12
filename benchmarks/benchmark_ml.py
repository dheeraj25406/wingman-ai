import os
import sys
import time
import json
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple
from sklearn.metrics import (
    precision_score,
    recall_score,
    f1_score,
    confusion_matrix,
    classification_report,
)
from sklearn.linear_model import LogisticRegression
from sklearn.dummy import DummyClassifier
from sklearn.ensemble import RandomForestClassifier

from ml.data.generator import generate_experiment_dataset
from ml.features.extractor import feature_extractor, FEATURE_NAMES
from ml.anomaly_detection.isolation_forest import AnomalyDetector
from ml.classification.classifier import IncidentClassifier, CLASS_MAPPING, REV_CLASS_MAPPING


def prepare_datasets(random_seed: int = 42) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, list]:
    """
    Generates reproducible Train, Validation, and Test sets using group-aware run splits.
    Ensures zero data leakage between splits.
    """
    # 70% Train (14 runs per class), 15% Val (3 runs per class), 15% Test (3 runs per class)
    train_df = generate_experiment_dataset(num_runs_per_class=14, samples_per_run=25, random_seed=random_seed)
    val_df = generate_experiment_dataset(num_runs_per_class=3, samples_per_run=25, random_seed=random_seed + 1)
    test_df = generate_experiment_dataset(num_runs_per_class=3, samples_per_run=25, random_seed=random_seed + 2)

    X_train = feature_extractor.extract_dataframe(train_df.to_dict(orient="records")).values
    y_train = train_df["label"].values

    X_val = feature_extractor.extract_dataframe(val_df.to_dict(orient="records")).values
    y_val = val_df["label"].values

    test_records = test_df.to_dict(orient="records")
    X_test = feature_extractor.extract_dataframe(test_records).values
    y_test = test_df["label"].values

    return X_train, y_train, X_val, y_val, X_test, y_test, test_records


def benchmark_anomaly_detection(X_train, y_train, X_val, y_val, X_test, y_test, test_records, if_threshold=0.52, calibrate=False) -> Dict[str, Any]:
    """
    Compares Isolation Forest against 3-Sigma Z-Score and Static Threshold baselines.
    """
    y_true_binary = (y_test > 0).astype(int)

    # 1. Baseline: Static Heuristic Thresholds
    y_pred_static = []
    for r in test_records:
        is_alert = (
            r["error_rate"] > 0.05
            or r["latency_p95"] > 600.0
            or r["cpu_utilization"] > 90.0
            or r["db_connections"] > 85.0
            or r["queue_depth"] > 3000.0
        )
        y_pred_static.append(1 if is_alert else 0)
    y_pred_static = np.array(y_pred_static)

    # 2. Baseline: 3-Sigma Z-Score Statistical Anomaly Detector
    # Feature index 12 is 'latency_baseline_zscore'
    y_pred_zscore = []
    for vec in X_test:
        z_score = abs(vec[12]) if len(vec) > 12 else 0.0
        # Alert if latency z-score > 3.0 or extreme CPU/memory/connections
        is_z_anomaly = (
            z_score > 3.0
            or vec[0] > 90.0  # cpu
            or vec[7] > 85.0  # db_connections
            or vec[8] > 3000.0  # queue_depth
        )
        y_pred_zscore.append(1 if is_z_anomaly else 0)
    y_pred_zscore = np.array(y_pred_zscore)

    # 3. Isolation Forest (Unsupervised)
    detector = AnomalyDetector()
    detector.threshold = if_threshold
    detector.train(X_train[y_train == 0])  # Train on clean normal baseline data
    if calibrate:
        detector.calibrate_threshold(X_val, y_val)

    y_pred_if = []
    latencies = []
    for vec in X_test:
        t0 = time.perf_counter()
        res = detector.predict_anomaly(vec)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        y_pred_if.append(1 if res["is_anomaly"] else 0)
    y_pred_if = np.array(y_pred_if)

    def calc_metrics(y_true, y_pred):
        cm = confusion_matrix(y_true, y_pred)
        tn, fp, fn, tp = cm.ravel()
        p = precision_score(y_true, y_pred, zero_division=0)
        r = recall_score(y_true, y_pred, zero_division=0)
        f1 = f1_score(y_true, y_pred, zero_division=0)
        fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
        fnr = fn / (fn + tp) if (fn + tp) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        return {
            "precision": round(float(p), 4),
            "recall": round(float(r), 4),
            "f1_score": round(float(f1), 4),
            "specificity": round(float(specificity), 4),
            "false_positive_rate": round(float(fpr), 4),
            "false_negative_rate": round(float(fnr), 4),
            "true_positives": int(tp),
            "false_positives": int(fp),
            "true_negatives": int(tn),
            "false_negatives": int(fn),
        }

    return {
        "static_threshold": calc_metrics(y_true_binary, y_pred_static),
        "zscore_detector": calc_metrics(y_true_binary, y_pred_zscore),
        "isolation_forest": {
            **calc_metrics(y_true_binary, y_pred_if),
            "threshold": if_threshold,
            "inference_latency_ms": {
                "mean": round(float(np.mean(latencies)), 4),
                "p50": round(float(np.percentile(latencies, 50)), 4),
                "p95": round(float(np.percentile(latencies, 95)), 4),
                "p99": round(float(np.percentile(latencies, 99)), 4),
            },
        },
    }


def benchmark_incident_classification(X_train, y_train, X_val, y_val, X_test, y_test) -> Dict[str, Any]:
    """
    Compares LightGBM Multi-class Classifier against Dummy, Logistic Regression, and Random Forest baselines.
    """
    results = {}

    # 1. Baseline: Dummy Classifier (Most Frequent)
    dummy = DummyClassifier(strategy="most_frequent")
    dummy.fit(X_train, y_train)
    y_pred_dummy = dummy.predict(X_test)
    results["dummy_majority"] = {
        "macro_precision": round(float(precision_score(y_test, y_pred_dummy, average="macro", zero_division=0)), 4),
        "macro_recall": round(float(recall_score(y_test, y_pred_dummy, average="macro", zero_division=0)), 4),
        "macro_f1": round(float(f1_score(y_test, y_pred_dummy, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_test, y_pred_dummy, average="weighted", zero_division=0)), 4),
    }

    # 2. Baseline: Multinomial Logistic Regression
    lr = LogisticRegression(max_iter=1000, random_state=42)
    lr.fit(X_train, y_train)
    t0 = time.perf_counter()
    y_pred_lr = lr.predict(X_test)
    lr_latency = (time.perf_counter() - t0) / len(X_test) * 1000.0
    results["logistic_regression"] = {
        "macro_precision": round(float(precision_score(y_test, y_pred_lr, average="macro", zero_division=0)), 4),
        "macro_recall": round(float(recall_score(y_test, y_pred_lr, average="macro", zero_division=0)), 4),
        "macro_f1": round(float(f1_score(y_test, y_pred_lr, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_test, y_pred_lr, average="weighted", zero_division=0)), 4),
        "inference_latency_ms": round(float(lr_latency), 4),
    }

    # 3. Baseline: Random Forest Classifier
    rf = RandomForestClassifier(n_estimators=100, random_state=42, n_jobs=-1)
    rf.fit(X_train, y_train)
    t0 = time.perf_counter()
    y_pred_rf = rf.predict(X_test)
    rf_latency = (time.perf_counter() - t0) / len(X_test) * 1000.0
    results["random_forest"] = {
        "macro_precision": round(float(precision_score(y_test, y_pred_rf, average="macro", zero_division=0)), 4),
        "macro_recall": round(float(recall_score(y_test, y_pred_rf, average="macro", zero_division=0)), 4),
        "macro_f1": round(float(f1_score(y_test, y_pred_rf, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_test, y_pred_rf, average="weighted", zero_division=0)), 4),
        "inference_latency_ms": round(float(rf_latency), 4),
    }

    # 4. LightGBM Supervised Classifier
    classifier = IncidentClassifier()
    classifier.train(X_train, y_train, X_val, y_val)

    latencies = []
    y_pred_lgbm = []
    for vec in X_test:
        t0 = time.perf_counter()
        res = classifier.predict(vec)
        latencies.append((time.perf_counter() - t0) * 1000.0)
        y_pred_lgbm.append(REV_CLASS_MAPPING.get(res["predicted_class"], 0))
    y_pred_lgbm = np.array(y_pred_lgbm)

    cm = confusion_matrix(y_test, y_pred_lgbm).tolist()
    cr = classification_report(y_test, y_pred_lgbm, target_names=list(CLASS_MAPPING.values()), output_dict=True, zero_division=0)

    results["lightgbm"] = {
        "macro_precision": round(float(precision_score(y_test, y_pred_lgbm, average="macro", zero_division=0)), 4),
        "macro_recall": round(float(recall_score(y_test, y_pred_lgbm, average="macro", zero_division=0)), 4),
        "macro_f1": round(float(f1_score(y_test, y_pred_lgbm, average="macro", zero_division=0)), 4),
        "weighted_f1": round(float(f1_score(y_test, y_pred_lgbm, average="weighted", zero_division=0)), 4),
        "inference_latency_ms": {
            "mean": round(float(np.mean(latencies)), 4),
            "p50": round(float(np.percentile(latencies, 50)), 4),
            "p95": round(float(np.percentile(latencies, 95)), 4),
            "p99": round(float(np.percentile(latencies, 99)), 4),
        },
        "per_class": {cls: cr[cls] for cls in CLASS_MAPPING.values() if cls in cr},
        "confusion_matrix": cm,
        "classes": list(CLASS_MAPPING.values()),
    }

    return results


def run_ml_benchmark(output_filename: str = "ml_benchmark_baseline.json") -> Dict[str, Any]:
    print("=" * 70)
    print(" EXECUTING RIGOROUS ML BENCHMARK SUITE")
    print("=" * 70)
    X_train, y_train, X_val, y_val, X_test, y_test, test_records = prepare_datasets(random_seed=42)
    print(f"Dataset Partitioning: Train={len(X_train)} samples, Val={len(X_val)} samples, Held-Out Test={len(X_test)} samples")

    print("\n[1/2] Benchmarking Anomaly Detection Models...")
    calibrate_mode = "optimized" in output_filename
    ad_results = benchmark_anomaly_detection(X_train, y_train, X_val, y_val, X_test, y_test, test_records, calibrate=calibrate_mode)

    print("\n[2/2] Benchmarking Incident Classification Models...")
    clf_results = benchmark_incident_classification(X_train, y_train, X_val, y_val, X_test, y_test)

    final_results = {
        "metadata": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "train_samples": len(X_train),
            "val_samples": len(X_val),
            "test_samples": len(X_test),
            "feature_count": len(FEATURE_NAMES),
            "features": FEATURE_NAMES,
        },
        "anomaly_detection": ad_results,
        "classification": clf_results,
    }

    os.makedirs("benchmarks/results", exist_ok=True)
    out_path = os.path.join("benchmarks/results", output_filename)
    with open(out_path, "w") as f:
        json.dump(final_results, f, indent=2)

    print(f"\n[OK] Machine-readable benchmark saved to {out_path}")
    return final_results


if __name__ == "__main__":
    out_file = sys.argv[1] if len(sys.argv) > 1 else "ml_benchmark_baseline.json"
    run_ml_benchmark(out_file)
