from fastapi import APIRouter, Response, status
from sqlalchemy import text
from backend.app.database.session import engine
from agent.tools.gemini_service import gemini_service
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier
from simulator.services.mesh import service_mesh

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
@router.get("/live")
async def get_liveness():
    """Liveness probe: verifies that the FastAPI process is responsive."""
    return {
        "status": "healthy",
        "service": "wingman-ai-backend",
        "components": {
            "simulator": "running" if service_mesh.is_running else "ready",
            "anomaly_detector": "loaded" if anomaly_detector.model is not None else "ready",
            "incident_classifier": "loaded" if incident_classifier.model is not None else "ready",
            "gemini_api": "configured" if gemini_service.is_configured else "unconfigured",
            "gemini_model": gemini_service.model_id,
        }
    }


@router.get("/ready")
async def get_readiness(response: Response):
    """Readiness probe: validates database connectivity and model initialization."""
    db_ok = False
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
            db_ok = True
    except Exception:
        db_ok = False

    models_ok = anomaly_detector.model is not None or incident_classifier.model is not None
    is_ready = db_ok

    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ready" if is_ready else "not_ready",
        "database": "connected" if db_ok else "disconnected",
        "models_loaded": models_ok,
        "simulator_running": service_mesh.is_running,
    }
