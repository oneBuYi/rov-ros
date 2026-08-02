#!/usr/bin/env python3
import asyncio
import base64
import logging
import os
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from ament_index_python.packages import get_package_share_directory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles

from .rosbridge import RosbridgeClient
from .routes import router
from .telemetry import store, ws_endpoint

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gcs_backend")

# Global rosbridge client reference
_rosbridge: Optional[RosbridgeClient] = None
_broadcast_task: Optional[asyncio.Task] = None
_joystick_task: Optional[asyncio.Task] = None
_reconnect_task: Optional[asyncio.Task] = None


def get_rosbridge() -> Optional[RosbridgeClient]:
    return _rosbridge


async def _subscribe_all(rb: RosbridgeClient) -> None:
    """Subscribe to all telemetry and camera topics."""
    await rb.subscribe(
        "/mavros/global_position/rel_alt",
        "std_msgs/msg/Float64",
        on_rel_alt,
    )
    await rb.subscribe(
        "/mavros/global_position/global",
        "sensor_msgs/msg/NavSatFix",
        on_global_position,
    )
    await rb.subscribe(
        "/mavros/global_position/compass_hdg",
        "std_msgs/msg/Float64",
        on_compass_hdg,
    )
    await rb.subscribe(
        "/rov/depth_ctrl/pid_output",
        "std_msgs/msg/Float32",
        on_vertical_pwm,
    )
    await rb.subscribe(
        "/rov/depth_ctrl/status_hold",
        "std_msgs/msg/Bool",
        on_depth_hold_status,
    )
    await rb.subscribe(
        "/rov/heading_ctrl/pid_output",
        "std_msgs/msg/Float32",
        on_yaw_pwm,
    )
    await rb.subscribe(
        "/rov/heading_ctrl/status_hold",
        "std_msgs/msg/Bool",
        on_heading_hold_status,
    )
    await rb.subscribe(
        "/mavros/state",
        "mavros_msgs/msg/State",
        on_mavros_state,
    )
    await rb.subscribe(
        "/rov/camera/image_raw/compressed",
        "sensor_msgs/msg/CompressedImage",
        on_camera_image,
    )
    # Grid topics
    await rb.subscribe(
        "/rov/grid/rows",
        "std_msgs/msg/Int32",
        on_grid_rows,
    )
    await rb.subscribe(
        "/rov/grid/cols",
        "std_msgs/msg/Int32",
        on_grid_cols,
    )
    await rb.subscribe(
        "/rov/grid/current_row",
        "std_msgs/msg/Int32",
        on_grid_current_row,
    )
    await rb.subscribe(
        "/rov/grid/current_col",
        "std_msgs/msg/Int32",
        on_grid_current_col,
    )
    await rb.subscribe(
        "/rov/grid/target_row",
        "std_msgs/msg/Int32",
        on_grid_target_row,
    )
    await rb.subscribe(
        "/rov/grid/target_col",
        "std_msgs/msg/Int32",
        on_grid_target_col,
    )
    await rb.subscribe(
        "/rov/grid/in_target",
        "std_msgs/msg/Bool",
        on_grid_in_target,
    )
    await rb.subscribe(
        "/rov/grid/target_dist",
        "std_msgs/msg/Float64",
        on_grid_target_dist,
    )
    await rb.subscribe(
        "/rov/grid/target_depth_err",
        "std_msgs/msg/Float64",
        on_grid_target_depth_err,
    )
    # Depth PID gains
    await rb.subscribe(
        "/rov/depth_ctrl/pid_kp",
        "std_msgs/msg/Float32",
        on_depth_kp,
    )
    await rb.subscribe(
        "/rov/depth_ctrl/pid_ki",
        "std_msgs/msg/Float32",
        on_depth_ki,
    )
    await rb.subscribe(
        "/rov/depth_ctrl/pid_kd",
        "std_msgs/msg/Float32",
        on_depth_kd,
    )
    # Heading PID gains
    await rb.subscribe(
        "/rov/heading_ctrl/pid_kp",
        "std_msgs/msg/Float32",
        on_heading_kp,
    )
    await rb.subscribe(
        "/rov/heading_ctrl/pid_ki",
        "std_msgs/msg/Float32",
        on_heading_ki,
    )
    await rb.subscribe(
        "/rov/heading_ctrl/pid_kd",
        "std_msgs/msg/Float32",
        on_heading_kd,
    )


