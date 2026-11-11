# Wingman AI — Agentic Investigation Engine Design (LangGraph + MCP + Gemini)

The investigation engine operates under the mandate:
> **"The investigation agent determines WHY it is happening."**

It follows a strictly orchestrated 16-node state machine built with **LangGraph**, communicating with observability backends via the **Model Context Protocol (MCP)**, reasoning through **Google Gemini 3.5 Flash-Lite**, and validating every output with **Pydantic**.

---

## 1. LangGraph State Machine Graph

```mermaid
flowchart TD
    N1[1. Incident Intake] --> N2[2. Context Builder]
    N2 --> N3[3. Affected Service Identification]
    N3 --> N4[4. Investigation Planner]
    
    subgraph Tool Diagnostic Phase (MCP Tools)
        N4 --> N5[5. Metrics Investigation]
        N5 --> N6[6. Log Investigation]
        N6 --> N7[7. Trace Investigation]
        N7 --> N8[8. Deployment Investigation]
    end
    
    N8 --> N9[9. Runbook Retrieval (Hybrid RAG)]
    N9 --> N10[10. Root Cause Hypothesis Generation (Gemini)]
    N10 --> N11[11. Evidence Validation]
    
    N11 --> CheckValid{Evidence Valid?}
    CheckValid -- Incomplete / Low Confidence --> BoundedLoop[Refine Plan / Bounded Loop <= 2]
    BoundedLoop --> N4
    CheckValid -- Confirmed --> N12[12. Hypothesis Ranking]
    
    N12 --> N13[13. Remediation Recommendation]
    N13 --> N14[14. Safety Validation Gate]
    N14 --> N15[15. Human Approval Gate]
    N15 --> N16[16. Recovery Verification]
```

---

## 2. Typed State Schema (`InvestigationState`)

```python
class InvestigationState(TypedDict):
    incident_id: str
    primary_service: str
    affected_services: list[str]
    timeline_start: str
    timeline_end: str
    anomalous_features: list[str]
    ml_predicted_category: str
    ml_confidence: float
    
    # Collected Evidence
    collected_metrics: list[dict]
    collected_logs: list[dict]
    collected_traces: list[dict]
    recent_deployments: list[dict]
    retrieved_runbooks: list[dict]
    evidence_ids: list[str]
    
    # Reasoning & Hypotheses
    hypotheses: list[HypothesisSchema]
    validated_root_cause: str | None
    investigation_loop_count: int
    
    # Remediation
    remediation_proposal: RemediationSchema | None
    safety_check_passed: bool
    human_approved: bool | None
    recovery_status: str | None
```

---

## 3. Strict Model & Gemini Service Constraints
- **Model**: `gemini-3.5-flash-lite`
- **SDK**: `google-genai` (official Google Gen AI Python SDK)
- **Centralized Service Abstraction**: `GeminiService` with circuit-breaker, structured JSON output mode, exponential backoff, retry limits, and Pydantic response parsing.
- **Forbidden**: OpenAI, Claude, Groq, OpenRouter, or fallback LLM providers. If Gemini is unreachable, return a structured diagnostic failure without fabricating hallucinated hypotheses.

---

## 4. Model Context Protocol (MCP) Server Tools
All diagnostics are exposed as read-only, strict-schema MCP tools:
1. `get_service_metrics(service_id, start_time, end_time, metric_names)`
2. `search_logs(service_id, start_time, end_time, min_level, query_filter)`
3. `get_trace(trace_id)`
4. `get_service_map()`
5. `get_recent_deployments(service_id, lookback_minutes)`
6. `get_runbook(topic, service_id)`
7. `compare_service_baseline(service_id, window_minutes)`
8. `get_incident_history(service_id, limit)`

---

## 5. Hybrid Runbook RAG
- Documents chunked by markdown section with metadata (`title`, `service`, `category`, `symptoms`, `remediation_steps`).
- **Dense Retrieval**: `sentence-transformers/all-MiniLM-L6-v2` with Qdrant vector database (fallback: in-memory cosine store).
- **Sparse Retrieval**: BM25 ranking.
- **Hybrid Fusion**: Reciprocal Rank Fusion (RRF) to blend semantic intent and exact operational keywords.
- **Citation Integrity**: Every recommendation from a runbook must cite the exact document and section reference.

---

## 6. Safety & Human Approval Gate
Remediation actions are strictly predefined Python callbacks:
- `restart_service(service_name)`
- `rollback_deployment(service_name, target_version)`
- `reset_db_pool_limit(service_name, new_limit)`
- `throttle_traffic_load(service_name, factor)`
- `drain_queue_backlog(service_name)`

**The agent NEVER has access to an open shell, arbitrary SQL execution, or file write operations.**
Execution requires explicit operator approval logged with timestamp and user notes.
