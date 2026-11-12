import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from backend.app.database.session import async_session_factory
from backend.app.models.models import (
    IncidentModel,
    IncidentEventModel,
    EvidenceModel,
    HypothesisModel,
    RemediationProposalModel,
    ServiceModel,
)

logger = logging.getLogger("wingman.database.repository")


def _parse_dt(val: Any) -> Optional[datetime]:
    if not val:
        return None
    if isinstance(val, datetime):
        return val.astimezone(timezone.utc).replace(tzinfo=None) if val.tzinfo else val
    try:
        if isinstance(val, str):
            val_clean = val.replace("Z", "+00:00")
            dt = datetime.fromisoformat(val_clean)
            return dt.astimezone(timezone.utc).replace(tzinfo=None) if dt.tzinfo else dt
    except Exception:
        pass
    return datetime.utcnow()


def _to_iso(dt: Optional[datetime]) -> Optional[str]:
    if not dt:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc).isoformat()
    return dt.isoformat()


async def ensure_service_exists(session, service_id: str):
    """Ensure foreign key target in services table exists, safely handling concurrency."""
    stmt = select(ServiceModel).where(ServiceModel.id == service_id)
    res = await session.execute(stmt)
    if not res.scalar_one_or_none():
        try:
            async with session.begin_nested():
                new_svc = ServiceModel(
                    id=service_id,
                    name=service_id.replace("-", " ").title(),
                    description=f"Automated registration for {service_id}",
                    status="healthy",
                    dependencies=[],
                )
                session.add(new_svc)
                await session.flush()
        except Exception:
            # Another concurrent transaction inserted the service; continue safely
            pass


async def save_incident_to_db(incident_data: Dict[str, Any]) -> None:
    """Persist or update an incident and its nested collections to the database."""
    inc_id = incident_data.get("id")
    if not inc_id:
        return

    try:
        async with async_session_factory() as session:
            async with session.begin():
                # Ensure primary service foreign key exists
                primary_svc = incident_data.get("primary_service_id", "order-service")
                await ensure_service_exists(session, primary_svc)

                # Fetch or create IncidentModel
                stmt = (
                    select(IncidentModel)
                    .where(IncidentModel.id == inc_id)
                    .options(
                        selectinload(IncidentModel.events),
                        selectinload(IncidentModel.evidence),
                        selectinload(IncidentModel.hypotheses),
                        selectinload(IncidentModel.remediations),
                    )
                )
                res = await session.execute(stmt)
                incident_model = res.scalar_one_or_none()

                if not incident_model:
                    incident_model = IncidentModel(
                        id=inc_id,
                        title=incident_data.get("title", f"Incident on {primary_svc}"),
                        severity=incident_data.get("severity", "P2_HIGH"),
                        status=incident_data.get("status", "DETECTED"),
                        primary_service_id=primary_svc,
                        affected_service_ids=incident_data.get("affected_service_ids", [primary_svc]),
                        detection_source=incident_data.get("detection_source", "ISOLATION_FOREST"),
                        detected_at=_parse_dt(incident_data.get("detected_at")) or datetime.utcnow(),
                        mitigated_at=_parse_dt(incident_data.get("mitigated_at")),
                        resolved_at=_parse_dt(incident_data.get("resolved_at")),
                        summary=incident_data.get("summary", ""),
                    )
                    session.add(incident_model)
                else:
                    incident_model.title = incident_data.get("title", incident_model.title)
                    incident_model.severity = incident_data.get("severity", incident_model.severity)
                    incident_model.status = incident_data.get("status", incident_model.status)
                    incident_model.affected_service_ids = incident_data.get("affected_service_ids", incident_model.affected_service_ids)
                    incident_model.mitigated_at = _parse_dt(incident_data.get("mitigated_at"))
                    incident_model.resolved_at = _parse_dt(incident_data.get("resolved_at"))
                    incident_model.summary = incident_data.get("summary", incident_model.summary)

                # Persist timeline events
                existing_event_ids = {e.id for e in incident_model.events}
                for ev in incident_data.get("timeline", []):
                    ev_id = ev.get("id")
                    if ev_id and ev_id not in existing_event_ids:
                        session.add(
                            IncidentEventModel(
                                id=ev_id,
                                incident_id=inc_id,
                                event_type=ev.get("event_type", "INFO"),
                                description=ev.get("description", ""),
                                payload=ev.get("payload"),
                                created_at=_parse_dt(ev.get("created_at")) or datetime.utcnow(),
                            )
                        )

                # Persist evidence
                existing_ev_ids = {e.id for e in incident_model.evidence}
                for ev in incident_data.get("evidence", []):
                    ev_id = ev.get("id")
                    if ev_id and ev_id not in existing_ev_ids:
                        ev_svc = ev.get("service_id", primary_svc)
                        await ensure_service_exists(session, ev_svc)
                        session.add(
                            EvidenceModel(
                                id=ev_id,
                                incident_id=inc_id,
                                evidence_type=ev.get("evidence_type", "METRIC_SPIKE"),
                                service_id=ev_svc,
                                headline=ev.get("headline", ""),
                                details=ev.get("details", {}),
                                confidence_score=float(ev.get("confidence_score", 1.0)),
                                timestamp=_parse_dt(ev.get("timestamp")) or datetime.utcnow(),
                            )
                        )

                # Persist hypotheses
                existing_hyp_ids = {h.id for h in incident_model.hypotheses}
                for hyp in incident_data.get("hypotheses", []):
                    hyp_id = hyp.get("id")
                    if hyp_id and hyp_id not in existing_hyp_ids:
                        session.add(
                            HypothesisModel(
                                id=hyp_id,
                                incident_id=inc_id,
                                rank=int(hyp.get("rank", 1)),
                                root_cause=hyp.get("root_cause", ""),
                                confidence_score=float(hyp.get("confidence_score", 0.9)),
                                explanation=hyp.get("explanation", ""),
                                supporting_evidence_ids=hyp.get("supporting_evidence_ids", []),
                                contradictory_evidence_ids=hyp.get("contradictory_evidence_ids", []),
                                recommended_remediation=hyp.get("recommended_remediation", "RESTART_SERVICE"),
                                status=hyp.get("status", "PROPOSED"),
                                created_at=datetime.utcnow(),
                            )
                        )

                # Persist remediation proposal
                prop = incident_data.get("remediation_proposal")
                if prop and prop.get("id"):
                    prop_id = prop.get("id")
                    target_svc = prop.get("target_service_id", primary_svc)
                    await ensure_service_exists(session, target_svc)
                    existing_rem = next((r for r in incident_model.remediations if r.id == prop_id), None)
                    if not existing_rem:
                        session.add(
                            RemediationProposalModel(
                                id=prop_id,
                                incident_id=inc_id,
                                action_type=prop.get("action_type", "RESTART_SERVICE"),
                                target_service_id=target_svc,
                                parameters=prop.get("parameters", {}),
                                justification=prop.get("justification", ""),
                                risk_assessment=prop.get("risk_assessment", "LOW"),
                                status=prop.get("status", "PENDING_APPROVAL"),
                                created_at=_parse_dt(prop.get("created_at")) or datetime.utcnow(),
                            )
                        )
                    else:
                        existing_rem.status = prop.get("status", existing_rem.status)
                        existing_rem.action_type = prop.get("action_type", existing_rem.action_type)
                        existing_rem.justification = prop.get("justification", existing_rem.justification)
    except Exception as e:
        logger.error(f"Error persisting incident {inc_id} to database: {e}")


