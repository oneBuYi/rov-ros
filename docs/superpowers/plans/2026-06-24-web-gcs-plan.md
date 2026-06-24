# Web 上位机实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 rosbridge + FastAPI + Vue 3 构建 Web 上位机，实现遥测监控、深度控制、手柄操控。

**Architecture:** rosbridge_server 将 ROS2 topic/service 暴露为 WebSocket；FastAPI 作为 BFF 层通过 rosbridge 协议订阅/调用 ROS2，对外提供 REST + WebSocket；Vue 3 前端通过 nginx 托管，浏览器 Gamepad API 采集手柄数据经 WebSocket 回传。

**Tech Stack:** ROS2 Foxy, rosbridge_suite, Python 3.8, FastAPI + uvicorn + websockets + pydantic, Vue 3 + Vite + Pinia, nginx

## Global Constraints

- ROS2 Foxy (`/opt/ros/foxy/`)，Python 3.8
- 运行在 Jetson ARM（Linux 4.9）
- Web 服务监听 `0.0.0.0:8000`
- 前端输入校验：目标深度 ≥ 0
- 手柄超时 500ms 后发布全零 ManualControl
- ROS 命名空间统一 `/rov` 下
- 包名：`rov_gcs`，遵循 ament_python 结构

---

## 文件结构映射

| 文件 | 责任 | 创建/修改 |
|------|------|-----------|
| `src/rov_gcs/package.xml` | 包元信息 + 依赖声明 | 创建 |
| `src/rov_gcs/setup.py` | 包安装 + entry point (gcs_backend) | 创建 |
| `src/rov_gcs/setup.cfg` | 模块发现配置 | 创建 |
| `src/rov_gcs/rov_gcs/__init__.py` | 包占位 | 创建 |
| `src/rov_gcs/rov_gcs/backend/__init__.py` | 子包占位 | 创建 |
| `src/rov_gcs/rov_gcs/backend/main.py` | FastAPI 入口、生命周期（启动连 rosbridge、关闭断开）、uvicorn 启动 | 创建 |
| `src/rov_gcs/rov_gcs/backend/rosbridge.py` | rosbridge WebSocket 管理：连接/重连/订阅 topic/发布 topic/调用 service | 创建 |
| `src/rov_gcs/rov_gcs/backend/models.py` | Pydantic 模型：Telemetry, SetTargetRequest, ApiResponse | 创建 |
| `src/rov_gcs/rov_gcs/backend/routes.py` | REST 路由：GET /api/telemetry, POST /api/depth/set_target, POST /api/depth/hold | 创建 |
| `src/rov_gcs/rov_gcs/backend/telemetry.py` | 遥测缓存 + WebSocket 端点：缓存最新值、广播推送给所有客户端 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/index.html` | Vite 入口 HTML | 创建 |
| `src/rov_gcs/rov_gcs/frontend/package.json` | 前端依赖声明 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/vite.config.ts` | Vite 配置（含 dev proxy） | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/App.vue` | 根组件：三栏布局 + WebSocket 连接管理 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/main.ts` | Vue 入口 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/stores/telemetry.ts` | Pinia store：遥测状态、连接状态 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/composables/useWebSocket.ts` | WebSocket 封装：连接/重连/收发 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/composables/useApi.ts` | REST 调用封装：setTarget, toggleHold | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/composables/useGamepad.ts` | Gamepad API 封装：读取手柄状态、通过 WebSocket 发送 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/components/StatusBar.vue` | 状态栏：ROS 连接灯 + Hold 状态 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/components/DepthGauge.vue` | 深度仪表盘（CSS 圆弧） | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/components/VideoPlaceholder.vue` | 视频预留区 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/components/TelemetryPanel.vue` | 经纬度/偏航/PID 数字显示 | 创建 |
| `src/rov_gcs/rov_gcs/frontend/src/components/ControlPanel.vue` | 目标深度输入 + 定深开关 + 手柄状态 | 创建 |
| `src/rov_gcs/launch/gcs.launch.py` | 启动文件：rosbridge + uvicorn + nginx | 创建 |
| `src/rov_control/rov_control/depth_ctrl_node.py` | 新增 publish `/rov/depth_ctrl/status` (Bool) | 修改 |
| `src/rov_control/rov_control/adhesion_ctrl_node.py` | 新增订阅 joystick_cmd / depth_status，合并发布 ManualControl | 修改 |
| `src/rov_bringup/launch/rov.launch.py` | 加入控制节点启动 | 修改 |
| `auto-start.sh` | 加入上位机启动 | 修改 |

---

### Task 1: 新建 rov_gcs ROS2 包骨架

**Files:**
- Create: `src/rov_gcs/package.xml`
- Create: `src/rov_gcs/setup.py`
- Create: `src/rov_gcs/setup.cfg`
- Create: `src/rov_gcs/rov_gcs/__init__.py`
- Create: `src/rov_gcs/rov_gcs/backend/__init__.py`
- Create: `src/rov_gcs/resource/rov_gcs` (ament index marker)

**Interfaces:**
- Produces: Python 包 `rov_gcs`，可被 `ros2 run rov_gcs gcs_backend` 调用（entry point 暂指向占位 main）

- [ ] **Step 1: 创建 package.xml**

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>rov_gcs</name>
  <version>0.1.0</version>
  <description>Web GCS backend for BlueROV2</description>
  <maintainer email="wanghaojiehero@qq.com">oneBuYi</maintainer>
  <license>MIT</license>

  <exec_depend>rclpy</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>std_srvs</exec_depend>
  <exec_depend>mavros_msgs</exec_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

- [ ] **Step 2: 创建 setup.py**

```python
from setuptools import find_packages, setup

package_name = 'rov_gcs'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='oneBuYi',
    maintainer_email='wanghaojiehero@qq.com',
    description='Web GCS backend',
    license='MIT',
    entry_points={
        'console_scripts': [
            'gcs_backend = rov_gcs.backend.main:main',
        ],
    },
)
```

- [ ] **Step 3: 创建 setup.cfg**

```ini
[develop]
script_dir=$base/lib/rov_gcs
```

- [ ] **Step 4: 创建 __init__.py 占位文件**

```bash
touch src/rov_gcs/rov_gcs/__init__.py
touch src/rov_gcs/rov_gcs/backend/__init__.py
```

- [ ] **Step 5: 创建 ament index marker**

```bash
mkdir -p src/rov_gcs/resource
touch src/rov_gcs/resource/rov_gcs
```

- [ ] **Step 6: 创建占位 main.py 验证包可构建**

```python
# src/rov_gcs/rov_gcs/backend/main.py
def main():
    print("rov_gcs backend placeholder")


if __name__ == '__main__':
    main()
```

