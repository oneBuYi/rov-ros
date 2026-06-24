import logging

from fastapi import APIRouter, HTTPException

from .models import ApiResponse, SetTargetRequest
from .telemetry import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/telemetry")
async def get_telemetry():
    """Return latest telemetry snapshot."""
    return store.snapshot()


@router.post("/depth/set_target", response_model=ApiResponse)
async def set_target(req: SetTargetRequest):
    """Set target depth via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/depth_ctrl/set_target",
            args={"target": req.target},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            store.update(target_depth=req.target, hold_enabled=True)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/depth/hold", response_model=ApiResponse)
async def toggle_hold():
    """Toggle depth hold via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/depth_ctrl/hold",
            args={},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        # Infer hold state from message
        hold_enabled = "enabled" in message.lower()
        store.update(hold_enabled=hold_enabled)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))
