import os
import joblib
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from ml.data.generator import generate_experiment_dataset
from ml.features.extractor import feature_extractor
from ml.anomaly_detection.isolation_forest import AnomalyDetector


def train_anomaly_model():
    print("[ML] Generating synthetic normal telemetry dataset...")
    df = generate_experiment_dataset(num_runs_per_class=20, samples_per_run=30)
    normal_df = df[df["label"] == 0].copy()

    print(f"[ML] Extracted {len(normal_df)} normal telemetry samples for unsupervised training.")
    records = normal_df.to_dict(orient="records")
    X_df = feature_extractor.extract_dataframe(records)
    X = X_df.values

    X_train, X_test = train_test_split(X, test_size=0.2, random_state=42)

    detector = AnomalyDetector()
    print("[ML] Fitting Isolation Forest on normal baseline...")
    detector.train(X_train, contamination=0.03, random_state=42)

    # Validate false positive rate on normal test split
    false_positives = 0
    scores = []
    for vec in X_test:
        res = detector.predict_anomaly(vec)
        scores.append(res["anomaly_score"])
        if res["is_anomaly"]:
            false_positives += 1

    fpr = false_positives / len(X_test)
    print(f"[ML] Training completed. Normal baseline FPR: {fpr:.2%} (Target < 3%)")
    print(f"[ML] Mean normal anomaly score: {np.mean(scores):.4f}")

    artifact_path = "ml/artifacts/isolation_forest.joblib"
    detector.save(artifact_path)
    print(f"[ML] Saved Isolation Forest artifact to {artifact_path}")
    return detector


if __name__ == "__main__":
    train_anomaly_model()
