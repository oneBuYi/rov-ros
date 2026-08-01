import logging

from fastapi import APIRouter, HTTPException

from .models import (
    ApiResponse,
    SetDepthTargetRequest,
    SetHeadingTargetRequest,
    SetGridTargetRequest,
    SetPIDGainsRequest,
)
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


# ----- grid control -----


@router.post("/grid/set_target", response_model=ApiResponse)
async def set_grid_target(req: SetGridTargetRequest):
    """Set target grid cell via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/grid/set_grid_target",
            args={"row": req.row, "col": req.col},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            store.update(
                grid_target_row=req.row,
                grid_target_col=req.col,
                target_grid=f"R{req.row}C{req.col}",
            )
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


# ----- arm/disarm -----

@router.post("/arm", response_model=ApiResponse)
async def arm():
    """Arm the vehicle via MAVROS."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/mavros/cmd/arming",
            args={"value": True},
        )
        success = result.get("success", False)
        message = result.get("message", "Arm command sent")
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/disarm", response_model=ApiResponse)
async def disarm():
    """Disarm the vehicle via MAVROS."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/mavros/cmd/arming",
            args={"value": False},
        )
        success = result.get("success", False)
        message = result.get("message", "Disarm command sent")
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


# ----- PID gain control -----


@router.post("/depth/pid_gains", response_model=ApiResponse)
async def set_depth_pid_gains(req: SetPIDGainsRequest):
    """Set depth PID gains via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/depth_ctrl/set_pid_gains",
            args={"kp": req.kp, "ki": req.ki, "kd": req.kd},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            store.update(depth_kp=req.kp, depth_ki=req.ki, depth_kd=req.kd)
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/depth/pid_reset", response_model=ApiResponse)
async def reset_depth_pid_gains():
    """Reset depth PID gains to defaults."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/depth_ctrl/reset_pid_gains",
            args={},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/heading/pid_gains", response_model=ApiResponse)
async def set_heading_pid_gains(req: SetPIDGainsRequest):
    """Set heading PID gains via rosbridge service call."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/heading_ctrl/set_pid_gains",
            args={"kp": req.kp, "ki": req.ki, "kd": req.kd},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        if success:
            store.update(
                heading_kp=req.kp, heading_ki=req.ki, heading_kd=req.kd
            )
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))


@router.post("/heading/pid_reset", response_model=ApiResponse)
async def reset_heading_pid_gains():
    """Reset heading PID gains to defaults."""
    from .main import get_rosbridge

    rb = get_rosbridge()
    if not rb or not rb.connected:
        raise HTTPException(status_code=503, detail="ROS not connected")

    try:
        result = await rb.call_service(
            service="/rov/heading_ctrl/reset_pid_gains",
            args={},
        )
        success = result.get("success", False)
        message = result.get("message", "")
        return ApiResponse(success=success, message=message)
    except RuntimeError as e:
        raise HTTPException(status_code=504, detail=str(e))
