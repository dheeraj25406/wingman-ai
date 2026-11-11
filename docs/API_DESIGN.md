# Wingman AI — REST API & SSE Specification

All endpoints are hosted by FastAPI at prefix `/api`. 
Consistent response wrapper:
```json
{
  "status": "success",
  "data": { ... },
  "message": null,
  "timestamp": "2026-11-11T09:22:00Z"
}
```
Errors adhere to RFC 7807 (Problem Details).

---

## 1. System & Services
- `GET /api/health`
  - Health check: checks database connectivity, ML models status, Gemini API configuration, and simulator status.
- `GET /api/services`
  - Returns list of monitored services, statuses (`healthy`, `degraded`, `critical`), and dependencies.
- `GET /api/services/{service_id}`
  - Returns service metadata, dependencies, active faults, and current telemetry summary.

## 2. Telemetry & Metrics
- `GET /api/metrics/overview`
  - Aggregate metrics across the entire application: global error rate, avg p95 latency, total throughput, active anomaly count.
- `GET /api/metrics/services/{service_id}?window=15m`
  - Time-series buckets for CPU, memory, error rate, p50/p95/p99 latency, DB connection utilization, queue depth.

## 3. Incident Management & Correlation
- `GET /api/incidents`
  - Query parameters: `status`, `severity`, `service_id`, `limit`, `offset`.
  - Returns paginated incident list with affected service summaries.
- `GET /api/incidents/{incident_id}`
  - Full incident details, root cause summary, and status.
- `POST /api/incidents/detect`
  - Triggers an anomaly scan across recent telemetry windows. If an anomaly is found, runs deterministic correlation and creates an incident.
- `GET /api/incidents/{incident_id}/timeline`
  - Chronological incident events (detection -> investigation steps -> approvals -> recovery).
- `GET /api/incidents/{incident_id}/evidence`
  - Concrete evidence collected for this incident (metric spikes, log traces, trace breakdowns).
- `GET /api/incidents/{incident_id}/hypotheses`
  - Ranked root-cause hypotheses with confidence scores and evidence citations.

## 4. Agentic Investigation Workflow
- `POST /api/incidents/{incident_id}/investigate`
  - Initiates the 16-node LangGraph investigation pipeline.
- `GET /api/incidents/{incident_id}/investigation/status`
  - Current LangGraph node, progress percentage, token usage, tool call logs.
- `POST /api/incidents/{incident_id}/remediation`
  - Synthesizes or retrieves proposed remediation.
- `POST /api/incidents/{incident_id}/approve`
  - Body: `{ "proposal_id": "...", "operator_notes": "..." }`
  - Executes the predefined safe remediation action and triggers recovery verification.
- `POST /api/incidents/{incident_id}/reject`
  - Body: `{ "proposal_id": "...", "operator_notes": "..." }`
  - Rejects proposed remediation and marks incident as requiring manual intervention.

## 5. Fault Injection & Traffic Simulator
- `POST /api/faults/inject`
  - Body: `{ "fault_type": "db_pool_exhaustion", "target_service": "order-service", "intensity": 0.9, "duration_seconds": 300 }`
- `POST /api/faults/{fault_id}/stop`
  - Immediately halts the active fault simulation.
- `GET /api/faults`
  - Returns list of active and recent fault injections with ground-truth labels.
- `POST /api/simulator/traffic`
  - Body: `{ "rps": 50, "pattern": "normal" | "spike" | "error_burst" }`
- `GET /api/simulator/status`
  - Current traffic generator status and active faults.

## 6. Machine Learning Intelligence
- `GET /api/models`
  - Overview of loaded models: Isolation Forest (version, threshold), LightGBM (version, classes, accuracy).
- `GET /api/models/metrics`
  - Precision, Recall, Macro-F1, PR-AUC, Confusion Matrix, Feature Importance.
- `POST /api/models/train`
  - Retrains models on synthetic or recorded fault injection datasets.

## 7. AI & Agent Evaluation
- `GET /api/evaluations`
  - History of evaluation runs with Top-1/Top-3 root-cause accuracies, evidence precision, and latency.
- `POST /api/evaluations/run`
  - Body: `{ "benchmark_name": "full_suite", "cases_count": 25 }`
  - Executes deterministic + Gemini-evaluated benchmark suite against ground-truth incidents.

## 8. Settings & Integrations
- `GET /api/settings/integrations`
  - Integration connectivity status (Gemini API, Prometheus, Loki, Tempo, Vector DB). Never returns API keys.
