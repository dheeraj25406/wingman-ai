# Wingman AI — Test Strategy & Verification Plan

## 1. Multi-Tier Testing Architecture

```
[Level 1: Unit Tests]
├── Backend Schemas & Database Models
├── ML Feature Extractor & Math Utilities
├── MCP Tool Input/Output Schemas
└── LangGraph Node State Reducers

[Level 2: Model & Benchmark Tests]
├── Isolation Forest Anomaly Scoring & Thresholds
├── LightGBM Supervised Classifier (Group-aware test split)
├── Hybrid RAG Retrieval (MRR, BM25 vs Vector)
└── Evaluation Suite (Deterministic ground-truth validation)

[Level 3: Agent Workflow Tests]
├── LangGraph Full Workflow with Gemini Mock
├── LangGraph Live Workflow with Gemini 3.5 Flash-Lite
├── Tool Call Sequence & Schema Conformance
└── Human Approval Safety Gate Enforcement

[Level 4: End-to-End System Integration Test]
└── Automated Simulation Loop:
    1. Start Services & Telemetry Simulator
    2. Inject "DB Connection Pool Exhaustion" Fault
    3. Run Anomaly Scan (Isolation Forest catches anomaly)
    4. Correlate Incident (Order Service -> Payment Service)
    5. Trigger LangGraph Investigation
    6. Verify Evidence Collection via MCP
    7. Inspect Ranked Hypotheses
    8. Approve Remediation Action
    9. Verify Recovery & Healthy Telemetry
```

---

## 2. Test Execution Commands

```bash
# Backend unit & integration tests
pytest backend/tests/ -v

# Machine Learning validation & baseline tests
pytest ml/tests/ -v
python -m ml.evaluation.evaluate_models

# Agent workflow tests
pytest agent/tests/ -v

# Full system end-to-end integration scenario
python -m tests.test_end_to_end_scenario
```

---

## 3. Continuous Benchmark Criteria
- **ML Detection Delay**: < 15 seconds after fault injection.
- **ML False Positive Rate**: < 3% under normal traffic.
- **Agent Top-1 Root Cause Accuracy**: > 85% on 25+ ground-truth benchmarks.
- **Zero Unsafe Action Execution**: 100% of remediation actions blocked without human approval.