# ----- rosbridge topic callbacks -----

def on_rel_alt(msg: dict):
    """/mavros/global_position/rel_alt -> depth (negated)."""
    alt = msg.get("data", 0.0)
    depth = round(-alt, 2)
    store.update(depth=depth)


def on_global_position(msg: dict):
    """/mavros/global_position/global -> lat, lon."""
    store.update(
        lat=msg.get("latitude", 0.0),
        lon=msg.get("longitude", 0.0),
    )


def on_compass_hdg(msg: dict):
    """/mavros/global_position/compass_hdg -> yaw."""
    store.update(yaw=round(msg.get("data", 0.0), 2))


def on_vertical_pwm(msg: dict):
    """/rov/depth_ctrl/pid_output -> PID output."""
    store.update(vertical_pwm=round(msg.get("data", 0.0), 2))


def on_yaw_pwm(msg: dict):
    """/rov/heading_ctrl/pid_output -> PID output."""
    store.update(yaw_pwm=round(msg.get("data", 0.0), 2))


def on_depth_hold_status(msg: dict):
    """/rov/depth_ctrl/status_hold -> depth hold state."""
    store.update(depth_hold_enabled=bool(msg.get("data", False)))


def on_heading_hold_status(msg: dict):
    """/rov/heading_ctrl/status_hold -> heading hold state."""
    store.update(heading_hold_enabled=bool(msg.get("data", False)))


def on_grid_rows(msg: dict):
    """/rov/grid/rows -> grid total rows."""
    store.update(grid_rows=msg.get("data", 0))


def on_grid_cols(msg: dict):
    """/rov/grid/cols -> grid total cols."""
    store.update(grid_cols=msg.get("data", 0))


def on_grid_current_row(msg: dict):
    """/rov/grid/current_row -> ROV current cell row."""
    row = msg.get("data", -1)
    store.update(grid_current_row=row)
    _update_current_grid_label()


def on_grid_current_col(msg: dict):
    """/rov/grid/current_col -> ROV current cell col."""
    col = msg.get("data", -1)
    store.update(grid_current_col=col)
    _update_current_grid_label()


def on_grid_target_row(msg: dict):
    """/rov/grid/target_row -> target cell row."""
    row = msg.get("data", -1)
    store.update(grid_target_row=row)
    _update_target_grid_label()


def on_grid_target_col(msg: dict):
    """/rov/grid/target_col -> target cell col."""
    col = msg.get("data", -1)
    store.update(grid_target_col=col)
    _update_target_grid_label()


def on_grid_in_target(msg: dict):
    """/rov/grid/in_target -> grid reached status."""
    store.update(grid_reached=bool(msg.get("data", False)))


def on_grid_target_dist(msg: dict):
    """/rov/grid/target_dist -> horizontal distance to target (m)."""
    store.update(target_dist=round(msg.get("data", 0.0), 3))


def on_grid_target_depth_err(msg: dict):
    """/rov/grid/target_depth_err -> depth error to target (m)."""
    store.update(target_depth_err=round(msg.get("data", 0.0), 3))


# ----- PID gain callbacks -----

def on_depth_kp(msg: dict):
    """Store depth kp gain."""
    store.update(depth_kp=round(msg.get("data", 0.0), 1))


def on_depth_ki(msg: dict):
    """Store depth ki gain."""
    store.update(depth_ki=round(msg.get("data", 0.0), 1))


def on_depth_kd(msg: dict):
    """Store depth kd gain."""
    store.update(depth_kd=round(msg.get("data", 0.0), 1))


def on_heading_kp(msg: dict):
    """Store heading kp gain."""
    store.update(heading_kp=round(msg.get("data", 0.0), 1))


def on_heading_ki(msg: dict):
    """Store heading ki gain."""
    store.update(heading_ki=round(msg.get("data", 0.0), 1))


