from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


# Standard API Response Envelope
class ApiResponse(BaseModel):
    status: str = "success"
    data: Any = None
    message: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# Service Schemas
class ServiceBase(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    status: str = "healthy"
    dependencies: List[str] = []


class ServiceDetail(ServiceBase):
    created_at: datetime
    updated_at: datetime
    current_metrics: Optional[Dict[str, float]] = None


# Metric Schemas
class MetricDataPoint(BaseModel):
    timestamp: str
    cpu_utilization: float
    memory_utilization: float
    request_rate: float
    error_rate: float
    latency_p50: float
    latency_p95: float
    latency_p99: float
    db_connections: float
    queue_depth: float


class MetricsOverview(BaseModel):
    total_services: int
    healthy_services: int
    degraded_services: int
    critical_services: int
    global_error_rate: float
    avg_latency_p95: float
    total_throughput_rps: float
    active_incidents_count: int


# Evidence Schemas
class EvidenceSchema(BaseModel):
    id: str
    incident_id: str
    evidence_type: str
    service_id: str
    headline: str
    details: Dict[str, Any]
    confidence_score: float = 1.0
    timestamp: datetime


# Hypothesis Schemas
class HypothesisSchema(BaseModel):
    id: str
    incident_id: str
    rank: int
    root_cause: str
    confidence_score: float
    explanation: str
    supporting_evidence_ids: List[str] = []
    contradictory_evidence_ids: List[str] = []
    recommended_remediation: str
    status: str = "PROPOSED"


# Remediation Schemas
class RemediationProposalSchema(BaseModel):
    id: str
    incident_id: str
    action_type: str
    target_service_id: str
    parameters: Dict[str, Any] = {}
    justification: str
    risk_assessment: str
    status: str = "PENDING_APPROVAL"
    created_at: datetime


class RemediationDecisionRequest(BaseModel):
    proposal_id: str
    operator_notes: Optional[str] = None
    force_failure: bool = False


# Incident Schemas
class IncidentBase(BaseModel):
    id: str
    title: str
    severity: str
    status: str
    primary_service_id: str
    affected_service_ids: List[str] = []
    detection_source: str
    detected_at: datetime
    mitigated_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    summary: Optional[str] = None


class IncidentEventSchema(BaseModel):
    id: str
    incident_id: str
    event_type: str
    description: str
    payload: Optional[Dict[str, Any]] = None
    created_at: datetime


class IncidentDetail(IncidentBase):
    events: List[IncidentEventSchema] = []
    evidence: List[EvidenceSchema] = []
    hypotheses: List[HypothesisSchema] = []
    remediations: List[RemediationProposalSchema] = []


# Fault Injection Schemas
class FaultInjectRequest(BaseModel):
    fault_type: str = Field(..., description="db_pool_exhaustion, cpu_saturation, memory_pressure, downstream_latency, downstream_failure, queue_backlog, bad_deployment")
    target_service_id: str
    intensity: float = Field(default=0.8, ge=0.1, le=1.0)
    duration_seconds: int = Field(default=180, ge=10, le=1200)
    parameters: Dict[str, Any] = {}


class FaultInjectionResponse(BaseModel):
    id: str
    fault_type: str
    target_service_id: str
    intensity: float
    status: str
    expected_root_cause: str
    started_at: datetime
    ended_at: Optional[datetime] = None


# Model Intelligence Schemas
class AnomalyDetectionResult(BaseModel):
    service_id: str
    timestamp: str
    is_anomaly: bool
    anomaly_score: float
    threshold: float
    abnormal_features: List[Dict[str, Any]]
    model_version: str


class ClassificationResult(BaseModel):
    service_id: str
    predicted_class: str
    confidence: float
    class_probabilities: Dict[str, float]
    model_version: str


class ModelMetricsResponse(BaseModel):
    isolation_forest: Dict[str, Any]
    lightgbm: Dict[str, Any]
    baseline_random_forest: Dict[str, Any]
    feature_importance: List[Dict[str, Any]]
    confusion_matrix: Dict[str, Any]


# Evaluation Schemas
class EvaluationRunRequest(BaseModel):
    benchmark_name: str = "standard_resilience_suite"
    cases_count: int = Field(default=25, ge=5, le=100)


class EvaluationCaseSchema(BaseModel):
    scenario_name: str
    ground_truth_cause: str
    predicted_cause: str
    is_top1_match: bool
    is_top3_match: bool
    evidence_count: int
    passed: bool
    failure_reason: Optional[str] = None


class EvaluationRunResponse(BaseModel):
    id: str
    benchmark_name: str
    total_cases: int
    top1_accuracy: float
    top3_accuracy: float
    evidence_precision: float
    avg_latency_ms: float
    avg_tokens_used: float
    executed_at: datetime
    cases: List[EvaluationCaseSchema] = []
