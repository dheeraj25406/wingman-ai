# Wingman AI — Project Plan & Execution Strategy

## 1. Executive Summary & Philosophy
Wingman AI is an autonomous, ML-powered production incident investigation platform for distributed microservices. 
The core philosophy is:
> **"Machine learning detects WHAT is going wrong. The investigation agent determines WHY it is happening. Evaluation ensures the system is reliable."**

The platform is purpose-built for enterprise SRE, DevOps, and Platform Engineering teams to cut Mean Time to Resolution (MTTR) while preventing LLM hallucinations through strict deterministic telemetry correlation, Model Context Protocol (MCP) tool gates, and human-in-the-loop remediation safety checks.

---

## 2. Hardware & Environment Constraints
- **Host System**: Apple Silicon Mac (M4, 16 GB RAM).
- **Execution Model**: CPU-optimized ML inference (Isolation Forest, LightGBM, MiniLM-L6-v2 embeddings).
- **External Dependencies**: Exactly ONE external LLM provider: Google Gemini (`gemini-3.5-flash-lite`) via `google-genai` SDK.
- **Fallbacks**: BM25 lexical search fallback if neural embeddings are unavailable; local SQLite database fallback with PostgreSQL production capability; in-process telemetry buffers with OpenTelemetry/Prometheus/Loki/Tempo export.

---

## 3. Work Breakdown Structure (WBS) & Milestones

### Phase 0: System Architecture & Specification (Current)
- [x] Workspace inspection and environment verification (Python 3.11, Node.js v25).
- [x] Secret management (`.gitignore`, `.env.example`, `.env`).
- [ ] Comprehensive engineering design specifications (`PROJECT_PLAN.md`, `ARCHITECTURE.md`, `DATABASE_DESIGN.md`, `API_DESIGN.md`, `ML_DESIGN.md`, `AGENT_DESIGN.md`, `FRONTEND_DESIGN.md`, `TEST_STRATEGY.md`, `PROGRESS.md`).

### Phase 1: Core Foundation & Monorepo Scaffold
- Scaffold clean directory structure:
  - `backend/`: FastAPI application, modular routers, core dependencies, SQLAlchemy 2 models, Pydantic v2 schemas.
  - `ml/`: Anomaly detection, classification, feature engineering, training pipelines, MLflow integration.
  - `agent/`: LangGraph state machine, MCP server, runbook RAG, prompt management, evaluation harness.
  - `simulator/`: Distributed e-commerce services, traffic generator, fault injector.
  - `observability/`: OpenTelemetry, Prometheus, Loki, Tempo configs.
  - `frontend/`: Vite + React + TypeScript + Tailwind CSS + TanStack Query + React Flow + Lucide.
- Virtual environment setup with pinned dependencies.
- Healthcheck and baseline tests.

### Phase 2: Distributed Application Simulator & Telemetry Pipeline
- Implement 6 communicating microservices (API Gateway, User, Product, Checkout, Payment, Order) + Database mock.
- Real HTTP calls with trace context propagation (`traceparent`), request IDs, and structured logging.
- Telemetry generation: CPU, memory, request count, error rates, p50/p95/p99 latency, DB connection utilization, queue depth.
- Controlled Fault Injection Engine:
  1. Database connection pool exhaustion.
  2. CPU saturation.
  3. Memory pressure.
  4. Downstream API latency.
  5. Downstream API failures (HTTP 500/503).
  6. Queue backlog.
  7. Bad deployment / configuration regression.

### Phase 3: Machine Learning Engine
- Unified feature engineering pipeline (rolling statistics, baseline deviations, rates of change).
- **Model 1 (Isolation Forest)**: Unsupervised window-based anomaly scoring per service with threshold calibration.
- **Model 2 (LightGBM Classifier)**: Supervised 7-class incident classification trained on controlled fault injections.
- **Baseline Comparison**: Random Forest baseline & threshold-based alerting comparison.
- **MLflow Tracking**: Model versioning, hyperparameter logging, confusion matrices, PR-AUC curves.
- Reproducible training scripts:
  - `python -m ml.training.train_anomaly`
  - `python -m ml.training.train_classifier`
  - `python -m ml.evaluation.evaluate_models`

### Phase 4: Deterministic Incident Correlation & Lifecycle
- Dependency graph traversal to identify root versus propagated failure.
- Temporal clustering & windowing to group alerts into a single actionable incident.
- Evidence store persisting metrics, logs, traces, and anomaly signals with foreign-key referential integrity.

### Phase 5: Agentic Investigation Engine (LangGraph + MCP + Gemini)
- 16-node stateful LangGraph workflow with typed Pydantic state and bounded loops:
  1. Incident Intake -> 2. Context Builder -> 3. Affected Service ID -> 4. Planner ->
  5. Metrics Inv -> 6. Log Inv -> 7. Trace Inv -> 8. Deployment Inv -> 9. Runbook RAG ->
  10. Hypothesis Gen (Gemini) -> 11. Evidence Validation -> 12. Ranking ->
  13. Remediation Proposal -> 14. Safety Validation -> 15. Human Approval -> 16. Recovery Verification.
- Standalone MCP Server exposing read-only diagnostic tools.
- Runbook RAG with chunking, hybrid Qdrant/BM25 retrieval, and citation verification.
- Human-in-the-loop remediation execution with predefined safe action callbacks.

### Phase 6: Comprehensive Evaluation Engine
- ML evaluation: Precision, Recall, Macro-F1, PR-AUC, Detection Delay, False Alert Rate.
- Agent evaluation: 100+ benchmark test cases measuring Top-1/Top-3 root-cause accuracy, evidence precision, tool selection accuracy, remediation safety, token consumption, and cost.
- Continuous evaluation pipeline with regression alerts.

### Phase 7: Enterprise Frontend (Linear / Datadog Aesthetic)
- Dark-mode technical design system (#0D1117, #111720, #151D27, #1A2430, #293442).
- 8 fully functional pages:
  1. Overview: System health, telemetry charts, incident activity.
  2. Incidents: Filterable, sortable incident table.
  3. Incident Investigation: Deep-dive view with timeline, telemetry overlays, evidence inspector, ranked hypotheses, and remediation approval modal.
  4. Service Map: Interactive React Flow topology with live health indicators.
  5. Model Intelligence: MLflow metrics, confusion matrix, feature importance, ROC/PR curves.
  6. AI Evaluation: Benchmark runs, accuracy breakdowns, latency/cost metrics, failed case inspection.
  7. Fault Lab: Real-time traffic controls and fault injection triggers.
  8. Settings: API status, integration health, safety toggles.

### Phase 8: Verification & Delivery
- Automated end-to-end integration test: Normal traffic -> Fault injection -> Anomaly detection -> Incident creation -> LangGraph investigation -> Hypothesis ranking -> Human approval -> Recovery verification.
- Comprehensive technical documentation, README, and reproducible demo scenario.
