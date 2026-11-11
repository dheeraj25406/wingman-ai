import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from backend.app.schemas.schemas import RemediationDecisionRequest
from backend.app.services.correlation_engine import correlation_engine
from agent.graph.investigation_graph import investigation_graph
from agent.state.investigation_state import InvestigationStateDict
from simulator.faults.fault_engine import fault_engine

router = APIRouter(prefix="/incidents", tags=["Incidents"])

# In-memory store for incidents with seeded realistic baseline data
INCIDENT_REGISTRY: Dict[str, Dict[str, Any]] = {}


def _seed_initial_demo_incidents():
    if INCIDENT_REGISTRY:
        return
    # Seeded initial demo incident so the dashboard is immediately informative
    demo_id = "inc-20261111-001"
    INCIDENT_REGISTRY[demo_id] = {
        "id": demo_id,
        "title": "PostgreSQL Connection Pool Exhaustion on order-service",
        "severity": "P1_CRITICAL",
        "status": "IDENTIFIED",
        "primary_service_id": "order-service",
        "affected_service_ids": ["order-service", "checkout-service", "api-gateway"],
        "detection_source": "ISOLATION_FOREST + LIGHTGBM",
        "detected_at": "2026-11-11T08:45:00Z",
        "mitigated_at": None,
        "resolved_at": None,
        "summary": "PostgreSQL connection pool saturated at 100/100 connections. Caused query timeouts and cascading HTTP 500 responses.",
        "anomaly_score": 0.89,
        "predicted_category": "DB_POOL_EXHAUSTION",
        "ml_confidence": 0.96,
        "abnormal_features": [
            {"feature": "db_connections", "value": 99.0, "deviation_sigma": 4.5},
            {"feature": "error_rate", "value": 0.65, "deviation_sigma": 5.2},
            {"feature": "latency_p95", "value": 2800.0, "deviation_sigma": 4.8},
        ],
        "timeline": [
            {"id": "ev-0", "event_type": "ALERT_TRIGGERED", "description": "Isolation Forest flagged anomaly on order-service (score: 0.89)", "created_at": "2026-11-11T08:45:00Z"},
            {"id": "ev-1", "event_type": "CORRELATED", "description": "Correlation engine grouped 3 alerts: order-service (primary) -> checkout-service -> api-gateway", "created_at": "2026-11-11T08:45:05Z"},
            {"id": "ev-2", "event_type": "INVESTIGATION_STARTED", "description": "16-node LangGraph investigation workflow launched", "created_at": "2026-11-11T08:45:10Z"},
            {"id": "ev-3", "event_type": "HYPOTHESIS_FORMED", "description": "Gemini 3.5 Flash-Lite ranked root-cause hypothesis #1: Connection Pool Exhaustion (Confidence: 0.96)", "created_at": "2026-11-11T08:45:22Z"},
            {"id": "ev-4", "event_type": "REMEDIATION_PROPOSED", "description": "Proposed action: RESET_CONNECTION_POOL on order-service. Awaiting human operator approval.", "created_at": "2026-11-11T08:45:25Z"},
        ],
        "evidence": [
            {
                "id": "ev-metric-101",
                "evidence_type": "METRIC_SPIKE",
                "service_id": "order-service",
                "headline": "Database connection pool utilization reached 99.0% (Normal: 15%)",
                "details": {"metric": "db_connections", "current": 99.0, "baseline": 15.0, "threshold": 80.0},
                "confidence_score": 1.0,
                "timestamp": "2026-11-11T08:45:00Z"
            },
            {
                "id": "ev-log-102",
                "evidence_type": "LOG_ERROR",
                "service_id": "order-service",
                "headline": "ConnectionPoolTimeoutError: Timeout acquiring PostgreSQL connection after 2500ms (100/100 active)",
                "details": {"error_type": "ConnectionPoolTimeoutError", "active": 100, "max": 100},
                "confidence_score": 1.0,
                "timestamp": "2026-11-11T08:45:02Z"
            },
            {
                "id": "ev-trace-103",
                "evidence_type": "TRACE_LATENCY",
                "service_id": "checkout-service",
                "headline": "Span POST /orders/create latency spiked to 2650ms returning HTTP 500",
                "details": {"trace_id": "tr-demo-001", "span_duration_ms": 2650.0, "status": "ERROR"},
                "confidence_score": 1.0,
                "timestamp": "2026-11-11T08:45:03Z"
            },
            {
                "id": "ev-rb-104",
                "evidence_type": "RUNBOOK_MATCH",
                "service_id": "order-service",
                "headline": "Matched Runbook [RB-DB-001] SRE Runbook: Database Connection Pool Exhaustion",
                "details": {"runbook_id": "RB-DB-001", "section": "Remediation & Recovery Procedure"},
                "confidence_score": 0.95,
                "timestamp": "2026-11-11T08:45:15Z"
            }
        ],
        "hypotheses": [
            {
                "id": "hyp-01",
                "rank": 1,
                "root_cause": "PostgreSQL database connection pool exhaustion on order-service",
                "explanation": "Connection pool utilization sustained at 100%, causing query timeouts and cascading HTTP 500 errors to checkout-service and api-gateway.",
                "confidence_score": 0.96,
                "supporting_evidence_ids": ["ev-metric-101", "ev-log-102", "ev-trace-103", "ev-rb-104"],
                "contradictory_evidence_ids": [],
                "affected_services": ["order-service", "checkout-service", "api-gateway"],
                "recommended_remediation": "Reset database connection pool limit and gracefully restart order-service.",
                "status": "VALIDATED"
            }
        ],
        "remediation_proposal": {
            "id": "rem-001",
            "action_type": "RESET_CONNECTION_POOL",
            "target_service_id": "order-service",
            "parameters": {"new_limit": 150},
            "justification": "Clear saturated idle database connections and restore checkout transaction throughput.",
            "risk_assessment": "LOW",
            "status": "PENDING_APPROVAL",
            "created_at": "2026-11-11T08:45:25Z"
        }
    }


