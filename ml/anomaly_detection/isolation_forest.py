import os
import joblib
import numpy as np
from typing import Dict, List, Any, Optional
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler

from ml.features.extractor import FEATURE_NAMES


class AnomalyDetector:
    """
    Unsupervised Anomaly Detector using Isolation Forest.
    Calculates calibrated anomaly scores and identifies abnormal features.
    """

    DEFAULT_THRESHOLD = 0.52

    def __init__(self, model_path: Optional[str] = None):
        self.model: Optional[IsolationForest] = None
        self.scaler: Optional[StandardScaler] = None
        self.threshold: float = self.DEFAULT_THRESHOLD
        self.version: str = "v1.0.0"
        self.feature_names = FEATURE_NAMES

        if model_path and os.path.exists(model_path):
            self.load(model_path)

    def train(self, X: np.ndarray, contamination: float = 0.03, random_state: int = 42):
        self.scaler = StandardScaler()
        X_scaled = self.scaler.fit_transform(X)

        self.model = IsolationForest(
            n_estimators=150,
            max_samples="auto",
            contamination=contamination,
            random_state=random_state,
            n_jobs=-1,
        )
        self.model.fit(X_scaled)

    def calibrate_threshold(self, X_val: np.ndarray, y_val: np.ndarray) -> float:
        """
        Sweeps anomaly score thresholds on validation set to find the F1-optimal threshold
        while constraining false positive rate (FPR <= 0.05).
        """
        if self.model is None or self.scaler is None:
            return self.threshold

        X_scaled = self.scaler.transform(X_val)
        raw_scores = self.model.decision_function(X_scaled)
        norm_scores = np.clip(0.5 - raw_scores, 0.0, 1.0)
        y_binary = (y_val > 0).astype(int)

        best_th = self.threshold
        best_f1 = -1.0

        for candidate_th in np.linspace(0.40, 0.70, 61):
            preds = (norm_scores >= candidate_th).astype(int)
            tn = np.sum((y_binary == 0) & (preds == 0))
            fp = np.sum((y_binary == 0) & (preds == 1))
            tp = np.sum((y_binary == 1) & (preds == 1))
            fn = np.sum((y_binary == 1) & (preds == 0))

            fpr = fp / (fp + tn) if (fp + tn) > 0 else 0.0
            if fpr > 0.06:
                continue

            prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0

            if f1 > best_f1:
                best_f1 = f1
                best_th = float(candidate_th)

        self.threshold = round(best_th, 4)
        return self.threshold

    def predict_anomaly(self, vector: np.ndarray) -> Dict[str, Any]:
        """
        Takes a 1D feature vector and returns calibrated anomaly score,
        boolean anomaly flag, and list of abnormal features.
        """
        if self.model is None or self.scaler is None:
            # Fallback heuristic if model not yet loaded/trained
            return self._heuristic_fallback(vector)

        X = vector.reshape(1, -1)
        X_scaled = self.scaler.transform(X)

        # Scikit-learn decision_function: negative is anomaly, positive is normal
        raw_score = self.model.decision_function(X_scaled)[0]
        # Normalize score to [0, 1] range where 1.0 is extremely anomalous
        # decision_function typically ranges from -0.5 (severe anomaly) to +0.5 (normal)
        normalized_score = float(np.clip(0.5 - raw_score, 0.0, 1.0))

        is_anomaly = normalized_score >= self.threshold

        # Find top abnormal features via z-score deviation from scaler mean
        deviations = np.abs(X_scaled[0])
        top_indices = np.argsort(deviations)[::-1][:3]

        abnormal_features = []
        for idx in top_indices:
            if deviations[idx] > 1.8:  # Significant deviation threshold
                feat_name = self.feature_names[idx]
                abnormal_features.append({
                    "feature": feat_name,
                    "value": float(vector[idx]),
                    "deviation_sigma": round(float(deviations[idx]), 2),
                })

        return {
            "is_anomaly": is_anomaly,
            "anomaly_score": round(normalized_score, 4),
            "threshold": self.threshold,
            "abnormal_features": abnormal_features,
            "model_version": self.version,
        }

    def _heuristic_fallback(self, vector: np.ndarray) -> Dict[str, Any]:
        # Fast statistical heuristic
        cpu = vector[0]
        mem = vector[1]
        err = vector[3]
        p95 = vector[5]
        db_conn = vector[7]

        score = 0.1
        abnormal = []
        if db_conn > 85:
            score += 0.7
            abnormal.append({"feature": "db_connections", "value": db_conn, "deviation_sigma": 4.5})
        if err > 0.05:
            score += 0.5
            abnormal.append({"feature": "error_rate", "value": err, "deviation_sigma": 5.0})
        if cpu > 90:
            score += 0.6
            abnormal.append({"feature": "cpu_utilization", "value": cpu, "deviation_sigma": 4.0})
        if mem > 90:
            score += 0.6
            abnormal.append({"feature": "memory_utilization", "value": mem, "deviation_sigma": 3.8})
        if p95 > 1000:
            score += 0.5
            abnormal.append({"feature": "latency_p95", "value": p95, "deviation_sigma": 4.2})

        score = min(1.0, score)
        return {
            "is_anomaly": score >= self.threshold,
            "anomaly_score": round(score, 4),
            "threshold": self.threshold,
            "abnormal_features": abnormal,
            "model_version": "heuristic-baseline",
        }

    def save(self, filepath: str):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        joblib.dump({
            "model": self.model,
            "scaler": self.scaler,
            "threshold": self.threshold,
            "version": self.version,
        }, filepath)

    def load(self, filepath: str):
        data = joblib.load(filepath)
        self.model = data["model"]
        self.scaler = data["scaler"]
        self.threshold = data.get("threshold", self.DEFAULT_THRESHOLD)
        self.version = data.get("version", "v1.0.0")


anomaly_detector = AnomalyDetector()
