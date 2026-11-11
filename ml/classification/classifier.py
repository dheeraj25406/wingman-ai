import os
import joblib
import numpy as np
from typing import Dict, List, Any, Optional
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, confusion_matrix, f1_score

from ml.features.extractor import FEATURE_NAMES


CLASS_MAPPING = {
    0: "NORMAL",
    1: "DB_POOL_EXHAUSTION",
    2: "CPU_SATURATION",
    3: "MEMORY_PRESSURE",
    4: "DOWNSTREAM_API_FAILURE",
    5: "QUEUE_BACKLOG",
    6: "DEPLOYMENT_REGRESSION",
}

REV_CLASS_MAPPING = {v: k for k, v in CLASS_MAPPING.items()}


class IncidentClassifier:
    """
    Supervised Incident Classifier trained on controlled fault injections.
    Predicts the exact category of production failure using LightGBM.
    """

    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[LGBMClassifier] = None
        self.baseline_rf: Optional[RandomForestClassifier] = None
        self.version: str = "v1.0.0"
        self.feature_names = FEATURE_NAMES
        self.classes = CLASS_MAPPING
        self.metrics_cache: Dict[str, Any] = {}

        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def train(self, X_train: np.ndarray, y_train: np.ndarray, X_val: np.ndarray, y_val: np.ndarray):
        # 1. Train LightGBM
        self.model = LGBMClassifier(
            n_estimators=100,
            learning_rate=0.05,
            num_leaves=31,
            random_state=42,
            n_jobs=-1,
            verbosity=-1,
        )
        self.model.fit(X_train, y_train)

        # 2. Train baseline Random Forest for comparison
        self.baseline_rf = RandomForestClassifier(
            n_estimators=50,
            random_state=42,
            n_jobs=-1,
        )
        self.baseline_rf.fit(X_train, y_train)

        # 3. Compute metrics on validation set
        y_pred = self.model.predict(X_val)
        y_pred_rf = self.baseline_rf.predict(X_val)

        lgbm_f1 = float(f1_score(y_val, y_pred, average="macro", zero_division=0))
        rf_f1 = float(f1_score(y_val, y_pred_rf, average="macro", zero_division=0))
        cm = confusion_matrix(y_val, y_pred).tolist()

        # Feature importance
        importances = self.model.feature_importances_
        feature_imp = [
            {"feature": feat, "importance": float(imp)}
            for feat, imp in zip(self.feature_names, importances)
        ]
        feature_imp.sort(key=lambda x: x["importance"], reverse=True)

        self.metrics_cache = {
            "lgbm_macro_f1": round(lgbm_f1, 4),
            "rf_baseline_macro_f1": round(rf_f1, 4),
            "confusion_matrix": cm,
            "feature_importance": feature_imp,
            "class_names": list(CLASS_MAPPING.values()),
        }

    def predict(self, vector: np.ndarray) -> Dict[str, Any]:
        """
        Takes a 1D feature vector and returns predicted class and probability distribution.
        """
        if self.model is None:
            return self._heuristic_fallback(vector)

        X = vector.reshape(1, -1)
        pred_class_idx = int(self.model.predict(X)[0])
        probabilities = self.model.predict_proba(X)[0]

        pred_name = CLASS_MAPPING.get(pred_class_idx, "UNKNOWN")
        prob_dict = {
            CLASS_MAPPING.get(i, f"CLASS_{i}"): round(float(prob), 4)
            for i, prob in enumerate(probabilities)
        }

        return {
            "predicted_class": pred_name,
            "confidence": round(float(probabilities[pred_class_idx]), 4),
            "class_probabilities": prob_dict,
            "model_version": self.version,
        }

    def _heuristic_fallback(self, vector: np.ndarray) -> Dict[str, Any]:
        cpu = vector[0]
        mem = vector[1]
        err = vector[3]
        p95 = vector[5]
        db_conn = vector[7]
        queue = vector[8]

        pred = "NORMAL"
        confidence = 0.90

        if db_conn > 80:
            pred = "DB_POOL_EXHAUSTION"
            confidence = 0.96
        elif cpu > 85:
            pred = "CPU_SATURATION"
            confidence = 0.94
        elif mem > 85:
            pred = "MEMORY_PRESSURE"
            confidence = 0.92
        elif queue > 5000:
            pred = "QUEUE_BACKLOG"
            confidence = 0.89
        elif err > 0.4 and p95 > 1000:
            pred = "DOWNSTREAM_API_FAILURE"
            confidence = 0.88
        elif err > 0.5:
            pred = "DEPLOYMENT_REGRESSION"
            confidence = 0.85

        probs = {name: (confidence if name == pred else (1 - confidence) / 6.0) for name in CLASS_MAPPING.values()}
        return {
            "predicted_class": pred,
            "confidence": round(confidence, 4),
            "class_probabilities": {k: round(v, 4) for k, v in probs.items()},
            "model_version": "heuristic-rule-baseline",
        }

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "baseline_rf": self.baseline_rf,
            "version": self.version,
            "metrics": self.metrics_cache,
        }, filepath)

    def load(self, filepath: str):
        data = joblib.load(filepath)
        self.model = data["model"]
        self.baseline_rf = data.get("baseline_rf")
        self.version = data.get("version", "v1.0.0")
        self.metrics_cache = data.get("metrics", {})


incident_classifier = IncidentClassifier()