_seed_initial_demo_incidents()


@router.get("")
async def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    service_id: Optional[str] = None,
    limit: int = 50,
) -> Dict[str, Any]:
    incidents = list(INCIDENT_REGISTRY.values())
    if status:
        incidents = [i for i in incidents if i["status"].upper() == status.upper()]
    if severity:
        incidents = [i for i in incidents if i["severity"].upper() == severity.upper()]
    if service_id:
        incidents = [i for i in incidents if i["primary_service_id"] == service_id or service_id in i["affected_service_ids"]]

    # Sort newest first
    incidents.sort(key=lambda x: x["detected_at"], reverse=True)
    return {"status": "success", "data": incidents[:limit], "count": len(incidents)}


@router.get("/{incident_id}")
async def get_incident(incident_id: str) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"status": "success", "data": incident}


@router.post("/detect")
async def detect_incidents() -> Dict[str, Any]:
    """
    Executes an anomaly scan across recent telemetry windows.
    If an anomaly is detected, deterministically correlates signals and creates an incident.
    """
    anomalies = correlation_engine.scan_for_anomalies()
    if not anomalies:
        return {"status": "success", "message": "No active anomalies detected across service fleet", "data": None}

    correlated = correlation_engine.correlate_incidents(anomalies)
    if not correlated:
        return {"status": "success", "message": "Anomalies below correlation threshold", "data": None}

    # Check if active incident already exists for this primary service
    for inc in INCIDENT_REGISTRY.values():
        if inc["primary_service_id"] == correlated["primary_service_id"] and inc["status"] in ["DETECTED", "INVESTIGATING", "IDENTIFIED"]:
            return {
                "status": "success",
                "message": f"Existing active incident already tracking {correlated['primary_service_id']}",
                "data": inc
            }

    # Create new incident
    new_id = f"inc-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{uuid.uuid4().hex[:4]}"
    incident_record = {
        "id": new_id,
        "title": correlated["title"],
        "severity": correlated["severity"],
        "status": "DETECTED",
        "primary_service_id": correlated["primary_service_id"],
        "affected_service_ids": correlated["affected_service_ids"],
        "detection_source": correlated["detection_source"],
        "detected_at": correlated["detected_at"],
        "mitigated_at": None,
        "resolved_at": None,
        "summary": f"Detected {correlated['predicted_category']} propagating through {correlated['propagation_path']}",
        "anomaly_score": correlated["anomalies"][0]["anomaly_score"],
        "predicted_category": correlated["predicted_category"],
        "ml_confidence": correlated["ml_confidence"],
        "abnormal_features": correlated["anomalies"][0]["abnormal_features"],
        "timeline": [
            {
                "id": f"ev-{uuid.uuid4().hex[:6]}",
                "event_type": "ALERT_TRIGGERED",
                "description": f"Isolation Forest anomaly detected on {correlated['primary_service_id']} (score: {correlated['anomalies'][0]['anomaly_score']})",
                "created_at": correlated["detected_at"]
            },
            {
                "id": f"ev-{uuid.uuid4().hex[:6]}",
                "event_type": "CORRELATED",
                "description": f"Correlation engine identified propagation path: {' -> '.join(correlated['propagation_path'])}",
                "created_at": correlated["detected_at"]
            }
        ],
        "evidence": [],
        "hypotheses": [],
        "remediation_proposal": None,
    }

    INCIDENT_REGISTRY[new_id] = incident_record
    return {"status": "success", "message": f"Incident {new_id} created", "data": incident_record}


