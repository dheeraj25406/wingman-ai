from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class HypothesisItem(BaseModel):
    id: str
    rank: int
    root_cause: str
    explanation: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    supporting_evidence_ids: List[str] = []
    contradictory_evidence_ids: List[str] = []
    affected_services: List[str] = []
    recommended_remediation: str
    risks: str = "Low risk bounded container action"
    preconditions: str = "Validate error rate is active"


class HypothesisListResponse(BaseModel):
    hypotheses: List[HypothesisItem] = []
    investigation_summary: str
    root_cause_uncertain: bool = False


class InvestigationStateDict(BaseModel):
    incident_id: str
    title: str
    primary_service_id: str
    affected_service_ids: List[str] = []
    severity: str
    detected_at: str

    # ML Anomaly Inputs
    anomaly_score: float = 0.0
    predicted_category: str = "UNKNOWN"
    ml_confidence: float = 0.0
    abnormal_features: List[Dict[str, Any]] = []

    # Diagnostic Evidence Collected
    metrics_evidence: List[Dict[str, Any]] = []
    logs_evidence: List[Dict[str, Any]] = []
    traces_evidence: List[Dict[str, Any]] = []
    deployments_evidence: List[Dict[str, Any]] = []
    retrieved_runbooks: List[Dict[str, Any]] = []
    evidence_ids: List[str] = []

    # Generated Intelligence
    hypotheses: List[HypothesisItem] = []
    validated_root_cause: Optional[str] = None
    investigation_summary: Optional[str] = None
    investigation_loop_count: int = 0
    current_node: str = "INTAKE"

    # Remediation Proposal & Approval
    remediation_proposal: Optional[Dict[str, Any]] = None
    safety_check_passed: bool = False
    human_approved: Optional[bool] = None
    recovery_status: Optional[str] = None
