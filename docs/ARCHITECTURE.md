# Wingman AI — System Architecture

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
| [API Gateway] -> [User Service]    |       | Strict JSON Schema Tools:          |       | 1. Feature Engineering             |
| [API Gateway] -> [Product Service] | <---> | - get_service_metrics              | <---> | 2. Isolation Forest (Anomaly)      |
| [API Gateway] -> [Checkout Service]|       | - search_logs                      |       | 3. LightGBM (Fault Classification) |
|       |-----> [Payment Service]    |       | - get_trace                        |       | 4. CUSUM Change-point Detection    |
|       +-----> [Order Service]      |       | - get_service_map                  |       | 5. Baseline Comparator             |
|                  |                 |       | - get_recent_deployments           |       | 6. MLflow Experiment Tracker       |
|                  v                 |       | - get_runbook                      |       +------------------------------------+
|             [Database]             |       | - compare_service_baseline         |
|                                    |       | - get_incident_history             |
| Telemetry exporters:               |       +-----------------+------------------+
| - OpenTelemetry Spans & Traces     |                         ^
| - Prometheus Counter / Histograms  |                         | MCP Client / Tool Dispatch
| - Structured JSON Logs             |                         v
+------------------------------------+       +---------------------------------------------------------------------------------+
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

## Key Architectural Invariants
1. **Model Decoupling**: Machine learning detectors run independently of the LLM. If the LLM is down or unconfigured, ML detection, alert clustering, and metric analysis still operate deterministically.
2. **Zero Fabricated Evidence**: The LLM is never provided unmetered logs or allowed to speculate without evidence IDs. Hypotheses must explicitly cite verified evidence artifacts gathered by deterministic tools.
3. **Strict Sandboxing**: No arbitrary code execution or shell commands. All remediation actions are strictly bounded Python callbacks requiring manual user approval in the UI.
4. **Resilient Local Execution**: Designed to execute comfortably on Apple Silicon (16GB RAM) without requiring heavy container overhead, with full Docker Compose support for production parity.