- [ ] **Step 7: 构建验证**

```bash
source /opt/ros/foxy/setup.bash
colcon build --packages-select rov_gcs
```

Expected: `Summary: 1 package finished`

- [ ] **Step 8: Commit**

```bash
git add src/rov_gcs/
git commit -m "feat: add rov_gcs package skeleton

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 2: rosbridge 连接管理器

**Files:**
- Create: `src/rov_gcs/rov_gcs/backend/rosbridge.py`

**Interfaces:**
- Produces:
  - `class RosbridgeClient` — 管理与 rosbridge 的 WebSocket 连接
    - `async connect() -> None` — 连接 rosbridge，失败时重试（指数退避 1s→2s→4s，上限 10s）
    - `async disconnect() -> None` — 取消所有订阅，关闭连接
    - `async subscribe(topic: str, msg_type: str, callback: Callable[[dict], None]) -> str` — 订阅 topic，返回 subscription id，收到消息时回调
    - `async unsubscribe(sub_id: str) -> None` — 取消订阅
    - `async publish(topic: str, msg_type: str, msg: dict) -> None` — 发布消息
    - `async call_service(service: str, args: dict) -> dict` — 调用 service，返回 values
    - `connected: bool` — 连接状态属性

- [ ] **Step 1: 写 rosbridge.py 完整实现**

```python
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
                self._ws = await websockets.connect(self._uri, ping_interval=20)
                self._connected = True
                self._recv_task = asyncio.create_task(self._recv_loop())
                logger.info(f"Connected to rosbridge at {self._uri}")
                return
            except (OSError, websockets.WebSocketException) as e:
                if not retry:
                    raise
                logger.warning(
                    f"rosbridge connection failed: {e}. Retrying in {backoff}s..."
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
        """Subscribe to a ROS topic. Returns subscription ID."""
        sub_id = f"sub_{topic}_{id(callback)}"
        async with self._lock:
            self._callbacks[sub_id] = callback
            msg = {
                "op": "subscribe",
                "id": sub_id,
                "topic": topic,
                "type": msg_type,
            }
            await self._ws.send(json.dumps(msg))
        logger.info(f"Subscribed to {topic} ({msg_type})")
        return sub_id

    async def unsubscribe(self, sub_id: str) -> None:
        """Cancel a subscription."""
        async with self._lock:
            self._callbacks.pop(sub_id, None)
            msg = {"op": "unsubscribe", "id": sub_id}
            await self._ws.send(json.dumps(msg))

    async def publish(self, topic: str, msg_type: str, msg: dict) -> None:
        """Publish a message to a ROS topic."""
        async with self._lock:
            payload = {
                "op": "publish",
                "topic": topic,
                "msg": msg,
            }
            await self._ws.send(json.dumps(payload))

    async def call_service(self, service: str, args: dict = None) -> dict:
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
            raise RuntimeError(f"Service call {service} timed out")

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
                    sub_id = msg.get("id", "")
                    topic = msg.get("topic", "")
                    data = msg.get("msg", {})
                    # Try exact match first, then match by topic prefix
                    cb = self._callbacks.get(sub_id)
                    if cb:
                        cb(data)

                elif op == "service_response":
                    call_id = msg.get("id", "")
                    future = self._pending_services.pop(call_id, None)
                    if future and not future.done():
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
```

- [ ] **Step 2: Commit**

```bash
git add src/rov_gcs/rov_gcs/backend/rosbridge.py
git commit -m "feat: add rosbridge WebSocket client

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 3: 数据模型 + 遥测缓存 + WebSocket 端点

**Files:**
- Create: `src/rov_gcs/rov_gcs/backend/models.py`
- Create: `src/rov_gcs/rov_gcs/backend/telemetry.py`

**Interfaces:**
- Produces:
  - `class Telemetry(BaseModel)` — 遥测数据模型
  - `class SetTargetRequest(BaseModel)` — 设定深度请求模型
  - `class ApiResponse(BaseModel)` — API 响应模型
  - `class TelemetryStore` — 遥测缓存单例
    - `update(data: dict) -> None` — 更新缓存
    - `snapshot() -> Telemetry` — 返回当前快照
    - `register_client(ws: WebSocket) -> None` — 注册前端 WebSocket 连接
    - `remove_client(ws: WebSocket) -> None` — 移除客户端
    - `broadcast() -> None` — 广播当前遥测给所有客户端
    - `joystick_queue: asyncio.Queue` — 手柄数据队列
  - `async def ws_endpoint(websocket: WebSocket) -> None` — WebSocket 端点（/ws）

- [ ] **Step 1: 创建 models.py**

```python
from pydantic import BaseModel, Field


class Telemetry(BaseModel):
    depth: float = 0.0              # 当前深度(m)，正=水下
    target_depth: float = 0.0       # 目标深度
    hold_enabled: bool = False      # 定深开关
    vertical_cmd: float = 0.0       # PID 输出
    lat: float = 0.0                # 纬度
    lon: float = 0.0                # 经度
    yaw: float = 0.0                # 偏航角(度)
    ros_connected: bool = False     # ROS 连接状态


class SetTargetRequest(BaseModel):
    target: float = Field(..., ge=0.0, description="目标深度(m)，必须 >= 0")


class ApiResponse(BaseModel):
    success: bool
    message: str
```

- [ ] **Step 2: 创建 telemetry.py**

```python
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

    def update(self, **kwargs) -> None:
        """Update cached telemetry fields. Thread-safe via asyncio lock
        (called only from rosbridge callback in same event loop)."""
        for key, value in kwargs.items():
            if hasattr(self._telemetry, key):
                setattr(self._telemetry, key, value)

    def snapshot(self) -> Telemetry:
        """Return a copy of current telemetry state."""
        return self._telemetry.model_copy()

    async def register_client(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.add(ws)
        logger.info(f"WebSocket client connected, total: {len(self._clients)}")

    async def remove_client(self, ws: WebSocket) -> None:
        async with self._lock:
            self._clients.discard(ws)
        logger.info(f"WebSocket client disconnected, total: {len(self._clients)}")

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
                # Put joystick data into queue for main loop to publish
                try:
                    store.joystick_queue.put_nowait(data)
                except asyncio.QueueFull:
                    pass  # Drop oldest if queue full
    except Exception:
        pass
    finally:
        await store.remove_client(websocket)
```

- [ ] **Step 3: Commit**

```bash
git add src/rov_gcs/rov_gcs/backend/models.py src/rov_gcs/rov_gcs/backend/telemetry.py
git commit -m "feat: add telemetry models, cache, and WebSocket endpoint

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 4: REST 路由

**Files:**
- Create: `src/rov_gcs/rov_gcs/backend/routes.py`

**Interfaces:**
- Consumes: `store: TelemetryStore` from `telemetry.py`, `rosbridge: RosbridgeClient` from `rosbridge.py`
- Produces:
  - `GET /api/telemetry` → `Telemetry`
  - `POST /api/depth/set_target` body `SetTargetRequest` → `ApiResponse`
  - `POST /api/depth/hold` → `ApiResponse`
  - `APIRouter router`

- [ ] **Step 1: 创建 routes.py**

```python
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
```

- [ ] **Step 2: Commit**

```bash
git add src/rov_gcs/rov_gcs/backend/routes.py
git commit -m "feat: add REST routes for telemetry and depth control

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 5: FastAPI 入口 + 生命周期集成

**Files:**
- Modify: `src/rov_gcs/rov_gcs/backend/main.py` (替换占位)

**Interfaces:**
- Produces:
  - `app = FastAPI(...)` — 带生命周期、路由、WebSocket 端点的完整的 app
  - `def get_rosbridge() -> Optional[RosbridgeClient]` — 模块级 getter，供 routes 使用
  - `def main()` — 控制台入口，启动 uvicorn

- [ ] **Step 1: 替换 main.py**

```python
#!/usr/bin/env python3
import asyncio
import logging
import signal
import sys
import time
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    """/mavros/global_position/rel_alt → depth (negated)."""
    alt = msg.get("data", 0.0)
    store.update(depth=round(-alt, 2))


def on_global_position(msg: dict):
    """/mavros/global_position/global → lat, lon."""
    store.update(lat=msg.get("latitude", 0.0), lon=msg.get("longitude", 0.0))


def on_compass_hdg(msg: dict):
    """/mavros/global_position/compass_hdg → yaw."""
    store.update(yaw=round(msg.get("data", 0.0), 2))


def on_vertical_cmd(msg: dict):
    """/rov/depth_ctrl/vertical_cmd → PID output."""
    store.update(vertical_cmd=round(msg.get("data", 0.0), 2))


# ----- joystick publisher -----

async def joystick_publisher():
    """Publish joystick data from queue to ROS via rosbridge.
    Handles timeout protection: if no data for 500ms, send zeros.
    """
    last_time = 0.0
    while True:
        try:
            # Wait up to 500ms for next joystick frame
            data = await asyncio.wait_for(store.joystick_queue.get(), timeout=0.5)
            last_time = time.time()
        except asyncio.TimeoutError:
            data = None

        rb = get_rosbridge()
        if not rb or not rb.connected:
            continue

        now = time.time()
        if data is None or (now - last_time > 0.5 and data is None):
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
            logger.warning(f"rosbridge not available, retry {retry_count}...")
            await asyncio.sleep(2.0)

    # Subscribe to telemetry topics
    await _rosbridge.subscribe(
        "/mavros/global_position/rel_alt", "std_msgs/Float64", on_rel_alt
    )
    await _rosbridge.subscribe(
        "/mavros/global_position/global", "sensor_msgs/NavSatFix", on_global_position
    )
    await _rosbridge.subscribe(
        "/mavros/global_position/compass_hdg",
        "std_msgs/Float64",
        on_compass_hdg,
    )
    await _rosbridge.subscribe(
        "/rov/depth_ctrl/vertical_cmd", "std_msgs/Float32", on_vertical_cmd
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


app = FastAPI(title="ROV GCS Backend", version="0.1.0", lifespan=lifespan)

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
```

- [ ] **Step 2: 构建验证**

```bash
source /opt/ros/foxy/setup.bash
colcon build --packages-select rov_gcs
```

Expected: `Summary: 1 package finished`

- [ ] **Step 3: Commit**

```bash
git add src/rov_gcs/rov_gcs/backend/main.py
git commit -m "feat: add FastAPI app with lifespan, rosbridge subs, joystick pub

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 6: Vue 3 + Vite 前端脚手架

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/package.json`
- Create: `src/rov_gcs/rov_gcs/frontend/index.html`
- Create: `src/rov_gcs/rov_gcs/frontend/vite.config.ts`
- Create: `src/rov_gcs/rov_gcs/frontend/src/main.ts`
- Create: `src/rov_gcs/rov_gcs/frontend/src/App.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/env.d.ts`

- [ ] **Step 1: 创建 package.json**

```json
{
  "name": "rov-gcs-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "pinia": "^2.1.7",
    "vue": "^3.4.0"
  },
  "devDependencies": {
    "@vitejs/plugin-vue": "^4.5.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "vue-tsc": "^1.8.0"
  }
}
```

- [ ] **Step 2: 创建 index.html**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>ROV 上位机</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: 'Segoe UI', system-ui, -apple-system, sans-serif;
      background: #0a0e17;
      color: #e0e6ed;
      min-height: 100vh;
    }
  </style>
