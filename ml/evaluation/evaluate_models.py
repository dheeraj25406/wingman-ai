import os
import json
import numpy as np
import pandas as pd
from sklearn.metrics import classification_report, f1_score, precision_score, recall_score, confusion_matrix

from ml.data.generator import generate_experiment_dataset
from ml.features.extractor import feature_extractor
from ml.anomaly_detection.isolation_forest import AnomalyDetector
from ml.classification.classifier import IncidentClassifier, CLASS_MAPPING


def evaluate_models():
    print("=" * 70)
    print(" Wingman AI — ML Model Benchmark & Comparison Suite")
    print("=" * 70)

    # Load or instantiate models
    anomaly_path = "ml/artifacts/isolation_forest.joblib"
    classifier_path = "ml/artifacts/lightgbm_model.joblib"

    if os.path.exists(anomaly_path):
        anomaly_model = AnomalyDetector(anomaly_path)
        print(f"[EVAL] Loaded Isolation Forest from {anomaly_path}")
    else:
        print("[EVAL] Artifact not found, running inline train...")
        from ml.training.train_anomaly import train_anomaly_model
        anomaly_model = train_anomaly_model()

    if os.path.exists(classifier_path):
        classifier_model = IncidentClassifier(classifier_path)
        print(f"[EVAL] Loaded LightGBM from {classifier_path}")
    else:
        print("[EVAL] Artifact not found, running inline train...")
        from ml.training.train_classifier import train_classifier_model
        classifier_model = train_classifier_model()

    # Generate strictly held-out test evaluation runs
    print("[EVAL] Generating held-out test runs (random_seed=999)...")
    test_df = generate_experiment_dataset(num_runs_per_class=10, samples_per_run=20, random_seed=999)
    records = test_df.to_dict(orient="records")
    X_df = feature_extractor.extract_dataframe(records)
    X_test = X_df.values
    y_true_multi = test_df["label"].values
    y_true_binary = (y_true_multi > 0).astype(int)  # 0: normal, 1: incident

    # 1. Static Threshold Heuristic Baseline
    y_pred_threshold = []
    for r in records:
        is_alert = (
            r["error_rate"] > 0.05
            or r["latency_p95"] > 600.0
            or r["cpu_utilization"] > 90.0
            or r["db_connections"] > 85.0
            or r["queue_depth"] > 3000.0
        )
        y_pred_threshold.append(1 if is_alert else 0)
    y_pred_threshold = np.array(y_pred_threshold)

    # 2. Isolation Forest Unsupervised Anomaly Detector
    y_pred_if = []
    if_scores = []
    for vec in X_test:
        res = anomaly_model.predict_anomaly(vec)
        y_pred_if.append(1 if res["is_anomaly"] else 0)
        if_scores.append(res["anomaly_score"])
    y_pred_if = np.array(y_pred_if)

    # 3. LightGBM Supervised Classifier
    y_pred_lgbm = []
    lgbm_confidences = []
    for vec in X_test:
        res = classifier_model.predict(vec)
        # Map predicted name back to int
        rev = {v: k for k, v in CLASS_MAPPING.items()}
        y_pred_lgbm.append(rev.get(res["predicted_class"], 0))
        lgbm_confidences.append(res["confidence"])
    y_pred_lgbm = np.array(y_pred_lgbm)

    # Compute binary anomaly metrics
    print("\n" + "-" * 70)
    print(" DETECTION PERFORMANCE (Binary: Normal vs Incident)")
    print("-" * 70)
    print(f"{'Method':<30} | {'Precision':<10} | {'Recall':<10} | {'F1-Score':<10}")
    print("-" * 70)

    p_th = precision_score(y_true_binary, y_pred_threshold, zero_division=0)
    r_th = recall_score(y_true_binary, y_pred_threshold, zero_division=0)
    f1_th = f1_score(y_true_binary, y_pred_threshold, zero_division=0)
    print(f"{'Static Heuristic Thresholds':<30} | {p_th:<10.4f} | {r_th:<10.4f} | {f1_th:<10.4f}")

    p_if = precision_score(y_true_binary, y_pred_if, zero_division=0)
    r_if = recall_score(y_true_binary, y_pred_if, zero_division=0)
    f1_if = f1_score(y_true_binary, y_pred_if, zero_division=0)
    print(f"{'Isolation Forest (Ours)':<30} | {p_if:<10.4f} | {r_if:<10.4f} | {f1_if:<10.4f}")

    # Compute multi-class classification metrics
    print("\n" + "-" * 70)
    print(" CLASSIFICATION PERFORMANCE (7-Class LightGBM Classifier)")
    print("-" * 70)
    macro_f1 = f1_score(y_true_multi, y_pred_lgbm, average="macro", zero_division=0)
    macro_p = precision_score(y_true_multi, y_pred_lgbm, average="macro", zero_division=0)
    macro_r = recall_score(y_true_multi, y_pred_lgbm, average="macro", zero_division=0)
    print(f"Overall Macro Precision: {macro_p:.4f}")
    print(f"Overall Macro Recall:    {macro_r:.4f}")
    print(f"Overall Macro F1-Score:  {macro_f1:.4f}")

    report = classification_report(y_true_multi, y_pred_lgbm, target_names=list(CLASS_MAPPING.values()), zero_division=0)
    print("\nPer-Class Breakdown:")
    print(report)

    cm = confusion_matrix(y_true_multi, y_pred_lgbm).tolist()
    results = {
        "binary_detection": {
            "threshold": {"precision": round(p_th, 4), "recall": round(r_th, 4), "f1": round(f1_th, 4)},
            "isolation_forest": {"precision": round(p_if, 4), "recall": round(r_if, 4), "f1": round(f1_if, 4)},
        },
        "multiclass_classification": {
            "macro_precision": round(macro_p, 4),
            "macro_recall": round(macro_r, 4),
            "macro_f1": round(macro_f1, 4),
            "confusion_matrix": cm,
            "classes": list(CLASS_MAPPING.values()),
        }
    }

    os.makedirs("ml/artifacts", exist_ok=True)
    with open("ml/artifacts/evaluation_report.json", "w") as f:
        json.dump(results, f, indent=2)

    print("[EVAL] Saved evaluation report to ml/artifacts/evaluation_report.json")
    return results


if __name__ == "__main__":
    evaluate_models()
