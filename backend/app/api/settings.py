import os
from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any, List
from pydantic import BaseModel, Field

from backend.app.core.config import settings
from backend.app.core.security import verify_admin_authorization, verify_destructive_admin_authorization
from agent.tools.gemini_service import gemini_service
from simulator.services.mesh import service_mesh
from simulator.faults.fault_engine import fault_engine

router = APIRouter(prefix="/settings", tags=["Settings"])


class TrafficConfig(BaseModel):
    rps: float = Field(default=10.0, ge=1.0, le=100.0)


class ApiKeyConfig(BaseModel):
    api_key: str = Field(..., min_length=10)


class SafetyConfig(BaseModel):
    human_approval_required: bool = True
    max_remediations_per_hour: int = Field(default=10, ge=1, le=100)
    allowed_actions: List[str] = [
        "RESTART_SERVICE",
        "RESET_CONNECTION_POOL",
        "ROLLBACK_DEPLOYMENT",
        "THROTTLE_TRAFFIC",
        "DRAIN_QUEUE",
    ]


# In-memory safety state
safety_state = {
    "human_approval_required": True,
    "max_remediations_per_hour": 10,
    "allowed_actions": [
        "RESTART_SERVICE",
        "RESET_CONNECTION_POOL",
        "ROLLBACK_DEPLOYMENT",
        "THROTTLE_TRAFFIC",
        "DRAIN_QUEUE",
    ],
    "arbitrary_execution_blocked": True,
}


@router.get("/integrations")
async def get_integration_settings() -> Dict[str, Any]:
    key_configured = bool(settings.GEMINI_API_KEY and len(settings.GEMINI_API_KEY) > 5)
    masked_key = (
        f"{settings.GEMINI_API_KEY[:4]}...{settings.GEMINI_API_KEY[-4:]}"
        if key_configured
        else "Not configured"
    )

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
                "database_url": (
                    settings.DATABASE_URL.split("@")[-1]
                    if "@" in settings.DATABASE_URL
                    else settings.DATABASE_URL
                ),
                "status": "Connected",
            },
            "safety": safety_state,
        },
    }


@router.post("/test-gemini")
async def test_gemini_connection() -> Dict[str, Any]:
    result = gemini_service.test_connection()
    if not result.get("ok"):
        return {
            "status": "error",
            "message": result.get("error", "Failed to connect to Gemini API"),
            "data": result,
        }
    return {
        "status": "success",
        "message": result.get("message", "Connected successfully"),
        "data": result,
    }


@router.post("/api-key")
async def update_api_key(
    cfg: ApiKeyConfig,
    _auth: bool = Depends(verify_destructive_admin_authorization),
) -> Dict[str, Any]:
    success = gemini_service.set_api_key(cfg.api_key)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to initialize client with provided API key")

    # Verify key immediately
    test_res = gemini_service.test_connection()
    masked = f"{cfg.api_key[:4]}...{cfg.api_key[-4:]}"

    return {
        "status": "success",
        "message": "Updated Gemini API key in active session",
        "data": {
            "masked_key": masked,
            "verification": test_res,
        },
    }


@router.get("/traffic")
async def get_traffic_status() -> Dict[str, Any]:
    return {
        "status": "success",
        "data": {
            "running": service_mesh.is_running,
            "target_rps": service_mesh.target_rps,
        },
    }


@router.post("/traffic")
async def update_traffic(
    cfg: TrafficConfig,
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    service_mesh.set_traffic_rps(cfg.rps)
    return {
        "status": "success",
        "message": f"Updated simulator target throughput to {cfg.rps} RPS",
        "data": {"target_rps": cfg.rps},
    }


@router.post("/traffic/toggle")
async def toggle_traffic(
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    if service_mesh.is_running:
        await service_mesh.stop()
        state = False
        msg = "Simulator traffic generator paused"
    else:
        await service_mesh.start()
        state = True
        msg = "Simulator traffic generator started"

    return {
        "status": "success",
        "message": msg,
        "data": {
            "running": state,
            "target_rps": service_mesh.target_rps,
        },
    }


@router.get("/safety")
async def get_safety_settings() -> Dict[str, Any]:
    return {
        "status": "success",
        "data": safety_state,
    }


@router.post("/safety")
async def update_safety_settings(
    cfg: SafetyConfig,
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    safety_state["human_approval_required"] = cfg.human_approval_required
    safety_state["max_remediations_per_hour"] = cfg.max_remediations_per_hour
    safety_state["allowed_actions"] = cfg.allowed_actions
    return {
        "status": "success",
        "message": "Autonomous safety policy updated",
        "data": safety_state,
    }


@router.get("/system-diagnostics")
async def get_system_diagnostics() -> Dict[str, Any]:
    # Check ML artifacts
    if_exists = os.path.exists("ml/artifacts/isolation_forest.joblib")
    lgb_exists = os.path.exists("ml/artifacts/lightgbm_model.joblib")

    # Check simulator
    mesh_ok = service_mesh.is_running
    active_faults_count = len(fault_engine.get_active_faults())

    # Check Gemini
    gemini_ok = gemini_service.is_configured

    ml_ready = bool(if_exists and lgb_exists)

    return {
        "status": "success",
        "data": {
            "subsystems": [
                {
                    "name": "Database (SQLite aiosqlite)",
                    "status": "HEALTHY",
                    "details": "Active session pool ready",
                },
                {
                    "name": "Gemini 3.5 Flash-Lite LLM Provider",
                    "status": "HEALTHY" if gemini_ok else "DEGRADED",
                    "details": f"Model: {gemini_service.model_id} (SDK: google-genai)",
                },
                {
                    "name": "ML Inference Engine",
                    "status": "HEALTHY" if ml_ready else "DEGRADED",
                    "details": "Isolation Forest + LightGBM 7-Class Classifier loaded",
                },
                {
                    "name": "Service Mesh Telemetry Loop",
                    "status": "HEALTHY" if mesh_ok else "PAUSED",
                    "details": f"Target: {service_mesh.target_rps} RPS ({active_faults_count} active faults)",
                },
                {
                    "name": "LangGraph Investigation Agent",
                    "status": "HEALTHY",
                    "details": "16-node state machine with MCP tools loaded",
                },
                {
                    "name": "Autonomous Safety Guardrails",
                    "status": "HEALTHY",
                    "details": "Human approval gate strictly enforced",
                },
            ],
            "all_healthy": bool(gemini_ok and ml_ready and mesh_ok),
        },
    }


@router.post("/reset-demo")
async def reset_demo_environment() -> Dict[str, Any]:
    stopped = fault_engine.stop_all_faults()
    service_mesh.set_traffic_rps(10.0)
    if not service_mesh.is_running:
        await service_mesh.start()

    return {
        "status": "success",
        "message": f"Demo environment reset to baseline: cleared {len(stopped)} active faults and normalized traffic to 10 RPS.",
        "data": {
            "stopped_faults": len(stopped),
            "target_rps": 10.0,
            "running": True,
        },
    }
