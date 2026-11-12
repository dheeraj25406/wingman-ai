import uuid
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, AliasChoices


class HypothesisItem(BaseModel):
    id: str = Field(default_factory=lambda: f"hyp-{uuid.uuid4().hex[:6]}")
    rank: int = 1
    root_cause: str = Field(
        ...,
        validation_alias=AliasChoices("root_cause", "hypothesis", "cause", "title"),
    )
    explanation: str = Field(
        default="Telemetry anomaly correlated with service degradation.",
        validation_alias=AliasChoices("explanation", "description", "summary", "detail"),
    )
    confidence_score: float = Field(
        default=0.85,
        ge=0.0,
        le=1.0,
        validation_alias=AliasChoices("confidence_score", "confidence", "score"),
    )
    supporting_evidence_ids: List[str] = Field(
        default_factory=list,
        validation_alias=AliasChoices("supporting_evidence_ids", "evidence_ids", "evidence"),
    )
    contradictory_evidence_ids: List[str] = []
    affected_services: List[str] = []
    recommended_remediation: str = Field(
        default="RESTART_SERVICE",
        validation_alias=AliasChoices("recommended_remediation", "remediation", "action"),
    )
    risks: str = "Low risk bounded container action"
    preconditions: str = "Validate error rate is active"


class HypothesisListResponse(BaseModel):
    hypotheses: List[HypothesisItem] = []
    investigation_summary: str = Field(
        default="Automated AI investigation completed across distributed telemetry and traces.",
        validation_alias=AliasChoices("investigation_summary", "summary", "overview"),
    )
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
    prefetched_diagnostics: Optional[Dict[str, Any]] = None

    # Generated Intelligence
    hypotheses: List[HypothesisItem] = []
    validated_root_cause: Optional[str] = None
    investigation_summary: Optional[str] = None
    remediation_proposal: Optional[Dict[str, Any]] = None
    current_phase: str = "INITIALIZED"
    current_node: str = "INITIALIZED"
    recovery_status: Optional[str] = None
    safety_check_passed: bool = True
    completed_nodes: List[str] = []
    is_terminal: bool = False
