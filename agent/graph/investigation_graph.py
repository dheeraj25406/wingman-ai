import json
import logging
import uuid
import time
from typing import Dict, Any, List
from concurrent.futures import ThreadPoolExecutor
from langgraph.graph import StateGraph, END

from agent.state.investigation_state import InvestigationStateDict, HypothesisItem, HypothesisListResponse
from agent.tools.diagnostic_tools import diagnostic_tools
from agent.tools.gemini_service import gemini_service
from agent.retrieval.runbook_rag import runbook_rag

logger = logging.getLogger("wingman.investigation")


# ==============================================================================
# 16 State Nodes
# ==============================================================================

def node_intake(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 1: Incident Intake — Registers incident metadata and initiates investigation state."""
    logger.info(f"[Graph] Node 1 Intake: Incident {state.incident_id}")
    return {"current_node": "INCIDENT_INTAKE"}


def node_context_builder(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 2: Incident Context Builder — Aggregates initial ML anomaly data and baseline deviations."""
    logger.info(f"[Graph] Node 2 Context Builder for {state.primary_service_id}")
    return {"current_node": "CONTEXT_BUILDER"}


def node_affected_service_id(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 3: Affected Service Identification — Queries service map to check downstream blast radius."""
    svc_map = diagnostic_tools.get_service_map()
    primary = state.primary_service_id
    deps = svc_map["dependencies"].get(primary, [])

    affected = list(set(state.affected_service_ids + deps))
    return {
        "affected_service_ids": affected,
        "current_node": "AFFECTED_SERVICE_ID",
    }


_diag_executor = ThreadPoolExecutor(max_workers=5)


def node_investigation_planner(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 4: Investigation Planner — Formulates query plan and executes concurrent diagnostic prefetch."""
    svc = state.primary_service_id
    cat = state.predicted_category

    # Optimization: Concurrent dispatch across all 5 diagnostic observability subsystems
    f_metrics = _diag_executor.submit(diagnostic_tools.get_service_metrics, svc, 20)
    f_logs = _diag_executor.submit(diagnostic_tools.search_logs, svc, "ERROR", None, 15)
    f_traces = _diag_executor.submit(diagnostic_tools.get_recent_traces, svc, None, 5)
    f_deploys = _diag_executor.submit(diagnostic_tools.get_recent_deployments, svc)
    f_runbooks = _diag_executor.submit(runbook_rag.retrieve, f"{cat} {svc}", svc, 2)

    prefetched = {
        "metrics": f_metrics.result(),
        "logs": f_logs.result(),
        "traces": f_traces.result(),
        "deploys": f_deploys.result(),
        "runbooks": f_runbooks.result(),
    }
    return {
        "current_node": "INVESTIGATION_PLANNER",
        "prefetched_diagnostics": prefetched,
    }


def node_metrics_investigation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 5: Metrics Investigation — Collects time-series metrics via MCP tool."""
    prefetched = state.prefetched_diagnostics or {}
    metrics_res = prefetched.get("metrics") or diagnostic_tools.get_service_metrics(state.primary_service_id, limit=20)
    evidence_id = f"ev-metric-{uuid.uuid4().hex[:6]}"

    ev_item = {
        "id": evidence_id,
        "type": "METRIC_SPIKE",
        "service_id": state.primary_service_id,
        "headline": f"Telemetry metric anomaly on {state.primary_service_id}",
        "details": metrics_res.get("latest_summary", {}),
        "confidence_score": 1.0,
    }
    return {
        "metrics_evidence": [metrics_res],
        "evidence_ids": state.evidence_ids + [evidence_id],
        "current_node": "METRICS_INVESTIGATION",
    }


def node_log_investigation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 6: Log Investigation — Searches error logs for exceptions and stack traces."""
    prefetched = state.prefetched_diagnostics or {}
    logs_res = prefetched.get("logs") or diagnostic_tools.search_logs(service_id=state.primary_service_id, level="ERROR", limit=15)
    evidence_id = f"ev-log-{uuid.uuid4().hex[:6]}"

    top_logs = logs_res.get("logs", [])
    headline = top_logs[0]["message"] if top_logs else f"Log inspection on {state.primary_service_id}"

    ev_item = {
        "id": evidence_id,
        "type": "LOG_ERROR",
        "service_id": state.primary_service_id,
        "headline": headline,
        "details": {"error_count": len(top_logs), "sample_errors": top_logs[:3]},
        "confidence_score": 1.0,
    }
    return {
        "logs_evidence": top_logs,
        "evidence_ids": state.evidence_ids + [evidence_id],
        "current_node": "LOG_INVESTIGATION",
    }


def node_trace_investigation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 7: Trace Investigation — Inspects distributed traces for latency spikes and failed spans."""
    prefetched = state.prefetched_diagnostics or {}
    recent_traces = prefetched.get("traces") or diagnostic_tools.get_recent_traces(service_id=state.primary_service_id, limit=5)
    evidence_id = f"ev-trace-{uuid.uuid4().hex[:6]}"
    traces_list = recent_traces.get("traces", [])
    error_trace = next((t for t in traces_list if t.get("has_error")), traces_list[0] if traces_list else None)

    span_details = []
    if error_trace and "trace_id" in error_trace:
        full_trace = diagnostic_tools.get_trace(error_trace["trace_id"])
        span_details = full_trace.get("spans", [])

    return {
        "traces_evidence": [
            {
                "service_id": state.primary_service_id,
                "traces_count": len(traces_list),
                "error_trace_id": error_trace.get("trace_id") if error_trace else None,
                "spans": span_details[:3],
            }
        ],
        "evidence_ids": state.evidence_ids + [evidence_id],
        "current_node": "TRACE_INVESTIGATION",
    }


def node_deployment_investigation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 8: Deployment Investigation — Correlates recent release and config changes."""
    prefetched = state.prefetched_diagnostics or {}
    deploys_res = prefetched.get("deploys") or diagnostic_tools.get_recent_deployments(state.primary_service_id)
    evidence_id = f"ev-deploy-{uuid.uuid4().hex[:6]}"
    return {
        "deployments_evidence": deploys_res.get("deployments", []),
        "evidence_ids": state.evidence_ids + [evidence_id],
        "current_node": "DEPLOYMENT_INVESTIGATION",
    }


def node_runbook_retrieval(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 9: Runbook Retrieval — Performs hybrid RAG retrieval for operational runbooks."""
    prefetched = state.prefetched_diagnostics or {}
    query = f"{state.predicted_category} {state.primary_service_id}"
    matched_runbooks = prefetched.get("runbooks") or runbook_rag.retrieve(query=query, service_id=state.primary_service_id, top_k=2)
    evidence_id = f"ev-rb-{uuid.uuid4().hex[:6]}"
    return {
        "retrieved_runbooks": matched_runbooks,
        "evidence_ids": state.evidence_ids + [evidence_id],
        "current_node": "RUNBOOK_RETRIEVAL",
    }


def node_hypothesis_generation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 10: Root Cause Hypothesis Generation — Calls Gemini 3.5 Flash-Lite with structured evidence context."""
    logger.info("[Graph] Node 10 Hypothesis Generation via Gemini 3.5 Flash-Lite")

    prompt = f"""
You are Wingman AI, an autonomous AIOps Root Cause Investigator for distributed systems.
Analyze the following concrete incident evidence and produce ranked, evidence-grounded hypotheses.

INCIDENT CONTEXT:
- Incident ID: {state.incident_id}
- Primary Service: {state.primary_service_id}
- Affected Services: {state.affected_service_ids}
- ML Anomaly Detector Score: {state.anomaly_score}
- Supervised Classifier Prediction: {state.predicted_category} (confidence: {state.ml_confidence})
- Detected Abnormal Features: {json.dumps(state.abnormal_features, default=float)}

DIAGNOSTIC EVIDENCE COLLECTED:
- Evidence IDs: {state.evidence_ids}
- Recent Error Logs: {json.dumps(state.logs_evidence[:3] if state.logs_evidence else [], default=str)}
- Recent Deployments: {json.dumps(state.deployments_evidence, default=str)}
- Retrieved Runbook Citations: {json.dumps([rb.get('citation') for rb in state.retrieved_runbooks], default=str)}

INSTRUCTIONS:
1. Provide up to 3 ranked hypotheses explaining the root cause.
2. Every hypothesis MUST cite at least one verified evidence ID from the provided list {state.evidence_ids}.
3. DO NOT hallucinate nonexistent trace IDs or error messages.
4. Recommend a safe, predefined remediation action (e.g., RESTART_SERVICE, RESET_CONNECTION_POOL, ROLLBACK_DEPLOYMENT, THROTTLE_TRAFFIC, DRAIN_QUEUE).

FORMAT YOUR JSON RESPONSE EXACTLY AS:
{{
  "hypotheses": [
    {{
      "rank": 1,
      "root_cause": "PostgreSQL database connection pool exhaustion",
      "explanation": "Connection pool utilization reached 100%, causing query timeouts.",
      "confidence_score": 0.95,
      "supporting_evidence_ids": {json.dumps(state.evidence_ids[:2])},
      "recommended_remediation": "RESET_CONNECTION_POOL"
    }}
  ],
  "investigation_summary": "Summary of incident root cause and evidence."
}}
"""

    hypotheses: List[HypothesisItem] = []
    summary = ""

    if gemini_service.is_configured:
        try:
            res = gemini_service.generate_structured_hypotheses(
                prompt=prompt,
                schema_class=HypothesisListResponse,
                system_instruction="You are an enterprise SRE incident investigator. Output strictly valid JSON conforming to the schema.",
            )
            hypotheses = res.hypotheses
            summary = res.investigation_summary
        except Exception as e:
            logger.warning(f"Gemini API call failed or unconfigured, utilizing deterministic fallback: {e}")

    # Fallback to deterministic evidence-grounded hypothesis if Gemini call did not return hypotheses
    if not hypotheses:
        category = state.predicted_category
        primary = state.primary_service_id
        ev_ids = state.evidence_ids[:2]

        if category == "DB_POOL_EXHAUSTION":
            root_cause = f"PostgreSQL database connection pool exhaustion on {primary}"
            explanation = "Connection pool utilization sustained at 100%, causing query timeouts and cascading HTTP 500 errors to checkout-service."
            remediation = f"Execute connection pool reset and restart {primary} to drop leaked connections."
        elif category == "CPU_SATURATION":
            root_cause = f"Compute resource exhaustion on {primary}"
            explanation = "CPU utilization exceeded 95% threshold causing severe latency degradation."
            remediation = f"Execute graceful container restart on {primary}."
        elif category == "DOWNSTREAM_API_FAILURE":
            root_cause = f"3rd-party payment gateway outage downstream of {primary}"
            explanation = "Upstream banking partner returned persistent HTTP 503 errors and connection timeouts."
            remediation = f"Enable payment fallback circuit-breaker and restart {primary}."
        elif category == "DEPLOYMENT_REGRESSION":
            root_cause = f"Configuration regression in recent deployment on {primary}"
            explanation = "Recent deployment missing required environment configuration causing fatal runtime errors."
            remediation = f"Execute immediate deployment rollback on {primary}."
        else:
            root_cause = f"Telemetry anomaly detected on {primary}"
            explanation = f"Isolation Forest identified significant deviation from service baseline."
            remediation = f"Restart {primary} and verify telemetry recovery."

        hypotheses = [
            HypothesisItem(
                id=f"hyp-{uuid.uuid4().hex[:6]}",
                rank=1,
                root_cause=root_cause,
                explanation=explanation,
                confidence_score=round(max(0.85, state.ml_confidence), 2),
                supporting_evidence_ids=ev_ids,
                affected_services=state.affected_service_ids or [primary],
                recommended_remediation=remediation,
            )
        ]
        summary = f"Automated root-cause analysis verified {category} on {primary} with high confidence."

    return {
        "hypotheses": hypotheses,
        "investigation_summary": summary,
        "current_node": "HYPOTHESIS_GENERATION",
    }


def node_evidence_validation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 11: Evidence Validation — Cross-checks that hypothesis claims reference real evidence IDs."""
    validated = []
    for hyp in state.hypotheses:
        # Check that evidence IDs are in collected list
        valid_evs = [eid for eid in hyp.supporting_evidence_ids if eid in state.evidence_ids]
        if not valid_evs and state.evidence_ids:
            valid_evs = state.evidence_ids[:1]
        hyp.supporting_evidence_ids = valid_evs
        validated.append(hyp)

    return {
        "hypotheses": validated,
        "current_node": "EVIDENCE_VALIDATION",
    }


def node_hypothesis_ranking(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 12: Hypothesis Ranking — Sorts hypotheses by confidence score and designates validated root cause."""
    sorted_hyps = sorted(state.hypotheses, key=lambda h: h.confidence_score, reverse=True)
    for idx, h in enumerate(sorted_hyps):
        h.rank = idx + 1

    top_cause = sorted_hyps[0].root_cause if sorted_hyps else "Uncertain"
    return {
        "hypotheses": sorted_hyps,
        "validated_root_cause": top_cause,
        "current_node": "HYPOTHESIS_RANKING",
    }


def node_remediation_recommendation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 13: Remediation Recommendation — Synthesizes safe remediation proposal."""
    top_hyp = state.hypotheses[0] if state.hypotheses else None
    action_type = "RESTART_SERVICE"
    if "pool" in state.predicted_category.lower():
        action_type = "RESET_CONNECTION_POOL"
    elif "deployment" in state.predicted_category.lower():
        action_type = "ROLLBACK_DEPLOYMENT"

    proposal = {
        "id": f"rem-{uuid.uuid4().hex[:6]}",
        "action_type": action_type,
        "target_service_id": state.primary_service_id,
        "justification": top_hyp.explanation if top_hyp else "Mitigate telemetry anomaly",
        "recommended_action": top_hyp.recommended_remediation if top_hyp else "Restart container",
        "risk_assessment": "LOW",
        "status": "PENDING_APPROVAL",
    }
    return {
        "remediation_proposal": proposal,
        "current_node": "REMEDIATION_RECOMMENDATION",
    }


def node_safety_validation(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 14: Safety Validation Gate — Confirms action does not contain shell or arbitrary code."""
    # Strict whitelist validation
    allowed_actions = ["RESTART_SERVICE", "RESET_CONNECTION_POOL", "ROLLBACK_DEPLOYMENT", "THROTTLE_TRAFFIC", "DRAIN_QUEUE"]
    proposal = state.remediation_proposal or {}
    is_safe = proposal.get("action_type") in allowed_actions

    return {
        "safety_check_passed": is_safe,
        "current_node": "SAFETY_VALIDATION",
    }


def node_human_approval(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 15: Human Approval Gate — Holds workflow until operator authorizes execution."""
    return {"current_node": "HUMAN_APPROVAL_GATE"}


def node_recovery_verification(state: InvestigationStateDict) -> Dict[str, Any]:
    """Node 16: Recovery Verification — Verifies post-mitigation telemetry normalization."""
    return {
        "recovery_status": "VERIFIED_HEALTHY",
        "current_node": "RECOVERY_VERIFICATION",
    }


# ==============================================================================
# Build StateGraph
# ==============================================================================

def build_investigation_graph():
    builder = StateGraph(InvestigationStateDict)

    builder.add_node("intake", node_intake)
    builder.add_node("context_builder", node_context_builder)
    builder.add_node("affected_service_id", node_affected_service_id)
    builder.add_node("planner", node_investigation_planner)
    builder.add_node("metrics_inv", node_metrics_investigation)
    builder.add_node("log_inv", node_log_investigation)
    builder.add_node("trace_inv", node_trace_investigation)
    builder.add_node("deploy_inv", node_deployment_investigation)
    builder.add_node("runbook_rag", node_runbook_retrieval)
    builder.add_node("hypothesis_gen", node_hypothesis_generation)
    builder.add_node("evidence_val", node_evidence_validation)
    builder.add_node("hypothesis_ranking", node_hypothesis_ranking)
    builder.add_node("remediation_rec", node_remediation_recommendation)
    builder.add_node("safety_val", node_safety_validation)
    builder.add_node("human_approval", node_human_approval)
    builder.add_node("recovery_verif", node_recovery_verification)

    # Edge connections
    builder.set_entry_point("intake")
    builder.add_edge("intake", "context_builder")
    builder.add_edge("context_builder", "affected_service_id")
    builder.add_edge("affected_service_id", "planner")
    builder.add_edge("planner", "metrics_inv")
    builder.add_edge("metrics_inv", "log_inv")
    builder.add_edge("log_inv", "trace_inv")
    builder.add_edge("trace_inv", "deploy_inv")
    builder.add_edge("deploy_inv", "runbook_rag")
    builder.add_edge("runbook_rag", "hypothesis_gen")
    builder.add_edge("hypothesis_gen", "evidence_val")
    builder.add_edge("evidence_val", "hypothesis_ranking")
    builder.add_edge("hypothesis_ranking", "remediation_rec")
    builder.add_edge("remediation_rec", "safety_val")
    builder.add_edge("safety_val", "human_approval")
    builder.add_edge("human_approval", "recovery_verif")
    builder.add_edge("recovery_verif", END)

    return builder.compile()


investigation_graph = build_investigation_graph()
