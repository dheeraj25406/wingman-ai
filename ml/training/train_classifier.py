import os
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit
import mlflow

from ml.data.generator import generate_experiment_dataset
from ml.features.extractor import feature_extractor
from ml.classification.classifier import IncidentClassifier, CLASS_MAPPING


def train_classifier_model():
    print("[ML] Generating multi-class fault experiment dataset...")
    df = generate_experiment_dataset(num_runs_per_class=25, samples_per_run=25)
    print(f"[ML] Total dataset size: {len(df)} samples across {df['run_id'].nunique()} distinct experiment runs.")

    records = df.to_dict(orient="records")
    X_df = feature_extractor.extract_dataframe(records)
    X = X_df.values
    y = df["label"].values
    groups = df["run_id"].values

    # Group-aware splitting: all samples from a single experiment run stay together
    gss = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=42)
    train_idx, val_idx = next(gss.split(X, y, groups=groups))

    X_train, y_train = X[train_idx], y[train_idx]
    X_val, y_val = X[val_idx], y[val_idx]

    print(f"[ML] Group-split: Train={len(X_train)} samples ({len(np.unique(groups[train_idx]))} runs), Val={len(X_val)} samples ({len(np.unique(groups[val_idx]))} runs)")

    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"
    mlflow.set_tracking_uri("sqlite:///mlflow.db")
    mlflow.set_experiment("wingman_incident_classifier")

    with mlflow.start_run(run_name="lightgbm_v1"):
        classifier = IncidentClassifier()
        print("[ML] Fitting LightGBM & baseline Random Forest...")
        classifier.train(X_train, y_train, X_val, y_val)

        macro_f1 = classifier.metrics_cache["lgbm_macro_f1"]
        rf_f1 = classifier.metrics_cache["rf_baseline_macro_f1"]

        print(f"[ML] LightGBM Validation Macro-F1: {macro_f1:.4f}")
        print(f"[ML] Random Forest Baseline Macro-F1: {rf_f1:.4f}")

        mlflow.log_metric("val_macro_f1", macro_f1)
        mlflow.log_metric("baseline_rf_macro_f1", rf_f1)
        mlflow.log_param("model_type", "LightGBM")
        mlflow.log_param("num_classes", len(CLASS_MAPPING))

        artifact_path = "ml/artifacts/lightgbm_model.joblib"
        classifier.save(artifact_path)
        print(f"[ML] Saved LightGBM classifier artifact to {artifact_path}")

    return classifier


if __name__ == "__main__":
    train_classifier_model()
