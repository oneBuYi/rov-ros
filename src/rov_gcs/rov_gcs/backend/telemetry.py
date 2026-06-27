import asyncio
import logging
from typing import Optional

from fastapi import WebSocket

from .models import Telemetry

logger = logging.getLogger(__name__)


class TelemetryStore:
    """Singleton cache for latest telemetry + active WebSocket clients."""

    def __init__(self):
        self._telemetry = Telemetry()
        self._lock = asyncio.Lock()
        self._clients: set[WebSocket] = set()
        self.joystick_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.latest_frame: bytes | None = None  # latest JPEG frame for MJPEG stream

    def update(self, **kwargs) -> None:
        """Update cached telemetry fields."""
        for key, value in kwargs.items():
            if hasattr(self._telemetry, key):
                setattr(self._telemetry, key, value)

    def snapshot(self) -> Telemetry:
        """Return a copy of current telemetry state."""
        return self._telemetry.model_copy()

    async def register_client(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)
        logger.info(
            f"WebSocket client connected, total: {len(self._clients)}"
        )

    async def remove_client(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info(
            f"WebSocket client disconnected, total: {len(self._clients)}"
        )

    async def broadcast(self) -> None:
        """Push current telemetry to all connected WebSocket clients."""
        dead: list[WebSocket] = []
        data = self.snapshot().model_dump()
        payload = {"type": "telemetry", "data": data}
        async with self._lock:
            clients = list(self._clients)
        for ws in clients:
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            await self.remove_client(ws)

    async def run_broadcast_loop(self, interval: float = 0.1) -> None:
        """Broadcast telemetry at fixed interval (default 100ms = 10Hz)."""
        while True:
            await asyncio.sleep(interval)
            await self.broadcast()


# Global singleton
store = TelemetryStore()


async def ws_endpoint(websocket: WebSocket):
    """Handle single WebSocket client connection.

    Receives joystick data from client, pushes telemetry via broadcast loop.
    """
    await websocket.accept()
    await store.register_client(websocket)
    try:
        while True:
            raw = await websocket.receive_json()
            if raw.get("type") == "joystick":
                data = raw.get("data", {})
                try:
                    store.joystick_queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass  # drop oldest if queue full
    except Exception:
        pass
    finally:
        await store.remove_client(websocket)