def on_heading_kd(msg: dict):
    """Store heading kd gain."""
    store.update(heading_kd=round(msg.get("data", 0.0), 1))


def _update_current_grid_label():
    """Derive current_grid string label from current row/col."""
    snap = store.snapshot()
    if snap.grid_current_row >= 0 and snap.grid_current_col >= 0:
        store.update(
            current_grid=f"R{snap.grid_current_row}C{snap.grid_current_col}"
        )
    else:
        store.update(current_grid="")


def _update_target_grid_label():
    """Derive target_grid string label from target row/col."""
    snap = store.snapshot()
    if snap.grid_target_row >= 0 and snap.grid_target_col >= 0:
        store.update(
            target_grid=f"R{snap.grid_target_row}C{snap.grid_target_col}"
        )
    else:
        store.update(target_grid="")


def on_mavros_state(msg: dict):
    """/mavros/state -> armed status."""
    store.update(armed=bool(msg.get("armed", False)))


def on_camera_image(msg: dict):
    """/rov/camera/image_raw/compressed -> store JPEG bytes directly."""
    try:
        data_b64 = msg.get("data", "")
        if not data_b64:
            return

        jpeg = base64.b64decode(data_b64)
        store.latest_frame = jpeg
        store.frame_event.set()
    except Exception:
        logger.exception("Failed to process camera image")


# ----- joystick publisher -----

async def joystick_publisher():
    """Publish joystick data from queue to ROS via rosbridge.

    Handles timeout protection: if no data for 500ms, send zeros.
    Tracks motor gain level and light state from button bit transitions.
    """
    last_time = time.time()
    prev_buttons = 0
    while True:
        try:
            # Wait up to 500ms for next joystick frame
            data = await asyncio.wait_for(
                store.joystick_queue.get(), timeout=0.5
            )
            last_time = time.time()
        except asyncio.TimeoutError:
            data = None

        rb = get_rosbridge()
        if not rb or not rb.connected:
            continue

        now = time.time()
        if data is None or now - last_time > 0.5:
            # Timeout: send zero commands to stop ROV
            msg = {"x": 0, "y": 0, "z": 0, "r": 0, "buttons": 0}
        else:
            buttons = data.get("buttons", [])
            # mavros_msgs/ManualControl buttons is uint16 bitmask.
            # Frontend sends an array of 0/1; pack into bitmask.
            btn_list = [int(b) for b in (buttons if isinstance(buttons, list) else [])]
            btn_mask = 0
            for i, b in enumerate(btn_list):
                if b:
                    btn_mask |= 1 << i
            msg = {
                "x": int(data.get("x", 0)),
                "y": int(data.get("y", 0)),
                "z": int(data.get("z", 0)),
                "r": int(data.get("r", 0)),
                "buttons": btn_mask,
            }

        try:
            await rb.publish(
                topic="/rov/joystick_ctrl/cmd",
                msg_type="mavros_msgs/ManualControl",
                msg=msg,
            )
        except Exception as e:
            logger.error(f"Failed to publish joystick: {e}")

        # Track motor gain and light state from button bit rising edges
        btn = msg["buttons"]
        rising = btn & ~prev_buttons  # 0→1 transitions this frame
        prev_buttons = btn

        snap = store.snapshot()
        if rising & (1 << 11):  # gain +25%
            store.update(gain_level=min(snap.gain_level + 25, 100))
        if rising & (1 << 12):  # gain -25%
            store.update(gain_level=max(snap.gain_level - 25, 25))
        if rising & (1 << 13):  # light off
            store.update(light_on=False)
        if rising & (1 << 14):  # light on
            store.update(light_on=True)


