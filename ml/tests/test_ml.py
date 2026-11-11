import numpy as np
import pytest

from ml.features.extractor import feature_extractor, FEATURE_NAMES
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier, CLASS_MAPPING
from ml.anomaly_detection.cusum import cusum_detector


def test_feature_extractor():
    sample_pt = {
        "service_id": "checkout-service",
        "cpu_utilization": 85.0,
        "memory_utilization": 40.0,
        "request_rate": 20.0,
        "error_rate": 0.05,
        "latency_p50": 30.0,
        "latency_p95": 120.0,
        "latency_p99": 250.0,
        "db_connections": 15.0,
        "queue_depth": 10.0,
        "timeout_rate": 0.01,
    }
    vec = feature_extractor.extract_vector(sample_pt)
    assert isinstance(vec, np.ndarray)
    assert len(vec) == len(FEATURE_NAMES)
    assert len(vec) == 13


def test_anomaly_detection_prediction():
    # Normal point vector
    normal_vec = np.array([20.0, 30.0, 15.0, 0.001, 20.0, 45.0, 70.0, 15.0, 5.0, 0.0, 1.0, 0.0, 0.2])
    res_normal = anomaly_detector.predict_anomaly(normal_vec)
    assert "anomaly_score" in res_normal
    assert "is_anomaly" in res_normal
    assert isinstance(res_normal["abnormal_features"], list)

    # Extreme anomalous point vector
    anom_vec = np.array([98.0, 95.0, 15.0, 0.85, 2500.0, 3800.0, 4500.0, 99.0, 100.0, 0.6, 3.5, 0.5, 8.5])
    res_anom = anomaly_detector.predict_anomaly(anom_vec)
    assert res_anom["is_anomaly"] is True
    assert res_anom["anomaly_score"] > 0.5


def test_incident_classification_prediction():
    # DB pool exhaustion vector
    db_vec = np.array([25.0, 35.0, 15.0, 0.70, 1500.0, 2800.0, 3500.0, 99.0, 10.0, 0.4, 1.0, 0.3, 6.0])
    res = incident_classifier.predict(db_vec)
    assert res["predicted_class"] == "DB_POOL_EXHAUSTION"
    assert res["confidence"] > 0.8
    assert len(res["class_probabilities"]) == len(CLASS_MAPPING)


def test_cusum_change_point():
    stable = [25.0, 26.0, 24.5, 25.5, 25.0, 26.0, 25.2]
    assert cusum_detector.detect_change_point(stable) is None

    # Step increase after index 4
    jump = [25.0, 25.5, 25.2, 24.8, 25.0, 180.0, 250.0, 300.0]
    idx = cusum_detector.detect_change_point(jump)
    assert idx is not None
    assert idx >= 4
