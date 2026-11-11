from datetime import datetime
from typing import Optional, List, Any
from sqlalchemy import (
    String,
    Text,
    Float,
    Integer,
    Boolean,
    DateTime,
    ForeignKey,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.database.session import Base


class ServiceModel(Base):
    __tablename__ = "services"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="healthy")  # healthy, degraded, critical
    dependencies: Mapped[List[str]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incidents: Mapped[List["IncidentModel"]] = relationship(
        "IncidentModel", back_populates="primary_service", foreign_keys="IncidentModel.primary_service_id"
    )
    deployments: Mapped[List["DeploymentEventModel"]] = relationship(
        "DeploymentEventModel", back_populates="service"
    )


class FaultInjectionModel(Base):
    __tablename__ = "fault_injections"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    fault_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_service_id: Mapped[str] = mapped_column(String(64), ForeignKey("services.id"), nullable=False)
    intensity: Mapped[float] = mapped_column(Float, default=1.0)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE")  # ACTIVE, STOPPED, EXPIRED
    expected_root_cause: Mapped[str] = mapped_column(String(255), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)


class DeploymentEventModel(Base):
    __tablename__ = "deployment_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    service_id: Mapped[str] = mapped_column(String(64), ForeignKey("services.id"), nullable=False)
    version: Mapped[str] = mapped_column(String(64), nullable=False)
    deployed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    is_canary: Mapped[bool] = mapped_column(Boolean, default=False)
    config_diff: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)

    service: Mapped["ServiceModel"] = relationship("ServiceModel", back_populates="deployments")


class IncidentModel(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[str] = mapped_column(String(32), default="P2_HIGH")  # P1_CRITICAL, P2_HIGH, P3_MEDIUM, P4_LOW
    status: Mapped[str] = mapped_column(String(32), default="DETECTED")   # DETECTED, INVESTIGATING, IDENTIFIED, MITIGATING, RESOLVED, CLOSED
    primary_service_id: Mapped[str] = mapped_column(String(64), ForeignKey("services.id"), nullable=False)
    affected_service_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    detection_source: Mapped[str] = mapped_column(String(64), default="ISOLATION_FOREST")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    mitigated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    fault_injection_id: Mapped[Optional[str]] = mapped_column(String(64), ForeignKey("fault_injections.id"), nullable=True)

    primary_service: Mapped["ServiceModel"] = relationship("ServiceModel", back_populates="incidents", foreign_keys=[primary_service_id])
    events: Mapped[List["IncidentEventModel"]] = relationship("IncidentEventModel", back_populates="incident", cascade="all, delete-orphan")
    evidence: Mapped[List["EvidenceModel"]] = relationship("EvidenceModel", back_populates="incident", cascade="all, delete-orphan")
    hypotheses: Mapped[List["HypothesisModel"]] = relationship("HypothesisModel", back_populates="incident", cascade="all, delete-orphan")
    investigations: Mapped[List["InvestigationModel"]] = relationship("InvestigationModel", back_populates="incident", cascade="all, delete-orphan")
    remediations: Mapped[List["RemediationProposalModel"]] = relationship("RemediationProposalModel", back_populates="incident", cascade="all, delete-orphan")


class IncidentEventModel(Base):
    __tablename__ = "incident_events"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    payload: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    incident: Mapped["IncidentModel"] = relationship("IncidentModel", back_populates="events")


class EvidenceModel(Base):
    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), nullable=False)
    evidence_type: Mapped[str] = mapped_column(String(32), nullable=False)  # METRIC_SPIKE, LOG_ERROR, TRACE_LATENCY, DEPLOYMENT_DIFF, RUNBOOK_MATCH
    service_id: Mapped[str] = mapped_column(String(64), ForeignKey("services.id"), nullable=False)
    headline: Mapped[str] = mapped_column(String(255), nullable=False)
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    confidence_score: Mapped[float] = mapped_column(Float, default=1.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    incident: Mapped["IncidentModel"] = relationship("IncidentModel", back_populates="evidence")


class HypothesisModel(Base):
    __tablename__ = "hypotheses"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), nullable=False)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)
    root_cause: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    explanation: Mapped[str] = mapped_column(Text, nullable=False)
    supporting_evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    contradictory_evidence_ids: Mapped[List[str]] = mapped_column(JSON, default=list)
    recommended_remediation: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="PROPOSED")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    incident: Mapped["IncidentModel"] = relationship("IncidentModel", back_populates="hypotheses")


