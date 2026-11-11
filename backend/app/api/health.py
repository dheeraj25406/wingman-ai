from fastapi import APIRouter
from agent.tools.gemini_service import gemini_service
from ml.anomaly_detection.isolation_forest import anomaly_detector
from ml.classification.classifier import incident_classifier
from simulator.services.mesh import service_mesh

router = APIRouter(prefix="/health", tags=["Health"])


@router.get("")
async def get_health():
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
