import logging

from fastapi import APIRouter, HTTPException

from .models import ApiResponse, SetDepthTargetRequest, SetHeadingTargetRequest
from .telemetry import store

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api")


@router.get("/telemetry")
async def get_telemetry():
    """Return latest telemetry snapshot."""
    return store.snapshot()


# ----- depth control -----

@router.post("/depth/set_target", response_model=ApiResponse)
async def set_depth_target(req: SetDepthTargetRequest):
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
            store.update(target_depth=req.target, depth_hold_enabled=True)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/depth/hold", response_model=ApiResponse)
async def toggle_depth_hold():
    """Toggle depth hold via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/depth_ctrl/toggle_hold",
            args={},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        depth_hold_enabled = "enabled" in message.lower()
        store.update(depth_hold_enabled=depth_hold_enabled)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


# ----- heading control -----

@router.post("/heading/set_target", response_model=ApiResponse)
async def set_heading_target(req: SetHeadingTargetRequest):
    """Set target heading via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/heading_ctrl/set_target",
            args={"target": req.target},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            target_normalized = req.target % 360.0
            store.update(
                target_heading=round(target_normalized, 1),
                heading_hold_enabled=True,
            )
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/heading/hold", response_model=ApiResponse)
async def toggle_heading_hold():
    """Toggle heading hold via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/heading_ctrl/toggle_hold",
            args={},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        heading_hold_enabled = "enabled" in message.lower()
        store.update(heading_hold_enabled=heading_hold_enabled)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))
