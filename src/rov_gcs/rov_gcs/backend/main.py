#!/usr/bin/env python3
import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from ament_index_python.packages import get_package_share_directory
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


def get_rosbridge() -> Optional[RosbridgeClient]:
    return _rosbridge


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
    """/rov/depth_ctrl/status -> depth hold state."""
    store.update(depth_hold_enabled=bool(msg.get("data", False)))


def on_heading_hold_status(msg: dict):
    """/rov/heading_ctrl/status -> heading hold state."""
    store.update(heading_hold_enabled=bool(msg.get("data", False)))


# ----- joystick publisher -----

async def joystick_publisher():
    """Publish joystick data from queue to ROS via rosbridge.

    Handles timeout protection: if no data for 500ms, send zeros.
    """
    last_time = time.time()
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
            msg = {"x": 0, "y": 0, "z": 0, "r": 0}
        else:
            msg = {
                "x": int(data.get("x", 0)),
                "y": int(data.get("y", 0)),
                "z": int(data.get("z", 0)),
                "r": int(data.get("r", 0)),
            }

        try:
            await rb.publish(
                topic="/rov/joystick/cmd",
                msg_type="mavros_msgs/ManualControl",
                msg=msg,
            )
        except Exception as e:
            logger.error(f"Failed to publish joystick: {e}")


# ----- lifecycle -----

@asynccontextmanager
async def lifespan(app: FastAPI):
    global _rosbridge, _broadcast_task, _joystick_task

    # Startup
    logger.info("Starting GCS backend...")
    _rosbridge = RosbridgeClient("ws://localhost:9090")

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
    await _rosbridge.subscribe(
        "/mavros/global_position/rel_alt",
        "std_msgs/msg/Float64",
        on_rel_alt,
    )
    await _rosbridge.subscribe(
        "/mavros/global_position/global",
        "sensor_msgs/msg/NavSatFix",
        on_global_position,
    )
    await _rosbridge.subscribe(
        "/mavros/global_position/compass_hdg",
        "std_msgs/msg/Float64",
        on_compass_hdg,
    )
    await _rosbridge.subscribe(
        "/rov/depth_ctrl/pid_output",
        "std_msgs/msg/Float32",
        on_vertical_pwm,
    )
    await _rosbridge.subscribe(
        "/rov/depth_ctrl/status",
        "std_msgs/msg/Bool",
        on_depth_hold_status,
    )
    await _rosbridge.subscribe(
        "/rov/heading_ctrl/pid_output",
        "std_msgs/msg/Float32",
        on_yaw_pwm,
    )
    await _rosbridge.subscribe(
        "/rov/heading_ctrl/status",
        "std_msgs/msg/Bool",
        on_heading_hold_status,
    )

    store.update(ros_connected=True)
    logger.info("All telemetry subscriptions active")

    # Start broadcast and joystick loops
    _broadcast_task = asyncio.create_task(store.run_broadcast_loop(0.1))
    _joystick_task = asyncio.create_task(joystick_publisher())

    yield  # <-- app runs here

    # Shutdown
    logger.info("Shutting down GCS backend...")
    store.update(ros_connected=False)

    for task in [_broadcast_task, _joystick_task]:
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

# Mount frontend static files
_frontend_dist = os.path.join(
    get_package_share_directory("rov_gcs"), "frontend", "dist"
)
if os.path.isdir(_frontend_dist):
    app.mount(
        "/", StaticFiles(directory=_frontend_dist, html=True), name="static"
    )
    logger.info(f"Serving frontend from {_frontend_dist}")


def main():
    """CLI entry point."""
    uvicorn.run(
        "rov_gcs.backend.main:app",
        host="0.0.0.0",
        port=8000,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()
