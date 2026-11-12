from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any

from backend.app.schemas.schemas import FaultInjectRequest
from backend.app.core.security import verify_admin_authorization
from simulator.faults.fault_engine import fault_engine
from simulator.services.mesh import service_mesh

router = APIRouter(prefix="/faults", tags=["Fault Injection"])


@router.get("")
async def list_faults() -> Dict[str, Any]:
    active = fault_engine.get_active_faults()
    history = fault_engine.get_history(limit=20)
    return {
        "status": "success",
        "data": {
            "active_faults": [
                {
                    "id": f.id,
                    "fault_type": f.fault_type,
                    "target_service_id": f.target_service_id,
                    "intensity": f.intensity,
                    "duration_seconds": f.duration_seconds,
                    "expected_root_cause": f.expected_root_cause,
                    "expected_affected_services": f.expected_affected_services,
                    "elapsed_seconds": int(f.duration_seconds - (f.duration_seconds - (f.started_at - f.started_at))),
                }
                for f in active
            ],
            "history_count": len(history),
            "definitions": fault_engine.FAULT_DEFINITIONS,
        }
    }


@router.post("/inject")
async def inject_fault(
    req: FaultInjectRequest,
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    try:
        fault = fault_engine.inject_fault(
            fault_type=req.fault_type,
            target_service_id=req.target_service_id,
            intensity=req.intensity,
            duration_seconds=req.duration_seconds,
            parameters=req.parameters,
        )
        return {
            "status": "success",
            "message": f"Injected {fault.fault_type} on {fault.target_service_id}",
            "data": {
                "fault_id": fault.id,
                "fault_type": fault.fault_type,
                "target_service_id": fault.target_service_id,
                "intensity": fault.intensity,
                "duration_seconds": fault.duration_seconds,
                "expected_root_cause": fault.expected_root_cause,
            }
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{fault_id}/stop")
async def stop_fault(
    fault_id: str,
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    fault = fault_engine.stop_fault(fault_id)
    if not fault:
        raise HTTPException(status_code=404, detail=f"Active fault {fault_id} not found")
    return {"status": "success", "message": f"Fault {fault_id} stopped successfully"}


@router.post("/stop-all")
async def stop_all_faults(
    _auth: bool = Depends(verify_admin_authorization),
) -> Dict[str, Any]:
    stopped = fault_engine.stop_all_faults()
    return {"status": "success", "message": f"Stopped {len(stopped)} active faults"}