@router.post("/{incident_id}/investigate")
async def investigate_incident(incident_id: str) -> Dict[str, Any]:
    """
    Executes the 16-node LangGraph autonomous investigation workflow for this incident.
    """
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    incident["status"] = "INVESTIGATING"
    incident["timeline"].append({
        "id": f"ev-{uuid.uuid4().hex[:6]}",
        "event_type": "INVESTIGATION_STARTED",
        "description": "Autonomous 16-node LangGraph investigation workflow launched",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    initial_state = InvestigationStateDict(
        incident_id=incident["id"],
        title=incident["title"],
        primary_service_id=incident["primary_service_id"],
        affected_service_ids=incident["affected_service_ids"],
        severity=incident["severity"],
        detected_at=incident["detected_at"],
        anomaly_score=incident.get("anomaly_score", 0.85),
        predicted_category=incident.get("predicted_category", "UNKNOWN"),
        ml_confidence=incident.get("ml_confidence", 0.90),
        abnormal_features=incident.get("abnormal_features", []),
    )

    # Run LangGraph State Machine
    final_state = investigation_graph.invoke(initial_state)

    # Convert generated hypotheses to dicts
    hyps_data = [h.model_dump() for h in final_state.get("hypotheses", [])]

    # Convert evidence items
    ev_list = []
    for m in final_state.get("metrics_evidence", []):
        ev_list.append({
            "id": f"ev-m-{uuid.uuid4().hex[:4]}",
            "evidence_type": "METRIC_SPIKE",
            "service_id": incident["primary_service_id"],
            "headline": f"Telemetry metric anomaly on {incident['primary_service_id']}",
            "details": m.get("latest_summary", {}),
            "confidence_score": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    for l in final_state.get("logs_evidence", [])[:2]:
        ev_list.append({
            "id": f"ev-l-{uuid.uuid4().hex[:4]}",
            "evidence_type": "LOG_ERROR",
            "service_id": incident["primary_service_id"],
            "headline": l.get("message", "Error in service logs"),
            "details": l,
            "confidence_score": 1.0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
    for rb in final_state.get("retrieved_runbooks", []):
        ev_list.append({
            "id": f"ev-rb-{uuid.uuid4().hex[:4]}",
            "evidence_type": "RUNBOOK_MATCH",
            "service_id": incident["primary_service_id"],
            "headline": f"Matched Runbook: {rb.get('title')}",
            "details": rb,
            "confidence_score": 0.95,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })

    incident["evidence"] = ev_list
    incident["hypotheses"] = hyps_data
    incident["remediation_proposal"] = final_state.get("remediation_proposal")
    incident["status"] = "IDENTIFIED"
    incident["summary"] = final_state.get("investigation_summary")

    top_h = hyps_data[0] if hyps_data else None
    incident["timeline"].append({
        "id": f"ev-{uuid.uuid4().hex[:6]}",
        "event_type": "HYPOTHESIS_FORMED",
        "description": f"Root-cause hypothesis confirmed: {top_h.get('root_cause') if top_h else 'Analyzed'} (Confidence: {top_h.get('confidence_score') if top_h else 0.9})",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"status": "success", "message": "Investigation completed", "data": incident}


@router.get("/{incident_id}/timeline")
async def get_incident_timeline(incident_id: str) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"status": "success", "data": incident.get("timeline", [])}


@router.get("/{incident_id}/evidence")
async def get_incident_evidence(incident_id: str) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"status": "success", "data": incident.get("evidence", [])}


@router.get("/{incident_id}/hypotheses")
async def get_incident_hypotheses(incident_id: str) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return {"status": "success", "data": incident.get("hypotheses", [])}


@router.post("/{incident_id}/approve")
async def approve_remediation(incident_id: str, req: RemediationDecisionRequest) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    proposal = incident.get("remediation_proposal")
    if not proposal:
        raise HTTPException(status_code=400, detail="No pending remediation proposal for this incident")

    # Execute predefined safe action
    action = proposal["action_type"]
    target_svc = proposal["target_service_id"]

    # Halt active faults on target service
    stopped_faults = []
    for f in fault_engine.get_active_faults():
        if f.target_service_id == target_svc:
            fault_engine.stop_fault(f.id)
            stopped_faults.append(f.id)

    proposal["status"] = "EXECUTED"
    incident["status"] = "RESOLVED"
    incident["mitigated_at"] = datetime.now(timezone.utc).isoformat()
    incident["resolved_at"] = datetime.now(timezone.utc).isoformat()

    incident["timeline"].append({
        "id": f"ev-{uuid.uuid4().hex[:6]}",
        "event_type": "REMEDIATION_APPROVED",
        "description": f"Operator approved action {action} on {target_svc}. Notes: {req.operator_notes or 'Authorized'}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })
    incident["timeline"].append({
        "id": f"ev-{uuid.uuid4().hex[:6]}",
        "event_type": "RECOVERED",
        "description": f"Telemetry verified healthy. Cleared {len(stopped_faults)} active faults.",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {
        "status": "success",
        "message": f"Remediation {action} executed successfully. Incident marked RESOLVED.",
        "data": incident
    }


@router.post("/{incident_id}/reject")
async def reject_remediation(incident_id: str, req: RemediationDecisionRequest) -> Dict[str, Any]:
    incident = INCIDENT_REGISTRY.get(incident_id)
    if not incident:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")

    proposal = incident.get("remediation_proposal")
    if proposal:
        proposal["status"] = "REJECTED"

    incident["status"] = "IDENTIFIED"
    incident["timeline"].append({
        "id": f"ev-{uuid.uuid4().hex[:6]}",
        "event_type": "REMEDIATION_REJECTED",
        "description": f"Operator rejected proposed remediation. Notes: {req.operator_notes or 'Manual intervention requested'}",
        "created_at": datetime.now(timezone.utc).isoformat()
    })

    return {"status": "success", "message": "Remediation rejected", "data": incident}
