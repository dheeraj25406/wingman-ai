import pytest
from agent.tools.diagnostic_tools import diagnostic_tools
from agent.retrieval.runbook_rag import runbook_rag
from agent.graph.investigation_graph import investigation_graph
from agent.state.investigation_state import InvestigationStateDict


def test_diagnostic_tools():
    from simulator.telemetry.buffer import telemetry_buffer, ServiceMetricPoint
    import time
    telemetry_buffer.record_metric(ServiceMetricPoint(
        timestamp="2026-11-11T09:00:00Z",
        epoch=time.time(),
        service_id="checkout-service",
        cpu_utilization=25.0,
        memory_utilization=38.0,
        request_rate=15.0,
        error_rate=0.001,
        latency_p50=25.0,
        latency_p95=50.0,
        latency_p99=80.0,
        db_connections=12.0,
        queue_depth=5.0,
        timeout_rate=0.0
    ))
    metrics = diagnostic_tools.get_service_metrics("checkout-service", limit=10)
    assert metrics["status"] == "OK"
    assert metrics["service_id"] == "checkout-service"

    svc_map = diagnostic_tools.get_service_map()
    assert "dependencies" in svc_map
    assert "checkout-service" in svc_map["dependencies"]


def test_runbook_rag_hybrid_retrieval():
    results = runbook_rag.retrieve("connection pool saturated timeout", service_id="order-service", top_k=2)
    assert len(results) > 0
    top = results[0]
    assert "relevance_score" in top
    assert "citation" in top
    assert "order-service" in top["service"] or "RB-DB-001" in top["doc_id"]


def test_langgraph_workflow_execution():
    state = InvestigationStateDict(
        incident_id="inc-test-001",
        title="Test Incident Investigation",
        primary_service_id="order-service",
        affected_service_ids=["order-service", "checkout-service"],
        severity="P1_CRITICAL",
        detected_at="2026-11-11T09:00:00Z",
        anomaly_score=0.91,
        predicted_category="DB_POOL_EXHAUSTION",
        ml_confidence=0.97,
        abnormal_features=[{"feature": "db_connections", "value": 99.0, "deviation_sigma": 4.5}],
    )

    final_state = investigation_graph.invoke(state)

    assert final_state["current_node"] == "RECOVERY_VERIFICATION"
    assert len(final_state["hypotheses"]) > 0
    top_hyp = final_state["hypotheses"][0]
    assert top_hyp.confidence_score >= 0.8
    assert len(top_hyp.supporting_evidence_ids) > 0
    assert final_state["remediation_proposal"] is not None
    assert final_state["safety_check_passed"] is True