async def delete_incident_from_db(incident_id: str) -> bool:
    """Delete an incident and all its cascade children from the database."""
    try:
        async with async_session_factory() as session:
            async with session.begin():
                stmt = select(IncidentModel).where(IncidentModel.id == incident_id)
                res = await session.execute(stmt)
                incident_model = res.scalar_one_or_none()
                if incident_model:
                    await session.delete(incident_model)
                    return True
                return False
    except Exception as e:
        logger.error(f"Error deleting incident {incident_id} from database: {e}")
        return False


def _model_to_dict(m: IncidentModel) -> Dict[str, Any]:
    return {
        "id": m.id,
        "title": m.title,
        "severity": m.severity,
        "status": m.status,
        "primary_service_id": m.primary_service_id,
        "affected_service_ids": m.affected_service_ids or [m.primary_service_id],
        "detection_source": m.detection_source,
        "detected_at": _to_iso(m.detected_at),
        "mitigated_at": _to_iso(m.mitigated_at),
        "resolved_at": _to_iso(m.resolved_at),
        "summary": m.summary or "",
        "timeline": [
            {
                "id": ev.id,
                "event_type": ev.event_type,
                "description": ev.description,
                "payload": ev.payload,
                "created_at": _to_iso(ev.created_at),
            }
            for ev in m.events
        ],
        "evidence": [
            {
                "id": e.id,
                "evidence_type": e.evidence_type,
                "service_id": e.service_id,
                "headline": e.headline,
                "details": e.details or {},
                "confidence_score": e.confidence_score,
                "timestamp": _to_iso(e.timestamp),
            }
            for e in m.evidence
        ],
        "hypotheses": [
            {
                "id": h.id,
                "rank": h.rank,
                "root_cause": h.root_cause,
                "confidence_score": h.confidence_score,
                "explanation": h.explanation,
                "supporting_evidence_ids": h.supporting_evidence_ids or [],
                "contradictory_evidence_ids": h.contradictory_evidence_ids or [],
                "recommended_remediation": h.recommended_remediation,
                "status": h.status,
            }
            for h in m.hypotheses
        ],
        "remediation_proposal": (
            {
                "id": m.remediations[0].id,
                "action_type": m.remediations[0].action_type,
                "target_service_id": m.remediations[0].target_service_id,
                "parameters": m.remediations[0].parameters or {},
                "justification": m.remediations[0].justification,
                "risk_assessment": m.remediations[0].risk_assessment,
                "status": m.remediations[0].status,
                "created_at": _to_iso(m.remediations[0].created_at),
            }
            if m.remediations
            else None
        ),
    }


async def get_incident_from_db(incident_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve single incident by ID from the database."""
    try:
        async with async_session_factory() as session:
            stmt = (
                select(IncidentModel)
                .where(IncidentModel.id == incident_id)
                .options(
                    selectinload(IncidentModel.events),
                    selectinload(IncidentModel.evidence),
                    selectinload(IncidentModel.hypotheses),
                    selectinload(IncidentModel.remediations),
                )
            )
            res = await session.execute(stmt)
            model = res.scalar_one_or_none()
            if model:
                return _model_to_dict(model)
            return None
    except Exception as e:
        logger.error(f"Error fetching incident {incident_id} from database: {e}")
        return None


async def load_incidents_from_db() -> List[Dict[str, Any]]:
    """Load all persisted incidents with timeline, evidence, and hypotheses."""
    results = []
    try:
        async with async_session_factory() as session:
            stmt = select(IncidentModel).options(
                selectinload(IncidentModel.events),
                selectinload(IncidentModel.evidence),
                selectinload(IncidentModel.hypotheses),
                selectinload(IncidentModel.remediations),
            )
            res = await session.execute(stmt)
            models = res.scalars().all()
            for m in models:
                results.append(_model_to_dict(m))
    except Exception as e:
        logger.error(f"Error loading incidents from database: {e}")
    return results
