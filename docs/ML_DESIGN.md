# Wingman AI — Machine Learning Engine Design

The ML subsystem performs deterministic, statistically rigorous incident detection and classification. It operates under the mandate:
> **"Machine learning detects WHAT is going wrong."**

```
Telemetry Window (15s - 60s) 
  --> Feature Extractor (13 features + rolling stats) 
    --> Isolation Forest (Unsupervised Anomaly Score)
    --> LightGBM (Supervised 7-class Fault Classifier)
    --> CUSUM Change-point Detector (Abrupt shift flag)
```

---

## 1. Feature Engineering Specification

For each service $s$ at sliding window $t$ (e.g., 30-second window, sampled every 5 seconds), the pipeline generates a standardized feature vector:

| Feature Name | Metric Definition | Mathematical / Statistical Transform |
|--------------|-------------------|---------------------------------------|
| `cpu_utilization` | CPU percentage (0–100%) | Instantaneous mean over window |
| `memory_utilization` | Memory percentage (0–100%) | Instantaneous mean over window |
| `request_rate` | Requests per second (RPS) | Window mean |
| `error_rate` | Ratio of 5xx errors to total requests | $N_{5xx} / (N_{total} + \epsilon)$ |
| `latency_p50` | Median response time (ms) | 50th percentile of response durations |
| `latency_p95` | 95th percentile response time (ms) | 95th percentile |
| `latency_p99` | 99th percentile response time (ms) | 99th percentile |
| `db_connection_utilization` | Active DB connections / Pool size | Ratio [0.0, 1.0] |
| `timeout_rate` | Client/gateway timeout occurrences | $N_{timeouts} / (N_{total} + \epsilon)$ |
| `queue_depth` | Message / task backlog count | Instantaneous gauge mean |
| `cpu_rolling_mean_ratio` | Ratio of current CPU to 10-window rolling mean | $x_{cpu} / (\mu_{cpu, 10} + \epsilon)$ |
| `error_rate_delta` | First-order rate of change in error rate | $(err_t - err_{t-1}) / \Delta t$ |
| `latency_baseline_zscore` | Normalized deviation from 24h service baseline | $(p95_t - \mu_{baseline}) / (\sigma_{baseline} + \epsilon)$ |

---

## 2. Model 1: Unsupervised Anomaly Detection (Isolation Forest)
- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Training Set**: Telemetry vectors collected during normal traffic conditions (free of fault injection).
- **Hyperparameters**:
  - `n_estimators`: 150
  - `max_samples`: "auto"
  - `contamination`: 0.03 (calibrated to restrict false alert rate to < 1 per 24 hours under normal variance)
  - `random_state`: 42
- **Scoring**:
  Raw anomaly score $s \in [-1, 1]$. We normalize this to a strictly defined Anomaly Index $\in [0, 1]$ where higher means more anomalous:
  $$\text{Anomaly Score} = \frac{1 - \text{decision\_function}(X)}{2}$$
  A sample is flagged as anomalous when the Anomaly Score exceeds the tuned threshold $\theta_{anomaly} \approx 0.65$.
- **Explainability**: Features with highest deviation from the normal training distribution are extracted as `abnormal_features`.

---

## 3. Model 2: Supervised Fault Classification (LightGBM)
- **Algorithm**: `lightgbm.LGBMClassifier`
- **Classes**:
  0. `NORMAL`
  1. `DB_POOL_EXHAUSTION`
  2. `CPU_SATURATION`
  3. `MEMORY_PRESSURE`
  4. `DOWNSTREAM_API_FAILURE`
  5. `QUEUE_BACKLOG`
  6. `DEPLOYMENT_REGRESSION`
- **Dataset Strategy**:
  - Training datasets are generated through randomized, controlled fault-injection runs with diverse intensities (0.3 to 1.0) and durations.
  - **Group-aware splitting**: Train/validation splits are grouped by entire experiment runs rather than individual consecutive rows, preventing temporal leakage.
- **Evaluation & Baseline Comparison**:
  - LightGBM is compared directly against a baseline `RandomForestClassifier` and static heuristic rules.
  - Metrics tracked: Macro-Precision, Macro-Recall, Macro-F1, Multi-class Log Loss, Confusion Matrix.
  - Calibrated class probabilities generated via softmax output.

---

## 4. Model 3: Change-Point Detection (CUSUM)
- Cumulative Sum control chart implemented in Python/NumPy for critical latency and error-rate time-series.
- Used to pinpoint the exact second a degradation began, providing an accurate `start_timestamp` for the incident timeline.

---

## 5. Model Management & MLflow
- Artifacts: Trained model files (`isolation_forest.joblib`, `lightgbm_model.joblib`), scaler (`scaler.joblib`), and feature metadata (`feature_names.json`).
- Experiment tracking in `./mlruns`: parameters, datasets, metrics, and confusion matrix artifacts logged for every training iteration.
