from fastapi import APIRouter
from typing import Dict, Any
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from agent.tools.gemini_service import gemini_service
from simulator.services.mesh import service_mesh

router = APIRouter(prefix="/settings", tags=["Settings"])


class TrafficConfig(BaseModel):
    rps: float = Field(default=10.0, ge=1.0, le=100.0)


@router.get("/integrations")
async def get_integration_settings() -> Dict[str, Any]:
    # Strictly never expose actual API key values
    key_configured = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 5)
    masked_key = f"{settings.GEMINI_API_KEY[:4]}...{settings.GEMINI_API_KEY[-4:]}" if key_configured else "Not configured"

    return {
        "status": "success",
        "data": {
            "gemini": {
                "configured": key_configured,
                "model_identifier": settings.GEMINI_MODEL,
                "api_key_status": "Active (Masked)" if key_configured else "Missing in .env",
                "masked_key": masked_key,
                "provider": "Google Gen AI SDK (google-genai)",
            },
            "observability": {
                "prometheus_status": "Ready",
                "prometheus_url": settings.PROMETHEUS_URL,
                "loki_url": settings.LOKI_URL,
                "tempo_url": settings.TEMPO_URL,
                "otel_endpoint": settings.OTEL_EXPORTER_OTLP_ENDPOINT,
            },
            "database": {
                "database_url": settings.DATABASE_URL.split("@")[-1] if "@" in settings.DATABASE_URL else settings.DATABASE_URL,
                "status": "Connected",
            },
            "safety": {
                "human_approval_required": True,
                "allowed_actions": ["RESTART_SERVICE", "RESET_CONNECTION_POOL", "ROLLBACK_DEPLOYMENT", "THROTTLE_TRAFFIC", "DRAIN_QUEUE"],
                "arbitrary_execution_blocked": True,
            }
        }
    }


@router.get("/traffic")
async def get_traffic_status() -> Dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "running": service_mesh.is_running,
            "target_rps": service_mesh.target_rps,
        }
    }


@router.post("/traffic")
async def update_traffic(cfg: TrafficConfig) -> Dict[str, Any]:
    service_mesh.set_traffic_rps(cfg.rps)
    return {
        "status": "success",
        "message": f"Updated simulator target throughput to {cfg.rps} RPS",
        "data": {"target_rps": cfg.rps}
    }