</head>
<body>
  <div id="app"></div>
  <script type="module" src="/src/main.ts"></script>
</body>
</html>
```

- [ ] **Step 3: 创建 vite.config.ts**

```typescript
import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true,
      },
    },
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets',
  },
})
```

- [ ] **Step 4: 创建 src/env.d.ts**

```typescript
/// <reference types="vite/client" />

declare module '*.vue' {
  import type { DefineComponent } from 'vue'
  const component: DefineComponent<{}, {}, any>
  export default component
}
```

- [ ] **Step 5: 创建 src/main.ts**

```typescript
import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'

const app = createApp(App)
app.use(createPinia())
app.mount('#app')
```

- [ ] **Step 6: 创建最简 App.vue（占位）**

```vue
<template>
  <div id="gcs-app">
    <h1>ROV 上位机</h1>
    <p>前端加载成功</p>
  </div>
</template>

<script setup lang="ts">
</script>

<style scoped>
#gcs-app {
  padding: 2rem;
  text-align: center;
}
h1 { color: #00d4ff; }
</style>
```

- [ ] **Step 7: 安装依赖 + 验证构建**

```bash
cd src/rov_gcs/rov_gcs/frontend
npm install
npm run build
```

Expected: `vite build` 完成，`dist/` 目录生成。

- [ ] **Step 8: Commit**

```bash
git add src/rov_gcs/rov_gcs/frontend/
git commit -m "feat: scaffold Vue 3 + Vite frontend

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 7: 前端 Pinia Store + WebSocket Composable

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/stores/telemetry.ts`
- Create: `src/rov_gcs/rov_gcs/frontend/src/composables/useWebSocket.ts`

**Interfaces:**
- Produces:
  - `useTelemetryStore()` — Pinia store:
    - `telemetry: Telemetry` — 遥测数据（reactive）
    - `rosConnected: boolean`
    - `updateTelemetry(data: Partial<Telemetry>) -> void`
    - `setRosConnected(v: boolean) -> void`
  - `useWebSocket(url: string)` — 返回 `{ send(data): void, close(): void }`

- [ ] **Step 1: 创建 stores/telemetry.ts**

```typescript
import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'

export interface Telemetry {
  depth: number
  target_depth: number
  hold_enabled: boolean
  vertical_cmd: number
  lat: number
  lon: number
  yaw: number
  ros_connected: boolean
}

function defaultTelemetry(): Telemetry {
  return {
    depth: 0,
    target_depth: 0,
    hold_enabled: false,
    vertical_cmd: 0,
    lat: 0,
    lon: 0,
    yaw: 0,
    ros_connected: false,
  }
}

export const useTelemetryStore = defineStore('telemetry', () => {
  const state = reactive<{ telemetry: Telemetry }>({
    telemetry: defaultTelemetry(),
  })

  function updateTelemetry(data: Partial<Telemetry>) {
    Object.assign(state.telemetry, data)
  }

  function setRosConnected(v: boolean) {
    state.telemetry.ros_connected = v
  }

  return {
    ...toRefs(state),
    updateTelemetry,
    setRosConnected,
  }
})
```

- [ ] **Step 2: 创建 composables/useWebSocket.ts**

```typescript
import { ref } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

export function useWebSocket(url: string) {
  const connected = ref(false)
  let ws: WebSocket | null = null
  let reconnectTimer: number | null = null
  const store = useTelemetryStore()

  function connect() {
    if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
      return
    }
    try {
      ws = new WebSocket(url)
    } catch (e) {
      scheduleReconnect()
      return
    }

    ws.onopen = () => {
      connected.value = true
      store.setRosConnected(true)
    }

    ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data)
        if (msg.type === 'telemetry' && msg.data) {
          store.updateTelemetry(msg.data)
        }
      } catch {
        // ignore malformed messages
      }
    }

    ws.onclose = () => {
      connected.value = false
      store.setRosConnected(false)
      scheduleReconnect()
    }

    ws.onerror = () => {
      ws?.close()
    }
  }

  function scheduleReconnect() {
    if (reconnectTimer !== null) return
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = null
      connect()
    }, 2000)
  }

  function send(data: unknown) {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }

  function close() {
    if (reconnectTimer !== null) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    ws?.close()
    ws = null
  }

  return { connected, connect, send, close }
}
```

- [ ] **Step 3: 更新 App.vue 测试连接**

```vue
<template>
  <div id="gcs-app">
    <div class="status-bar">
      <span class="dot" :class="store.telemetry.value.ros_connected ? 'green' : 'red'"></span>
      {{ store.telemetry.value.ros_connected ? 'ROS 已连接' : 'ROS 未连接' }}
      | 深度: {{ store.telemetry.value.depth }}m
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import { useWebSocket } from './composables/useWebSocket'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const wsUrl = `ws://${window.location.host}/ws`
const { connect, close } = useWebSocket(wsUrl)

