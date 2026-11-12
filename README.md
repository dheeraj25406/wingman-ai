# Wingman AI — Autonomous Production Reliability Engineer

> **Your AI-powered production incident investigator.**  
> *Machine learning detects WHAT is going wrong. The investigation agent determines WHY it is happening. Closed-loop remediation and evaluation ensure the system recovers reliably.*

[![CI](https://github.com/dheerajalamuri/wingman-ai/actions/workflows/ci.yml/badge.svg)](https://github.com/dheerajalamuri/wingman-ai)
[![Python 3.11](https://img.shields.io/badge/Python-3.11-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React-19.0-blue.svg)](https://react.dev/)
[![LangGraph](https://img.shields.io/badge/LangGraph-16--Node%20Workflow-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Gemini-3.5%20Flash--Lite-blueviolet.svg)](https://ai.google.dev/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 1. Problem Statement & Overview

In distributed microservice architectures, an isolated infrastructure failure (e.g. database connection starvation or downstream provider latency) quickly causes cascading 5xx errors and timeout storms across upstream dependencies. On-call engineers often spend 30–60 minutes manually stitching together disparate metrics, log traces, and runbooks to identify the primary failure point.

**Wingman AI** is an autonomous production reliability platform that:
1. **Detects Anomalies Deterministically**: Uses an unsupervised Isolation Forest and multi-class LightGBM classifier over a 16-dimensional telemetry feature vector.
2. **Autonomously Investigates Root Cause**: Executes a 16-node state-machine agent using **LangGraph** and **Google Gemini 3.5 Flash-Lite**, fetching multi-modal diagnostic evidence (metrics, logs, traces, runbooks, deployments) via the **Model Context Protocol (MCP)**.
3. **Recommends & Verifies Remediation**: Proposes targeted, whitelisted remediation actions (e.g. connection pool reset, rollback, service restart), enforces **Human-in-the-Loop approval**, and verifies closed-loop recovery against live telemetry.

> [!NOTE]
> **Simulation Architecture Notice**: The 6 monitored microservices (`api-gateway`, `user-service`, `product-service`, `checkout-service`, `payment-service`, `order-service`) operate through an in-process discrete-event microservice simulator (`simulator/services/mesh.py`). The simulator models realistic inter-service HTTP dependency graphs, database connection pools, queue backlogs, memory pressure, and CPU saturation. This enables reproducible fault injection, benchmarking, and closed-loop recovery verification in testing environments without requiring a multi-node Kubernetes cluster.
>
> In contrast, the application stack itself runs **3 independently containerized production services** via Docker Compose: `wingman-postgres` (PostgreSQL 16), `wingman-backend` (FastAPI + LangGraph + Uvicorn), and `wingman-frontend` (React 19 + Nginx reverse proxy).

---

## 2. System Architecture

```mermaid
flowchart TD
    subgraph Client["Presentation Layer (Desktop & Mobile)"]
        UI["React 19 + Vite Dashboard<br/>(Tailwind, Lucide, Recharts)"]
    end

    subgraph Ingress["Ingress & Defensive Security"]
        NGX["Nginx 1.31 Reverse Proxy<br/>(:80 / :443)"]
        SEC["FastAPI Security Middleware<br/>(Rate Limiting, X-Real-IP, CSP)"]
    end

    subgraph Core["Backend Platform (FastAPI / Python 3.11)"]
        ROUTERS["API Routers<br/>(Incidents, Faults, Metrics, Health)"]
        SIM["Microservice Mesh Simulator<br/>(6 Monitored Services)"]
        ORCH["Incident Correlation Engine"]
        REPO["Incident Repository & Alembic"]
    end

    subgraph ML["Machine Learning Pipeline"]
        FEAT["16-Dim Feature Extractor"]
        IF["Isolation Forest (Anomaly Detection)<br/>97.56% Recall, 0% FPR"]
        LGBM["LightGBM (Fault Classifier)<br/>1.0000 Macro-F1 (Synthetic)"]
    end

    subgraph Agent["Agentic Investigation Engine (LangGraph)"]
        LG16["16-Node State Machine Agent"]
        MCP["Model Context Protocol (MCP) Server<br/>(8 Diagnostic Tools)"]
        GEMINI["Google Gemini 3.5 Flash-Lite<br/>(Structured Pydantic Validation)"]
        GATE{"Human-in-the-Loop<br/>Approval Gate"}
        EXEC["Remediation & Recovery Verification"]
    end

    subgraph Storage["Persistence Layer"]
        PG[("PostgreSQL 16 Alpine<br/>(15 Migration Tables)")]
    end

    UI -->|REST / SSE| NGX
    NGX -->|Internal Proxy| SEC
    SEC --> ROUTERS
    SIM -->|Telemetry Window (5s)| FEAT
    FEAT --> IF & LGBM
    IF & LGBM --> ORCH
    ORCH --> ROUTERS
    ROUTERS -->|Persist State| REPO
    REPO --> PG
    ROUTERS -->|Trigger Investigation| LG16
    LG16 -->|Parallel Prefetch| MCP
    LG16 -->|Reasoning Prompt| GEMINI
    LG16 --> GATE
    GATE -->|Authorized Operator| EXEC
    EXEC -->|Verify Health| SIM
```

---

## 3. Technology Stack

| Layer | Technologies |
| :--- | :--- |
| **Frontend** | React 19, TypeScript, Vite, Tailwind CSS, Recharts, Lucide Icons |
| **Backend API** | FastAPI, Uvicorn, Python 3.11, Pydantic v2, Starlette |
| **Database & ORM** | PostgreSQL 16 Alpine, SQLAlchemy 2 (asyncpg), Alembic (15 migration tables) |
| **Machine Learning** | Scikit-learn (Isolation Forest), LightGBM, NumPy, Pandas, Joblib |
| **AI & Agent Workflow** | LangGraph, Google GenAI SDK (`gemini-3.5-flash-lite`), MCP Server |
| **Container & CI** | Docker Compose v2, Nginx 1.31 Alpine, GitHub Actions CI |

---

## 4. Key Performance Benchmarks (Audited)

All metrics below represent **empirically measured values** captured during standardized benchmark executions across controlled fault scenarios. See [`docs/BENCHMARK_REPORT.md`](docs/BENCHMARK_REPORT.md) for full methodology, raw JSON outputs, and statistical limitations.

| Pillar | Measured Metric | Baseline | Optimized | Verification Summary |
| :--- | :--- | :---: | :---: | :--- |
| **ML Anomaly Detection** | **Recall** on held-out test split | 90.89% | **97.56%** | **+6.67% improvement** via 16-feature calibration |
| **ML Anomaly Detection** | **False Positive Rate** | 0.00% | **0.00%** | Zero false alarms on normal baseline split |
| **ML Inference Latency** | **p50 Latency** per feature vector | 3.06 ms | **3.07 ms** | Real-time scoring suitable for 5s telemetry windows |
| **AI Investigation** | **Root-Cause Accuracy** | 83.33% | **83.33%** | Evaluated across 30 repeated fault trials |
| **AI Evidence Grounding** | **Evidence Items Gathered** | 0.0 | **5.0 items** | Metrics, logs, traces, topology, runbooks |
| **Remediation MTTR** | **Decision & Action MTTR** | 9.46 s | **4.92 s** | **-47.9% reduction** via parallel diagnostic prefetch |
| **Remediation Safety** | **Verified Recovery Rate** | 100.0% | **100.0%** | Zero false recoveries across 30 live fault injections |
| **Backend Throughput** | **Peak Throughput (5 clients)** | 1,059 RPS | **1,677 RPS** | **+58.4% improvement** via in-memory micro-caching |
| **Backend Latency** | **p50 Latency (5 clients)** | 2.68 ms | **2.50 ms** | Sustained sub-3ms latency across 15,000 requests |
| **Resource Efficiency** | **Full Docker Stack RAM** | — | **290.6 MiB** | Backend (237M), Frontend (9M), Postgres (44M) |

---

## 5. Quickstart & Local Installation

### Prerequisites
- macOS (Apple Silicon verified) or Linux x86_64
- Python 3.11+
- Node.js 20+ & npm 10+
- Docker Desktop or Docker Engine v24+

### Option A: Local Development Setup

1. **Clone the Repository**:
   ```bash
   git clone https://github.com/dheerajalamuri/wingman-ai.git
   cd wingman-ai
   ```

2. **Configure Environment Variables**:
   ```bash
   cp .env.example .env
   # Add your Google Gemini API key if testing external live reasoning:
   # GEMINI_API_KEY=your_key_here
   ```

3. **Backend Setup & Virtual Environment**:
   ```bash
   python3.11 -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```

4. **Initialize Database Migrations**:
   ```bash
   DATABASE_URL="sqlite+aiosqlite:///./wingman.db" alembic upgrade head
   ```

5. **Frontend Setup**:
   ```bash
   cd frontend
   npm ci
   cd ..
   ```

6. **Run Automated Test Suite (31 Tests)**:
   ```bash
   DATABASE_URL="sqlite+aiosqlite:///./test_isolated.db" PYTHONPATH=. pytest tests/ backend/tests/ ml/tests/ agent/tests/
   rm -f test_isolated.db
   ```

7. **Start Development Servers**:
   - Terminal 1 (Backend & Telemetry Simulator):
     ```bash
     source .venv/bin/activate
     PYTHONPATH=. uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --reload
     ```
   - Terminal 2 (React Vite Dashboard):
     ```bash
     cd frontend && npm run dev
     ```
   - Open browser at `http://localhost:5173`.

---

### Option B: Docker Compose Deployment

#### 1. Local Development Profile
Runs the full containerized stack with developer ports exposed (`5432` for database access, `8000` for backend API, `3000` for frontend):
```bash
cp .env.example .env
docker compose up -d --build
```
- Frontend Dashboard: `http://localhost:3000`
- Backend API Docs: `http://localhost:8000/docs`
- Health Liveness: `http://localhost:8000/api/health/live`
- Health Readiness: `http://localhost:8000/api/health/ready`

#### 2. Production Profile (`docker-compose.prod.yml`)
Enforces strict security boundaries: PostgreSQL is internal-only (no host port exposure), backend is private, public ingress is routed solely through Nginx on port 80/443, non-root user execution is enforced, and administrative authorization is mandatory:
```bash
ADMIN_API_KEY="your_secure_admin_key" \
POSTGRES_PASSWORD="your_secure_db_pass" \
docker compose -f docker-compose.prod.yml up -d --build
```

---

## 6. Interactive Incident Lifecycle Walkthrough

1. Open `http://localhost:3000` (or `http://localhost:5173`). Observe the **Overview** dashboard reporting 6 healthy microservices with ~35ms baseline latency.
2. Navigate to **Fault Lab** (`/fault-lab`).
3. Select **DB Connection Pool Exhaustion** on `order-service` with intensity `0.85`, duration `180s`, and click **"Inject Fault"**.
4. Return to **Overview** (`/`). Observe real-time telemetry degradation:
   - `order-service` database connections surge to 99%.
   - Latency p95 spikes from 70ms to > 2,500ms.
   - Upstream `checkout-service` and `api-gateway` begin cascading 5xx timeouts.
5. In **Incidents** (`/incidents`), click **"Scan Anomaly Pipeline"** (or wait for the 5-second autonomous scan).
6. Click into the newly generated incident (`/incidents/inc-...`).
7. Click **"Run Investigation Workflow"**:
   - Watch the 16-node LangGraph agent prefetch metrics, search error logs, trace distributed spans, and retrieve runbook `[RB-DB-001]`.
   - Review Gemini's structured hypothesis: *"PostgreSQL connection pool exhaustion on order-service (Confidence: 96%)"*.
8. Inspect the proposed remediation: `RESET_CONNECTION_POOL` on `order-service`.
9. Enter operator notes and click **"Approve & Execute Remediation"**.
10. The simulator resets the pool. The closed-loop verification node monitors recovery telemetry, confirms healthy operation, and marks the incident **RESOLVED**.

---

## 7. Security & Hardening Highlights

- **Zero Secret Exposure**: Gemini API keys and database credentials remain strictly server-side.
- **Fail-Closed Authorization**: Constant-time token checks protect all mutating endpoints (`/faults/inject`, `/faults/stop-all`, `/incidents/{id}/investigate`, `/incidents/{id}/approve`).
- **Non-Root Containers**: Backend Docker containers run under unprivileged user `appuser` (UID 1000).
- **Rate Limiting**: Sliding-window limiter defends against brute force and DDoS on public ingress.
- **Dependency Auditing**: Verified zero known vulnerabilities with `pip-audit`.

For detailed security guidelines, see [`docs/SECURITY.md`](docs/SECURITY.md).

---

## 8. Current Limitations & Future Work

- **In-Process Telemetry Simulator**: Current microservice topology is generated by an in-process discrete-event simulator rather than a live multi-node Kubernetes cluster.
- **Deterministic Service Topology**: Currently models 6 core microservices; enterprise scaling to 100+ services will require dynamic topology discovery via eBPF or service mesh APIs (Istio / Linkerd).
- **Public LLM API Quotas**: Google Gemini Free Tier limits requests to 15 RPM. Production enterprise deployments should use Vertex AI or dedicated LLM endpoints with auto-scaling quotas.

---

## 9. License

This project is licensed under the [MIT License](LICENSE).