class InvestigationModel(Base):
    __tablename__ = "investigations"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), nullable=False)
    graph_execution_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    state: Mapped[str] = mapped_column(String(32), default="RUNNING")  # RUNNING, AWAITING_APPROVAL, COMPLETED, FAILED
    current_node: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    incident: Mapped["IncidentModel"] = relationship("IncidentModel", back_populates="investigations")
    tool_executions: Mapped[List["ToolExecutionModel"]] = relationship("ToolExecutionModel", back_populates="investigation", cascade="all, delete-orphan")


class ToolExecutionModel(Base):
    __tablename__ = "tool_executions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    investigation_id: Mapped[str] = mapped_column(String(64), ForeignKey("investigations.id"), nullable=False)
    tool_name: Mapped[str] = mapped_column(String(64), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    result_summary: Mapped[str] = mapped_column(Text, nullable=False)
    execution_duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    investigation: Mapped["InvestigationModel"] = relationship("InvestigationModel", back_populates="tool_executions")


class RemediationProposalModel(Base):
    __tablename__ = "remediation_proposals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    incident_id: Mapped[str] = mapped_column(String(64), ForeignKey("incidents.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    target_service_id: Mapped[str] = mapped_column(String(64), ForeignKey("services.id"), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    risk_assessment: Mapped[str] = mapped_column(String(32), default="LOW")
    status: Mapped[str] = mapped_column(String(32), default="PENDING_APPROVAL")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    incident: Mapped["IncidentModel"] = relationship("IncidentModel", back_populates="remediations")
    approvals: Mapped[List["RemediationApprovalModel"]] = relationship("RemediationApprovalModel", back_populates="proposal", cascade="all, delete-orphan")


class RemediationApprovalModel(Base):
    __tablename__ = "remediation_approvals"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    proposal_id: Mapped[str] = mapped_column(String(64), ForeignKey("remediation_proposals.id"), nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)  # APPROVED, REJECTED
    operator_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    executed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    execution_output: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    verification_status: Mapped[str] = mapped_column(String(32), default="PENDING")

    proposal: Mapped["RemediationProposalModel"] = relationship("RemediationProposalModel", back_populates="approvals")


class ModelVersionModel(Base):
    __tablename__ = "model_versions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)  # IsolationForest, LightGBM
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    artifact_path: Mapped[str] = mapped_column(String(255), nullable=False)
    parameters: Mapped[dict] = mapped_column(JSON, default=dict)
    metrics: Mapped[dict] = mapped_column(JSON, default=dict)
    trained_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class EvaluationRunModel(Base):
    __tablename__ = "evaluation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    benchmark_name: Mapped[str] = mapped_column(String(128), nullable=False)
    total_cases: Mapped[int] = mapped_column(Integer, default=0)
    top1_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    top3_accuracy: Mapped[float] = mapped_column(Float, default=0.0)
    evidence_precision: Mapped[float] = mapped_column(Float, default=0.0)
    avg_latency_ms: Mapped[float] = mapped_column(Float, default=0.0)
    avg_tokens_used: Mapped[float] = mapped_column(Float, default=0.0)
    executed_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    cases: Mapped[List["EvaluationCaseModel"]] = relationship("EvaluationCaseModel", back_populates="run", cascade="all, delete-orphan")


class EvaluationCaseModel(Base):
    __tablename__ = "evaluation_cases"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), ForeignKey("evaluation_runs.id"), nullable=False)
    scenario_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ground_truth_cause: Mapped[str] = mapped_column(String(255), nullable=False)
    predicted_cause: Mapped[str] = mapped_column(String(255), nullable=False)
    is_top1_match: Mapped[bool] = mapped_column(Boolean, default=False)
    is_top3_match: Mapped[bool] = mapped_column(Boolean, default=False)
    evidence_count: Mapped[int] = mapped_column(Integer, default=0)
    passed: Mapped[bool] = mapped_column(Boolean, default=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    run: Mapped["EvaluationRunModel"] = relationship("EvaluationRunModel", back_populates="cases")