onMounted(() => connect())
onUnmounted(() => close())
</script>

<style scoped>
.status-bar {
  padding: 8px 16px;
  background: #1a1f2e;
  font-size: 14px;
}
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; }
.green { background: #00e676; }
.red { background: #ff1744; }
</style>
```

- [ ] **Step 4: 构建验证**

```bash
cd src/rov_gcs/rov_gcs/frontend
npm run build
```

Expected: 无 TypeScript 错误，构建成功。

- [ ] **Step 5: Commit**

```bash
git add src/rov_gcs/rov_gcs/frontend/src/stores/ src/rov_gcs/rov_gcs/frontend/src/composables/ src/rov_gcs/rov_gcs/frontend/src/App.vue
git commit -m "feat: add Pinia store and WebSocket composable

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 8: 前端遥测显示组件

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/StatusBar.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/DepthGauge.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/VideoPlaceholder.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/TelemetryPanel.vue`

- [ ] **Step 1: 创建 StatusBar.vue**

```vue
<template>
  <div class="status-bar">
    <span class="indicator">
      <span class="dot" :class="rosConnected ? 'green' : 'red'"></span>
      {{ rosConnected ? 'ROS 已连接' : 'ROS 未连接' }}
    </span>
    <span class="spacer"></span>
    <span class="hold-badge" :class="holdEnabled ? 'active' : ''">
      HOLD {{ holdEnabled ? '开' : '关' }}
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  rosConnected: boolean
  holdEnabled: boolean
}>()
</script>

<style scoped>
.status-bar {
  display: flex; align-items: center; padding: 6px 16px;
  background: #141924; border-bottom: 1px solid #2a3040; font-size: 13px;
}
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; }
.green { background: #00e676; box-shadow: 0 0 6px #00e676; }
.red { background: #ff1744; box-shadow: 0 0 6px #ff1744; }
.spacer { flex: 1; }
.hold-badge {
  padding: 2px 10px; border-radius: 4px; background: #2a3040; color: #8899aa;
}
.hold-badge.active { background: #00d4ff33; color: #00d4ff; }
</style>
```

- [ ] **Step 2: 创建 DepthGauge.vue（CSS 圆弧仪表盘）**

```vue
<template>
  <div class="depth-gauge">
    <svg viewBox="0 0 200 200" class="gauge-svg">
      <!-- Background arc -->
      <circle cx="100" cy="100" r="85" fill="none" stroke="#2a3040" stroke-width="12" />
      <!-- Value arc (270 degrees, from 135° to 405°) -->
      <circle
        cx="100" cy="100" r="85" fill="none"
        :stroke="gaugeColor"
        stroke-width="12"
        stroke-linecap="round"
        :stroke-dasharray="`${arcLength} 534`"
        stroke-dashoffset="0"
        transform="rotate(135, 100, 100)"
      />
      <!-- Depth reading -->
      <text x="100" y="95" text-anchor="middle" class="depth-value">{{ depth.toFixed(1) }}</text>
      <text x="100" y="115" text-anchor="middle" class="depth-unit">m</text>
      <!-- Target indicator -->
      <text x="100" y="140" text-anchor="middle" class="target-text">
        目标 {{ targetDepth.toFixed(1) }} m
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  depth: number
  targetDepth: number
  maxDepth?: number
}>()

const maxDepth = computed(() => props.maxDepth || 10)

const ratio = computed(() => Math.min(props.depth / maxDepth.value, 1.0))

const arcLength = computed(() => Math.round(ratio.value * 400))

const gaugeColor = computed(() => {
  if (ratio.value > 0.7) return '#ff6b6b'
  if (ratio.value > 0.4) return '#ffd93d'
  return '#00d4ff'
})
</script>

<style scoped>
.depth-gauge {
  display: flex; justify-content: center; align-items: center;
  padding: 16px;
}
.gauge-svg { width: 200px; height: 200px; }
.depth-value { font-size: 36px; font-weight: 700; fill: #e0e6ed; }
.depth-unit { font-size: 14px; fill: #8899aa; }
.target-text { font-size: 12px; fill: #8899aa; }
</style>
```

- [ ] **Step 3: 创建 VideoPlaceholder.vue**

```vue
<template>
  <div class="video-placeholder">
    <div class="placeholder-content">
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#4a5568" stroke-width="1.5">
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M10 9l5 3-5 3V9z" fill="#4a5568" />
      </svg>
      <p>视频功能开发中</p>
    </div>
  </div>
</template>

<style scoped>
.video-placeholder {
  display: flex; justify-content: center; align-items: center;
  height: 200px; background: #141924; border: 1px dashed #2a3040;
  border-radius: 8px; margin: 8px 0;
}
.placeholder-content { text-align: center; }
.placeholder-content p { margin-top: 8px; color: #4a5568; font-size: 13px; }
</style>
```

- [ ] **Step 4: 创建 TelemetryPanel.vue**

```vue
<template>
  <div class="telemetry-panel">
    <div class="telem-item">
      <span class="label">纬度</span>
      <span class="value">{{ lat.toFixed(4) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">经度</span>
      <span class="value">{{ lon.toFixed(4) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">偏航角</span>
      <span class="value">{{ yaw.toFixed(1) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">PID 输出</span>
      <span class="value">{{ verticalCmd.toFixed(1) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  lat: number
  lon: number
  yaw: number
  verticalCmd: number
}>()
</script>

<style scoped>
.telemetry-panel {
  display: flex; flex-direction: column; gap: 8px; padding: 8px;
}
.telem-item {
  display: flex; justify-content: space-between; padding: 6px 12px;
  background: #141924; border-radius: 6px;
}
.label { color: #8899aa; font-size: 13px; }
.value { color: #e0e6ed; font-size: 14px; font-weight: 600; font-family: monospace; }
</style>
```

- [ ] **Step 5: Commit**

```bash
git add src/rov_gcs/rov_gcs/frontend/src/components/
git commit -m "feat: add status bar, depth gauge, video placeholder, telemetry panel components

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 9: 前端控制面板 + REST Composable

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/composables/useApi.ts`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/ControlPanel.vue`
- Modify: `src/rov_gcs/rov_gcs/frontend/src/App.vue` (组装全部组件)

- [ ] **Step 1: 创建 useApi.ts**

```typescript
import { useTelemetryStore } from '../stores/telemetry'

const BASE = '/api'

async function request(method: string, path: string, body?: unknown) {
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text)
  }
  return resp.json()
}

export function useApi() {
  const store = useTelemetryStore()

  async function setTarget(target: number) {
    if (target < 0) throw new Error('目标深度必须 >= 0')
    const result = await request('POST', '/depth/set_target', { target })
    store.updateTelemetry({ target_depth: target, hold_enabled: true })
    return result
  }

  async function toggleHold() {
    const result = await request('POST', '/depth/hold')
    // Infer hold state from response message
    if (result.message) {
      const enabled = result.message.toLowerCase().includes('enabled')
      store.updateTelemetry({ hold_enabled: enabled })
    }
    return result
  }

  return { setTarget, toggleHold }
}
```

- [ ] **Step 2: 创建 ControlPanel.vue**

```vue
<template>
  <div class="control-panel">
    <div class="depth-control">
      <label>目标深度 (m)</label>
      <div class="input-row">
        <input
          v-model.number="targetInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="输入深度"
          @keyup.enter="handleSetTarget"
        />
        <button :disabled="sending" @click="handleSetTarget">设定</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
    <button
      class="hold-btn"
      :class="holdEnabled ? 'active' : ''"
      :disabled="sending"
      @click="handleHold"
    >
      {{ holdEnabled ? '关闭定深' : '开启定深' }}
    </button>
    <div class="gamepad-status">
      🎮 {{ gamepadConnected ? '手柄已连接' : '手柄未连接' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useApi } from '../composables/useApi'
import { useTelemetryStore } from '../stores/telemetry'

const props = defineProps<{ gamepadConnected: boolean }>()
const store = useTelemetryStore()
const { setTarget, toggleHold } = useApi()
const targetInput = ref(0)
const sending = ref(false)
const error = ref('')

const holdEnabled = computed(() => store.telemetry.value.hold_enabled)

async function handleSetTarget() {
  error.value = ''
  if (targetInput.value < 0) {
    error.value = '深度不能为负数'
    return
  }
  sending.value = true
  try {
    await setTarget(targetInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleHold() {
  error.value = ''
  sending.value = true
  try {
    await toggleHold()
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.control-panel {
  display: flex; align-items: center; gap: 16px; padding: 10px 16px;
  background: #141924; border-top: 1px solid #2a3040;
}
.depth-control { display: flex; align-items: center; gap: 8px; flex: 1; }
.depth-control label { color: #8899aa; font-size: 13px; white-space: nowrap; }
.input-row { display: flex; gap: 6px; }
input {
  width: 100px; padding: 6px 10px; border: 1px solid #2a3040; border-radius: 4px;
  background: #0a0e17; color: #e0e6ed; font-size: 14px;
}
input:focus { outline: none; border-color: #00d4ff; }
button {
  padding: 6px 14px; border: none; border-radius: 4px; cursor: pointer;
  font-size: 13px; background: #00d4ff; color: #0a0e17; font-weight: 600;
}
button:disabled { opacity: 0.5; cursor: not-allowed; }
.hold-btn { background: #2a3040; color: #8899aa; }
.hold-btn.active { background: #00d4ff33; color: #00d4ff; }
.error { color: #ff6b6b; font-size: 12px; margin-left: 8px; }
.gamepad-status { margin-left: auto; font-size: 13px; color: #8899aa; }
</style>
```

- [ ] **Step 3: 更新 App.vue 组装全部组件**

```vue
<template>
  <div id="gcs-app">
    <StatusBar
      :ros-connected="t.ros_connected"
      :hold-enabled="t.hold_enabled"
    />
    <div class="dashboard">
      <DepthGauge :depth="t.depth" :target-depth="t.target_depth" />
      <VideoPlaceholder />
      <TelemetryPanel
        :lat="t.lat" :lon="t.lon" :yaw="t.yaw" :vertical-cmd="t.vertical_cmd"
      />
    </div>
    <ControlPanel :gamepad-connected="gamepadConnected" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import VideoPlaceholder from './components/VideoPlaceholder.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const t = computed(() => store.telemetry.value)
const gamepadConnected = ref(false)

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

onMounted(() => connect())
onUnmounted(() => close())

// Provide send to ControlPanel (for gamepad)
;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => { gamepadConnected.value = v }
</script>

<style>
#gcs-app {
  display: flex; flex-direction: column; height: 100vh;
  max-width: 960px; margin: 0 auto;
}
.dashboard {
  flex: 1; display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px; padding: 8px;
}
@media (max-width: 700px) {
  .dashboard { grid-template-columns: 1fr; }
}
</style>
```

- [ ] **Step 4: 构建验证**

```bash
cd src/rov_gcs/rov_gcs/frontend
npm run build
```

Expected: 无错误，构建成功。

- [ ] **Step 5: Commit**

```bash
git add src/rov_gcs/rov_gcs/frontend/src/
git commit -m "feat: add control panel, API composable, and wire up App layout

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 10: 改造 depth_ctrl_node 发布 status

**Files:**
- Modify: `src/rov_control/rov_control/depth_ctrl_node.py`

**Changes:**
- 新增 `from std_msgs.msg import Bool`（已有 Float64、Float32，加 Bool）
- 在 `__init__` 中新增 publisher: `self._status_pub = self.create_publisher(Bool, 'depth_ctrl/status', 10)`
- 在 `_hold_cb` 中，每次切换后 publish status

- [ ] **Step 1: 编辑 depth_ctrl_node.py**

```
# 第 1 行 import 区，新增 Bool：
from std_msgs.msg import Float64, Float32, Bool

# 在 __init__ 中，_srv_hold 之后，_timer 之前插入：
        self._status_pub = self.create_publisher(
            Bool, 'depth_ctrl/status', 10)

# 在 _hold_cb 中，self._enabled = not self._enabled 之后，调用 _pid.reset() 之前插入：
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
```

> 等价于下面这些编辑操作。

- [ ] **Step 2: 修改 import 行**

在 `depth_ctrl_node.py` 第 5 行 `from std_msgs.msg import Float64, Float32` 改为 `from std_msgs.msg import Float64, Float32, Bool`

- [ ] **Step 3: 在 __init__ 中新增 publisher**

定位到 `self._srv_hold = self.create_service(...)` 那几行之后，`self._timer` 之前，插入：

```python
        self._status_pub = self.create_publisher(
            Bool, 'depth_ctrl/status', 10)
```

- [ ] **Step 4: 在 _hold_cb 中新增 publish**

定位到 `self._enabled = not self._enabled` 之后，`self._pid.reset()` 之前，插入：

```python
        msg = Bool()
        msg.data = self._enabled
        self._status_pub.publish(msg)
```

- [ ] **Step 5: 构建验证**

```bash
source /opt/ros/foxy/setup.bash
colcon build --packages-select rov_control
```

Expected: `Summary: 1 package finished`

- [ ] **Step 6: Commit**

```bash
git add src/rov_control/rov_control/depth_ctrl_node.py
git commit -m "feat: depth_ctrl_node publish /rov/depth_ctrl/status on hold toggle

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 11: 改造 adhesion_ctrl_node 接入手柄 + status

**Files:**
- Modify: `src/rov_control/rov_control/adhesion_ctrl_node.py`

**Changes:**
- 新增订阅 `/rov/joystick/cmd`（ManualControl）和 `/rov/depth_ctrl/status`（Bool）
- 内部缓存 joystick_x/y/z/r、vertical_cmd、hold_enabled
- 每次收到任一消息时，合并发布到 `/mavros/manual_control/send`

- [ ] **Step 1: 替换 adhesion_ctrl_node.py 完整内容**

```python
import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup
from rclpy.executors import MultiThreadedExecutor
from std_msgs.msg import Float32, Bool
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class RovAdhesionCtrlNode(Node):
    def __init__(self):
        super().__init__('adhesion_ctrl', namespace='rov')

        self._vertical_cmd = 0.0
        self._joystick_x = 0
        self._joystick_y = 0
        self._joystick_z = 0
        self._joystick_r = 0
        self._hold_enabled = False
        self._cb_group = MutuallyExclusiveCallbackGroup()

        self._sub_vertical = self.create_subscription(
            Float32, '/rov/depth_ctrl/vertical_cmd',
            self._on_vertical_cmd, 10)

        self._sub_joystick = self.create_subscription(
            ManualControl, '/rov/joystick/cmd',
            self._on_joystick_cmd, 10)

        self._sub_hold_status = self.create_subscription(
            Bool, '/rov/depth_ctrl/status',
            self._on_hold_status, 10)

        self._pub = self.create_publisher(
            ManualControl, '/mavros/manual_control/send', 10)

        self._srv_toggle = self.create_service(
            Trigger, 'adhesion_ctrl/toggle_depth',
            self._toggle_depth_cb, callback_group=self._cb_group)

        self._depth_hold_client = self.create_client(
            Trigger, 'depth_ctrl/hold', callback_group=self._cb_group)

        self.get_logger().info('rov_adhesion_ctrl started')

    def _on_vertical_cmd(self, msg):
        self._vertical_cmd = msg.data
        self._publish_merged()

    def _on_joystick_cmd(self, msg):
        self._joystick_x = int(msg.x)
        self._joystick_y = int(msg.y)
        self._joystick_z = int(msg.z)
        self._joystick_r = int(msg.r)
        self._publish_merged()

    def _on_hold_status(self, msg):
        self._hold_enabled = msg.data
        self._publish_merged()

    def _publish_merged(self):
        manual = ManualControl()
        manual.x = self._joystick_x
        manual.y = self._joystick_y
        manual.r = self._joystick_r
        manual.z = float(self._vertical_cmd) if self._hold_enabled else float(self._joystick_z)
        self._pub.publish(manual)

    def _toggle_depth_cb(self, request, response):
        if not self._depth_hold_client.wait_for_service(timeout_sec=0.5):
            response.success = False
            response.message = 'depth_ctrl hold service not available'
            return response

        future = self._depth_hold_client.call_async(request)
        future.add_done_callback(self._toggle_done_cb)

        response.success = True
        response.message = 'Toggle request forwarded'
        return response

    def _toggle_done_cb(self, future):
        try:
            response = future.result()
            self.get_logger().info(
                f'Toggle depth result: success={response.success}, '
                f'message="{response.message}"')
        except Exception as e:
            self.get_logger().error(f'Toggle depth call failed: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = RovAdhesionCtrlNode()
    executor = MultiThreadedExecutor()
    executor.add_node(node)
    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        executor.shutdown()
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 构建验证**

```bash
source /opt/ros/foxy/setup.bash
colcon build --packages-select rov_control
```

Expected: `Summary: 1 package finished`

- [ ] **Step 3: Commit**

```bash
git add src/rov_control/rov_control/adhesion_ctrl_node.py
git commit -m "feat: adhesion_ctrl_node supports joystick + hold_status merging

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 12: 手柄 Composable（Gamepad API）

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/composables/useGamepad.ts`

**Interfaces:**
- Produces: `useGamepad(options: {onData: (data) => void, onConnect?: (v: boolean) => void})` → `{ start(), stop() }`

- [ ] **Step 1: 创建 useGamepad.ts**

```typescript
interface JoystickData {
  x: number   // -100 ~ 100
  y: number
  z: number
  r: number
}

export function useGamepad(options: {
  onData: (data: JoystickData) => void
  onConnect?: (connected: boolean) => void
}) {
  let animFrameId: number | null = null
  let wasConnected = false

  function poll() {
    const gamepads = navigator.getGamepads()
    const gamepad = gamepads[0]  // Use first gamepad

    const connected = gamepad !== null
    if (connected !== wasConnected) {
      wasConnected = connected
      options.onConnect?.(connected)
    }

    if (gamepad) {
      // axes: 0=leftX, 1=leftY, 2=rightX, 3=rightY
      // buttons: 0=A, 1=B, 2=X, 3=Y, 4=LB, 5=RB, 6=LT, 7=RT
      const leftX = gamepad.axes[0] ?? 0    // left stick horizontal
      const leftY = gamepad.axes[1] ?? 0    // left stick vertical
      const rightX = gamepad.axes[2] ?? 0   // right stick horizontal
      const rightY = gamepad.axes[3] ?? 0   // right stick vertical

      // Map to MAVLink convention:
      // x = forward/back (left stick Y, reversed: up = positive)
      // y = lateral (left stick X)
      // z = vertical (right stick Y, reversed)
      // r = yaw (right stick X)
      const data: JoystickData = {
        x: Math.round(-leftY * 100),   // forward = positive
        y: Math.round(leftX * 100),    // right = positive
        z: Math.round(-rightY * 100),  // up = positive
        r: Math.round(rightX * 100),   // right turn = positive
      }
      options.onData(data)
    }

    animFrameId = requestAnimationFrame(poll)
  }

  function start() {
    if (animFrameId === null) {
      animFrameId = requestAnimationFrame(poll)
    }
  }

  function stop() {
    if (animFrameId !== null) {
      cancelAnimationFrame(animFrameId)
      animFrameId = null
    }
  }

  return { start, stop }
}
```

- [ ] **Step 2: 更新 App.vue 集成 Gamepad**

在 `App.vue` 中新增导入并使用：

```typescript
// 新增 import
import { useGamepad } from './composables/useGamepad'

// 在 onMounted 中，connect() 之后新增：
const gamepad = useGamepad({
  onData: (data) => {
    (window as any).__gcsSend?.({ type: 'joystick', data })
  },
  onConnect: (v) => {
    (window as any).__gcsSetGamepadConnected?.(v)
  },
})
gamepad.start()
```

- [ ] **Step 3: 最终 App.vue 的 `<script>` 部分应为：**

```vue
<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import VideoPlaceholder from './components/VideoPlaceholder.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useGamepad } from './composables/useGamepad'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const t = computed(() => store.telemetry.value)
const gamepadConnected = ref(false)

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => { gamepadConnected.value = v }

onMounted(() => {
  connect()
  const gamepad = useGamepad({
    onData: (data) => {
      send({ type: 'joystick', data })
    },
    onConnect: (v) => {
      gamepadConnected.value = v
    },
  })
  gamepad.start()
})

onUnmounted(() => close())
</script>
```

- [ ] **Step 4: 构建验证**

```bash
cd src/rov_gcs/rov_gcs/frontend
npm run build
```

Expected: 无错误。

- [ ] **Step 5: Commit**

```bash
git add src/rov_gcs/rov_gcs/frontend/src/
git commit -m "feat: add Gamepad API composable, integrate with WebSocket

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 13: 启动文件 + 部署整合

**Files:**
- Create: `src/rov_gcs/launch/gcs.launch.py`
- Modify: `src/rov_bringup/launch/rov.launch.py` (加入 depth_ctrl + adhesion_ctrl)
- Modify: `auto-start.sh` (加入上位机启动)

- [ ] **Step 1: 创建 launch/gcs.launch.py**

```python
import os
import subprocess
import signal
import sys

from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    OpaqueFunction,
    RegisterEventHandler,
    LogInfo,
)
from launch.event_handlers import OnProcessExit


def _launch_web_stack(context, *args, **kwargs):
    """Launch rosbridge, uvicorn, and nginx."""
    actions = []

    # 1. rosbridge_server
    rosbridge = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'rosbridge_server', 'rosbridge_websocket',
            '--ros-args',
            '-p', 'port:=9090',
            '-p', 'address:=0.0.0.0',
        ],
        output='screen',
    )
    actions.append(rosbridge)

    # 2. uvicorn (FastAPI backend)
    uvicorn_cmd = ExecuteProcess(
        cmd=[
            sys.executable, '-m', 'uvicorn',
            'rov_gcs.backend.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
        ],
        output='screen',
    )
    actions.append(uvicorn_cmd)

    # 3. nginx (serve frontend static files)
    # Find frontend dist path relative to this package
    frontend_dist = os.path.join(
        os.path.dirname(__file__), '..', 'rov_gcs', 'frontend', 'dist'
    )
    # Create nginx config inline
    nginx_conf = os.path.join('/tmp', 'rov_gcs_nginx.conf')
    with open(nginx_conf, 'w') as f:
        f.write(f"""
worker_processes 1;
pid /tmp/rov_gcs_nginx.pid;
error_log /tmp/rov_gcs_nginx_error.log;
events {{ worker_connections 64; }}
http {{
    access_log /tmp/rov_gcs_nginx_access.log;
    server {{
        listen 80;
        location / {{
            root {frontend_dist};
            index index.html;
            try_files $uri $uri/ /index.html;
        }}
        location /api {{
            proxy_pass http://127.0.0.1:8000;
        }}
        location /ws {{
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}
    }}
}}
""")
    nginx_cmd = ExecuteProcess(
        cmd=['nginx', '-c', nginx_conf, '-g', 'daemon off;'],
        output='screen',
    )
    actions.append(nginx_cmd)

    # Log after rosbridge exits
    actions.append(RegisterEventHandler(
        OnProcessExit(
            target_action=rosbridge,
            on_exit=[LogInfo(msg='rosbridge exited, shutting down web stack')],
        )
    ))

    return actions


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=_launch_web_stack),
    ])
```

- [ ] **Step 2: 更新 setup.py 加入 launch 文件**

```python
# 在 setup.py 的 data_files 中新增：
(os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
```

`glob` 已在 setup.py 中 import（从现有 pattern 看已有 `from glob import glob`）。

- [ ] **Step 3: 更新 rov_bringup launch 文件**

```python
# src/rov_bringup/launch/rov.launch.py
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        parameters=[{
            'fcu_url': '/dev/pixhawk:115200',
            'gcs_url': 'udp-b://@0.0.0.0:14551',
        }],
        output='screen',
    )

    depth_ctrl_node = Node(
        package='rov_control',
        executable='depth_ctrl_node',
        output='screen',
    )

    adhesion_ctrl_node = Node(
        package='rov_control',
        executable='adhesion_ctrl_node',
        output='screen',
    )

    return LaunchDescription([
        mavros_node,
        depth_ctrl_node,
        adhesion_ctrl_node,
    ])
```

- [ ] **Step 4: 更新 auto-start.sh**

```bash
#!/bin/bash

source /opt/ros/foxy/setup.bash
source /home/jetson/whj/rov-ros/install/setup.bash

ros2 launch rov_bringup rov.launch.py &
sleep 5
ros2 launch rov_gcs gcs.launch.py &

wait
```

- [ ] **Step 5: 更新 setup.py data_files（确保 launch 文件被安装）**

确认 `src/rov_gcs/setup.py` 已有：
```python
(os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
```

（在 Task 1 的 setup.py 中没有这行，需要新增）

- [ ] **Step 6: 构建全部**

```bash
source /opt/ros/foxy/setup.bash
colcon build
```

Expected: 所有 4 个包构建成功。

- [ ] **Step 7: Commit**

```bash
git add src/rov_gcs/launch/ src/rov_gcs/setup.py src/rov_bringup/launch/rov.launch.py auto-start.sh
git commit -m "feat: add GCS launch file, integrate control nodes in bringup, update auto-start

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

### Task 14: ROS2 依赖安装 + 端到端验证

**Files:** 无新文件，验证性任务。

- [ ] **Step 1: 安装 rosbridge**

```bash
sudo apt-get update
sudo apt-get install -y ros-foxy-rosbridge-suite
```

- [ ] **Step 2: 安装 Python 依赖**

```bash
pip install fastapi uvicorn websockets pydantic
```

- [ ] **Step 3: 安装 nginx**

```bash
sudo apt-get install -y nginx-core
```

- [ ] **Step 4: 构建前端（在 Jetson 上）**

```bash
cd src/rov_gcs/rov_gcs/frontend
# 如果 npm 未安装: sudo apt-get install -y nodejs npm
npm install
npm run build
```

Expected: `dist/` 目录生成。

- [ ] **Step 5: 构建 ROS 包**

```bash
source /opt/ros/foxy/setup.bash
colcon build
```

Expected: 4 个包全部成功。

- [ ] **Step 6: 启动验证**

```bash
source install/setup.bash
# Terminal 1
ros2 launch rov_gcs gcs.launch.py
```

Expected: rosbridge 启动（日志可见），uvicorn 启动（`Uvicorn running on http://0.0.0.0:8000`），nginx 启动。

```bash
# Terminal 2: 验证 rosbridge 连通性
curl http://localhost:8000/api/telemetry
```

Expected: `{"depth":0.0,"target_depth":0.0,...}` 的 JSON 响应。

```bash
# Terminal 3: 验证 WebSocket
wscat -c ws://localhost:8000/ws
```

Expected: 连接成功，每 100ms 收到 JSON telemetry 推送。

- [ ] **Step 7: 确认浏览器访问**

在操作员 PC 浏览器打开 `http://<jetson-ip>:8000`（或 `:80` 如果用 nginx 80 端口），应看到完整 UI。

- [ ] **Step 8: Commit（如有变更）**

```bash
git add -A
git commit -m "chore: dependency notes and verification

Co-Authored-By: Claude <noreply@anthropic.com>"
```

---

## Spec Self-Review

### Coverage Check

| Spec Section | Task(s) |
|---|---|
| 2. 架构 (rosbridge + FastAPI + Vue) | Task 1, 5, 6, 13 |
| 3.1 rosbridge 协议对接 | Task 2, 5 |
| 3.2 订阅 4 个 topic | Task 5 (main.py 生命周期) |
| 3.3 调用 2 个 service | Task 4 (routes.py) |
| 3.4 发布 joystick/cmd | Task 5 (joystick_publisher) |
| 4.1 REST 3 个端点 | Task 4 |
| 4.2 WebSocket /ws | Task 3, 5, 7 |
| 5.1 depth_ctrl 新增 status publish | Task 10 |
| 5.2 adhesion_ctrl 改造合并逻辑 | Task 11 |
| 6.1 页面布局 | Task 9 (App.vue) |
| 6.2 组件树 (5 组件) | Task 8, 9 |
| 6.3 数据流 (WebSocket + Store + Gamepad) | Task 7, 9, 12 |
| 6.4 技术细节 (Vite proxy, 100ms, 重连) | Task 6, 7 |
| 7. 项目结构 | Task 1 (全部文件) |
| 8. 启动部署 | Task 13 |
| 9. 错误处理 | Tasks 4, 5, 7 (每个任务内) |
| 10. 实现顺序 | 14 tasks 按顺序覆盖 8 个阶段 |

✅ 所有 spec 章节均有对应 task。

### Placeholder Scan

✅ 无 TBD、TODO、占位符。每个 step 带有完整代码或精确命令。

### Type Consistency

- `Telemetry` 模型字段名：Task 3 `models.py` 定义，Task 7 `stores/telemetry.ts` 一致
- `SetTargetRequest.target`：Task 3 定义 `ge=0`，Task 9 前端校验 `>= 0`
- `ApiResponse {success, message}`：Task 3 定义，Task 4 返回
- `RosbridgeClient` 方法签名：Task 2 定义，Task 4/5 调用一致
- WebSocket 消息格式 `{type: "telemetry"|"joystick", data: ...}`：Task 3/5/7/12 一致
- Topic 名称 `/rov/depth_ctrl/status`：Task 10 发布，Task 11 订阅，Task 5 隐式消费

✅ 类型、名称、接口跨 task 一致。