# ----- lifecycle -----

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rosbridge, _broadcast_task, _joystick_task, _reconnect_task

    # Startup
    logger.info("Starting GCS backend...")
    _rosbridge = RosbridgeClient("ws://localhost:9090")
    _rosbridge._on_disconnect = lambda: store.update(ros_connected=False)

    # Connect to rosbridge with retry
    retry_count = 0
    while True:
        try:
            await _rosbridge.connect(retry=False)
            break
        except Exception:
            retry_count += 1
            logger.warning(
                f"rosbridge not available, retry {retry_count}..."
            )
            await asyncio.sleep(2.0)

    # Wait for MAVROS publishers to come online before subscribing.
    # rosbridge determines subscriber QoS based on existing publishers at
    # subscription time. MAVROS uses BEST_EFFORT reliability; if we subscribe
    # before MAVROS starts publishing, rosbridge defaults to RELIABLE and
    # message delivery fails due to ROS2 QoS incompatibility.
    logger.info("Waiting for MAVROS publishers to come online...")
    await asyncio.sleep(5.0)

    # Subscribe to telemetry topics (ROS2 type names for correctness)
    await _subscribe_all(_rosbridge)

    store.update(ros_connected=True)
    logger.info("All telemetry subscriptions active")

    # Start reconnection watchdog
    async def reconnect_watchdog():
        while True:
            await asyncio.sleep(3.0)
            rb = get_rosbridge()
            if rb and not rb.connected:
                logger.warning("rosbridge disconnected, attempting reconnect...")
                try:
                    await rb.connect(retry=False)
                    await _subscribe_all(rb)
                    store.update(ros_connected=True)
                    logger.info("Reconnected to rosbridge")
                except Exception:
                    logger.debug("rosbridge reconnection failed, will retry")

    _reconnect_task = asyncio.create_task(reconnect_watchdog())

    # Start broadcast and joystick loops
    _broadcast_task = asyncio.create_task(store.run_broadcast_loop(0.1))
    _joystick_task = asyncio.create_task(joystick_publisher())

    yield  # <-- app runs here

    # Shutdown
    logger.info("Shutting down GCS backend...")
    store.update(ros_connected=False)

    for task in [_broadcast_task, _joystick_task, _reconnect_task]:
        if task:
            task.cancel()

    if _rosbridge:
        await _rosbridge.disconnect()

    logger.info("GCS backend stopped")


app = FastAPI(
    title="ROV GCS Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS: allow browser from any origin (for development convenience)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
app.add_api_websocket_route("/ws", ws_endpoint)


@app.get("/api/video/snapshot")
async def video_snapshot():
    """Return the latest camera frame as a single JPEG image."""
    from fastapi.responses import Response

    if store.latest_frame is None:
        return Response(status_code=204)

    return Response(content=store.latest_frame, media_type="image/jpeg")


@app.get("/api/video/stream")
async def video_stream():
    """MJPEG video stream of /rov/camera/image_raw."""

    async def generate():
        while True:
            # Wait for next frame; timeout keeps loop alive even if
            # camera temporarily stops publishing
            try:
                await asyncio.wait_for(store.frame_event.wait(), timeout=1.0)
            except asyncio.TimeoutError:
                continue
            store.frame_event.clear()
            frame = store.latest_frame
            if frame is not None:
                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n"
                )

    return StreamingResponse(
        generate(),
        media_type="multipart/x-mixed-replace; boundary=frame",
    )

# Mount frontend static files
_frontend_dist = os.path.join(
    get_package_share_directory("rov_gcs"), "frontend", "dist"
)
if os.path.isdir(_frontend_dist):
    app.mount(
        "/", StaticFiles(directory=_frontend_dist, html=True, follow_symlink=True), name="static"
    )
    logger.info(f"Serving frontend from {_frontend_dist}")


# Path to SSL certs (relative to this file, works in dev and production)
_CERTS_DIR = os.path.join(os.path.dirname(__file__), "certs")
_CERT_FILE = os.path.join(_CERTS_DIR, "cert.pem")
_KEY_FILE = os.path.join(_CERTS_DIR, "key.pem")


def main():
    """CLI entry point."""
    kwargs: dict = dict(
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )

    if os.path.isfile(_CERT_FILE) and os.path.isfile(_KEY_FILE):
        kwargs["ssl_certfile"] = _CERT_FILE
        kwargs["ssl_keyfile"] = _KEY_FILE
        logger.info(f"HTTPS enabled, cert={_CERT_FILE}")
    else:
        logger.warning(f"SSL certs not found at {_CERTS_DIR}, running HTTP only")

    uvicorn.run("rov_gcs.backend.main:app", **kwargs)


if __name__ == "__main__":
    main()
