# Wingman AI — Autonomous Production Incident Investigator

> **Your AI-powered production incident investigator.**  
> *Machine learning detects WHAT is going wrong. The investigation agent determines WHY it is happening. Evaluation ensures the system is reliable.*

[![CI](https://github.com/dheerajalamuri/wingman-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/dheerajalamuri/wingman-ai)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React 18](https://img.shields.io/badge/React-18.2-blue.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-16--Node%20Workflow-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini-3.5%20Flash--Lite-blueviolet.svg)](https://ai.google.dev/)

---

## 1. Problem Statement & Motivation
In modern microservice architectures, an isolated infrastructure fault (e.g. database connection starvation or downstream provider timeout) quickly triggers cascading 5xx errors and latency degradation across dozens of upstream services. On-call engineers are inundated with alert storms, spending 45+ minutes manually stitching together disparate metrics, log traces, and runbooks to identify the primary root cause.

**Wingman AI** is an autonomous, ML-powered production incident investigation platform that monitors distributed telemetry in real time, deterministically isolates primary versus propagated failures using machine learning and dependency topology graphs, autonomously investigates using a 16-node LangGraph agent over the Model Context Protocol (MCP), cites verified evidence artifacts, and recommends safe, human-authorized remediations.

---

## 2. Architectural Blueprint

```
                                  +-------------------------------------------------------------+
                                  |                     ENTERPRISE FRONTEND                     |
                                  |        (React 18, Vite, TypeScript, Tailwind, React Flow)   |
                                  +------------------------------+------------------------------+
                                                                 | REST / SSE / WebSockets
                                                                 v
+-------------------------------------------------------------------------------------------------------------------------------+
|                                                      BACKEND PLATFORM (FastAPI)                                               |
|                                                                                                                               |
|  +-----------------------+     +-------------------------+     +------------------------+     +----------------------------+  |
|  |     API Routers       |     |  Incident Orchestrator  |     |   Fault Lab Controller |     |     Evaluation Runner      |  |
|  | (Incidents, Services, |     | (Lifecycle & Correlation|     |  (Injection & Traffic  |     |   (ML Benchmark & Agent    |  |
|  |  Metrics, Models, RAG)|     |         Engine)         |     |       Simulation)      |     |          Harness)          |  |
|  +-----------+-----------+     +------------+------------+     +-----------+------------+     +-------------+--------------+  |
|              |                              |                              |                                |                 |
|              +------------------------------+------------------------------+--------------------------------+                 |
|                                             |                                                                                 |
|                                             v                                                                                 |
|  +-------------------------------------------------------------------------------------------------------------------------+  |
|  |                                              PERSISTENCE & STORAGE (SQLAlchemy 2)                                       |  |
|  |  PostgreSQL / Async SQLite (Services, Incidents, Hypotheses, Evidence, ModelVersions, Evaluations, Remediations)       |  |
|  +-------------------------------------------------------------------------------------------------------------------------+  |
+-------------------------------------------------------------------------------------------------------------------------------+
           |                                             |                                          ^
           | Telemetry Stream / Ingestion                | Diagnostic Tool Calls                    | Model Inferences
           v                                             v                                          |
+------------------------------------+       +------------------------------------+       +------------------------------------+
|  SIMULATOR & OBSERVABILITY PIPELINE|       |       MODEL CONTEXT PROTOCOL       |       |       MACHINE LEARNING ENGINE      |
|                                    |       |            (MCP SERVER)            |       |                                    |
| [API Gateway] -> [User Service]    |       | Strict JSON Schema Tools:          |       | 1. Feature Engineering (13 dims)   |
| [API Gateway] -> [Product Service] | <---> | - get_service_metrics              | <---> | 2. Isolation Forest (Anomaly)      |
| [API Gateway] -> [Checkout Service]|       | - search_logs                      |       | 3. LightGBM (Fault Classifier)     |
|       |-----> [Payment Service]    |       | - get_trace                        |       | 4. CUSUM Change-point Detection    |
|       +-----> [Order Service]      |       | - get_service_map                  |       | 5. Baseline Comparator             |
|                  |                 |       | - get_recent_deployments           |       | 6. MLflow Experiment Tracker       |
|                  v                 |       | - get_runbook                      |       +------------------------------------+
|             [Database]             |       | - compare_service_baseline         |
|                                    |       | - get_incident_history             |
+------------------------------------+       +-----------------+------------------+
                                                               ^
                                                               | MCP Diagnostic Tool Dispatch
                                                               v
                                             +---------------------------------------------------------------------------------+
                                             |                     AGENTIC INVESTIGATION ENGINE (LangGraph)                    |
                                             |                                                                                 |
                                             |  [Intake] -> [ContextBuilder] -> [AffectedServiceID] -> [Planner]              |
                                             |      |                                                                          |
                                             |      +--> [MetricsInv] -> [LogInv] -> [TraceInv] -> [DeployInv]                 |
                                             |      |                                                                          |
                                             |      +--> [Runbook RAG] (Hybrid Qdrant + BM25)                                  |
                                             |      |                                                                          |
                                             |      v                                                                          |
                                             |  [Hypothesis Generation] (Google Gemini 3.5 Flash-Lite: Pydantic Validation)    |
                                             |      |                                                                          |
                                             |      v                                                                          |
                                             |  [Evidence Validation] -> [Hypothesis Ranking] -> [Remediation Proposal]       |
                                             |      |                                                                          |
                                             |      v                                                                          |
                                             |  [Safety Validation] -> [HUMAN APPROVAL GATE] -> [Execution & Verification]    |
                                             +---------------------------------------------------------------------------------+
```

---

## 3. Machine Learning Engine & Mathematics

### Feature Engineering (13-Dimensional Standardized Vector)
Every sliding telemetry window (sampled every 5 seconds) is mapped to:
1. `cpu_utilization`: Instantaneous CPU percentage (0–100%)
2. `memory_utilization`: Instantaneous Memory percentage (0–100%)
3. `request_rate`: Requests Per Second (RPS)
4. `error_rate`: $N_{5xx} / (N_{total} + \epsilon)$
5. `latency_p50`: 50th percentile response duration (ms)
6. `latency_p95`: 95th percentile response duration (ms)
7. `latency_p99`: 99th percentile response duration (ms)
8. `db_connections`: Active connection utilization (%)
9. `queue_depth`: Async pending item backlog
10. `timeout_rate`: Timeout ratio [0.0, 1.0]
11. `cpu_rolling_mean_ratio`: $x_{cpu} / (\mu_{cpu, 5} + \epsilon)$
12. `error_rate_delta`: First-order rate of change $(err_t - err_{t-1}) / \Delta t$
13. `latency_baseline_zscore`: Normalized deviation $(p95_t - \mu_{baseline}) / (\sigma_{baseline} + \epsilon)$

### Model 1: Unsupervised Anomaly Detection (Isolation Forest)
- **Algorithm**: `sklearn.ensemble.IsolationForest`
- **Training Baseline**: Trained strictly on normal operation windows.
- **Calibrated Scoring Formula**:
  $$\text{Anomaly Score} = \text{clip}\left(\frac{1 - \text{decision\_function}(X)}{2}, 0.0, 1.0\right)$$
- **Tuned Threshold**: $\theta = 0.5200$.

### Model 2: Supervised Multi-Class Classifier (LightGBM)
- **Algorithm**: `lightgbm.LGBMClassifier`
- **Classes**:
  - `0`: NORMAL
  - `1`: DB_POOL_EXHAUSTION
  - `2`: CPU_SATURATION
  - `3`: MEMORY_PRESSURE
  - `4`: DOWNSTREAM_API_FAILURE
  - `5`: QUEUE_BACKLOG
  - `6`: DEPLOYMENT_REGRESSION
- **Split Strategy**: `GroupShuffleSplit` by entire experiment run to avoid temporal data leakage.
- **Evaluation Baseline Comparison**: Directly benchmarked against `RandomForestClassifier`.

### Actual Benchmark Results on Held-Out Test Set (1,400 samples)
```
----------------------------------------------------------------------
 DETECTION PERFORMANCE (Binary: Normal vs Incident)
----------------------------------------------------------------------
Method                         | Precision  | Recall     | F1-Score  
----------------------------------------------------------------------
Static Heuristic Thresholds    | 1.0000     | 1.0000     | 1.0000    
Isolation Forest (Ours)        | 0.9983     | 0.9725     | 0.9852    

----------------------------------------------------------------------
 CLASSIFICATION PERFORMANCE (7-Class LightGBM Classifier)
----------------------------------------------------------------------
Overall Macro Precision: 0.9993
Overall Macro Recall:    0.9993
Overall Macro F1-Score:  0.9993

Per-Class Breakdown:
                        precision    recall  f1-score   support
                NORMAL       1.00      1.00      1.00       200
    DB_POOL_EXHAUSTION       1.00      1.00      1.00       200
        CPU_SATURATION       1.00      1.00      1.00       200
       MEMORY_PRESSURE       1.00      1.00      1.00       200
DOWNSTREAM_API_FAILURE       1.00      1.00      1.00       200
         QUEUE_BACKLOG       1.00      0.99      1.00       200
 DEPLOYMENT_REGRESSION       1.00      1.00      1.00       200
```

---

## 4. Agentic AI & Model Context Protocol (MCP)

### Centralized Gemini Provider
- **Provider**: Google Gemini API via official `google-genai` Python SDK.
- **Exact Model**: `gemini-3.5-flash-lite`.
- **Structured Validation**: Every LLM response is parsed and validated against strict Pydantic schemas (`HypothesisListResponse`). Circuit-breaker fallback ensures zero crashes or fabricated hallucinations during network partitions.

### Official MCP Server (`agent/mcp_server/server.py`)
Exposes 8 strictly bounded, read-only diagnostic tools over Model Context Protocol:
1. `get_service_metrics(service_id, limit)`
2. `search_logs(service_id, level, query, limit)`
3. `get_trace(trace_id)`
4. `get_service_map()`
5. `get_recent_deployments(service_id, lookback_minutes)`
6. `compare_service_baseline(service_id)`
7. `get_incident_history(service_id, limit)`

### 16-Node LangGraph State Machine
1. `node_intake`
2. `node_context_builder`
3. `node_affected_service_id`
4. `node_investigation_planner`
5. `node_metrics_investigation` (MCP Tool)
6. `node_log_investigation` (MCP Tool)
7. `node_trace_investigation` (MCP Tool)
8. `node_deployment_investigation` (MCP Tool)
9. `node_runbook_retrieval` (Hybrid BM25 + Vector RAG)
10. `node_hypothesis_generation` (Gemini 3.5 Flash-Lite)
11. `node_evidence_validation` (Grounding Check)
12. `node_hypothesis_ranking`
13. `node_remediation_recommendation`
14. `node_safety_validation` (Whitelist Enforcement)
15. `node_human_approval` (Human-in-the-Loop Gate)
16. `node_recovery_verification` (Telemetry Health Check)

---

## 5. Quickstart & Local Setup

### Prerequisites
- macOS (Apple Silicon M-series verified) or Linux
- Python 3.11+
- Node.js 20+ & npm

### 1. Clone & Environment Configuration
```bash
git clone https://github.com/dheerajalamuri/wingman-ai.git
cd wingman-ai

cp .env.example .env
# Edit .env to add your GEMINI_API_KEY if testing live external LLM calls
```

### 2. Python Virtual Environment & Dependencies
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install greenlet
```

### 3. Train ML Models
```bash
python -m ml.training.train_anomaly
python -m ml.training.train_classifier
python -m ml.evaluation.evaluate_models
```

### 4. Run Automated Test Suite
```bash
# Run all unit and integration tests (12 tests)
PYTHONPATH=. pytest backend/tests ml/tests agent/tests -v

# Run the complete end-to-end acceptance integration scenario
PYTHONPATH=. python -m tests.test_end_to_end_scenario
```

### 5. Launch Backend & Frontend Servers
In Terminal 1 (Backend API & Telemetry Simulator):
```bash
source .venv/bin/activate
PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
```

In Terminal 2 (React Enterprise Dashboard):
```bash
cd frontend
npm install
npm run dev
```

Open your browser at `http://localhost:5173`.

---

## 6. Full Docker Compose Deployment

```bash
docker compose up --build
```
- Frontend: `http://localhost:3000`
- Backend API: `http://localhost:8000`
- Interactive OpenAPI Docs: `http://localhost:8000/docs`

---

## 7. Interactive Demonstration Script (Fault Lab Walkthrough)

1. Open `http://localhost:5173`. Notice all 6 microservices reporting **Healthy** with normal baseline latency (~35ms).
2. Navigate to **Fault Lab** (`/fault-lab`).
3. Select **DB Connection Pool Exhaustion** on `order-service` with intensity `0.85` and click **"Inject Fault into Telemetry Pipeline"**.
4. Return to **Overview** (`/`). Observe `order-service` and dependent `checkout-service` degrade:
   - Database connection utilization jumps to 99%.
   - Latency P95 spikes from 70ms to > 2500ms.
   - 5xx error rate spikes.
5. In **Incidents** (`/incidents`), click **"Scan Anomaly Pipeline"** or wait for the automatic scan.
6. Open the newly detected incident deep-dive.
7. Click **"Run Investigation Workflow"**.
   - Watch the 16-node LangGraph workflow execute.
   - Inspect the collected evidence artifacts (metric spikes, error logs, runbook match `[RB-DB-001]`).
   - Review the ranked hypothesis: **"PostgreSQL database connection pool exhaustion on order-service" (Confidence: 96%)**.
8. Inspect the proposed remediation: `RESET_CONNECTION_POOL` on `order-service`.
9. Enter operator notes and click **"Approve & Execute Remediation"**.
10. Telemetry recovery verifies healthy normalization. The incident transitions to **RESOLVED**.

---

## 8. Technical Invariants & Interview Talking Points
- **Machine Learning vs Agent Decoupling**: We do not ask the LLM to do numerical anomaly detection on millions of metric points. Isolation Forest and LightGBM handle mathematical detection; Gemini handles semantic reasoning and runbook grounding.
- **Zero Hallucinated Evidence**: Every generated hypothesis must reference a verified evidence ID from the MCP diagnostic phase.
- **Group-Aware Splitting**: Splitting time-series telemetry randomly leaks adjacent time samples. We split datasets strictly by entire experiment runs.
- **Bounded Remediation Safety**: Zero arbitrary shell or script execution. All remediations are whitelisted, deterministic backend functions requiring human operator authorization.
