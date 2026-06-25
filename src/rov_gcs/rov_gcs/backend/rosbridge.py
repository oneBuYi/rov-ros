import asyncio
import json
import logging
from typing import Callable, Optional

import websockets

logger = logging.getLogger(__name__)


class RosbridgeClient:
    def __init__(self, uri: str = "ws://localhost:9090"):
        self._uri = uri
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._callbacks: dict[str, Callable] = {}
        self._pending_services: dict[str, asyncio.Future] = {}
        self._call_id = 0
        self._connected = False
        self._recv_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    @property
    def connected(self) -> bool:
        return self._connected

    async def connect(self, retry: bool = True) -> None:
        """Connect to rosbridge server with optional retry."""
        backoff = 1.0
        while True:
            try:
                self._ws = await websockets.connect(
                    self._uri, ping_interval=20
                )
                self._connected = True
                self._recv_task = asyncio.create_task(self._recv_loop())
                logger.info(f"Connected to rosbridge at {self._uri}")
                return
            except (OSError, websockets.WebSocketException) as e:
                if not retry:
                    raise
                logger.warning(
                    f"rosbridge connection failed: {e}. "
                    f"Retrying in {backoff}s..."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 10.0)

    async def disconnect(self) -> None:
        """Close rosbridge connection."""
        self._connected = False
        if self._recv_task:
            self._recv_task.cancel()
            self._recv_task = None
        if self._ws:
            await self._ws.close()
            self._ws = None
        logger.info("Disconnected from rosbridge")

    async def subscribe(
        self, topic: str, msg_type: str, callback: Callable[[dict], None]
    ) -> str:
        """Subscribe to a ROS topic. Returns the topic (used as subscription ID).

        Note: rosbridge publish messages do NOT include the subscription ``id``
        field; they use ``topic`` to identify the source.  We therefore key
        callbacks by topic name rather than the client-generated sub_id.
        """
        async with self._lock:
            self._callbacks[topic] = callback
            msg = {
                "op": "subscribe",
                "id": topic,
                "topic": topic,
                "type": msg_type,
            }
            await self._ws.send(json.dumps(msg))
        logger.info(f"Subscribed to {topic} ({msg_type})")
        return topic

    async def unsubscribe(self, topic: str) -> None:
        """Cancel a subscription by topic name."""
        async with self._lock:
            self._callbacks.pop(topic, None)
            msg = {"op": "unsubscribe", "id": topic, "topic": topic}
            await self._ws.send(json.dumps(msg))

    async def publish(
        self, topic: str, msg_type: str, msg: dict
    ) -> None:
        """Publish a message to a ROS topic."""
        async with self._lock:
            payload = {
                "op": "publish",
                "topic": topic,
                "msg": msg,
            }
            await self._ws.send(json.dumps(payload))

    async def call_service(
        self, service: str, args: dict = None
    ) -> dict:
        """Call a ROS service and return the result."""
        self._call_id += 1
        call_id = f"call_{self._call_id}"
        future: asyncio.Future = asyncio.get_event_loop().create_future()
        self._pending_services[call_id] = future

        async with self._lock:
            msg = {
                "op": "call_service",
                "id": call_id,
                "service": service,
                "args": args or {},
            }
            await self._ws.send(json.dumps(msg))

        try:
            result = await asyncio.wait_for(future, timeout=5.0)
            return result
        except asyncio.TimeoutError:
            self._pending_services.pop(call_id, None)
            raise RuntimeError(
                f"Service call {service} timed out"
            )

    async def _recv_loop(self) -> None:
        """Main receive loop: dispatch incoming rosbridge messages."""
        try:
            async for raw in self._ws:
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue

                op = msg.get("op")
                if op == "publish":
                    # rosbridge publish messages use "topic" rather than "id"
                    # to identify the source subscription.
                    topic = msg.get("topic", "")
                    data = msg.get("msg", {})
                    cb = self._callbacks.get(topic)
                    if cb:
                        cb(data)

                elif op == "service_response":
                    call_id = msg.get("id", "")
                    future = self._pending_services.pop(call_id, None)
                    if future and not future.done():
                        if msg.get("result") is False:
                            error_msg = msg.get("values", "Unknown service error")
                            future.set_exception(RuntimeError(str(error_msg)))
                        else:
                            values = msg.get("values", {})
                            future.set_result(values)

                elif op == "status":
                    level = msg.get("level", "info")
                    text = msg.get("msg", "")
                    if level == "error":
                        logger.error(f"rosbridge error: {text}")
                    else:
                        logger.debug(f"rosbridge status: {text}")
        except websockets.ConnectionClosed:
            logger.warning("rosbridge connection closed")
        finally:
            self._connected = False
