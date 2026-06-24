# Web 上位机设计文档

**日期**：2026-06-24  
**状态**：设计完成，待实现

---

## 1. 概述

基于现有 ROV ROS2 系统，开发一个 Web 上位机（Ground Control Station），运行在 ROV 本体的 Jetson 上，操作员通过笔记本/平板浏览器访问。提供实时遥测监控、深度控制、手柄操控功能。

### 1.1 功能范围

- **遥测监控**：当前深度、目标深度、PID 输出、经纬度、偏航角
- **深度控制**：设定目标深度（set_target）、定深开关（hold）
- **手柄操控**：操作员 PC 手柄控制 ROV 水平运动（x/y/r），深度轴在定深模式下由 PID 接管
- **视频预留**：UI 预留视频窗口，当前不实现
- **不在范围**：PID 参数在线调整、数据记录/回放、多车管理

### 1.2 运行环境

- **ROV 端**：NVIDIA Jetson（ARM，Linux 4.9），ROS2 Foxy，已有 Pixhawk/ArduSub + MAVROS
- **操作员端**：任意设备的浏览器，USB 手柄
- **网络**：操作员 PC 与 Jetson 在同一局域网（网线/WiFi）

---

## 2. 架构

### 2.1 整体架构

```
┌──────────────────────────────────────────────────────────┐
│  Jetson (ROV 本体)                                       │
│                                                          │
│  Pixhawk ◄── UART ──► MAVROS ◄── topics/services ──┐   │
│                                     │                │   │
│                          rov_control 节点              │   │
│                          (depth_ctrl + adhesion)       │   │
│                                     │                │   │
│                          rosbridge_server              │   │
│                          (WebSocket :9090)             │   │
│                              ▲    ▲                    │   │
│                              │    │                    │   │
│                    ┌─────────┘    └──────────┐        │   │
│                    │                        │        │   │
│              FastAPI 后端              Vue 3 前端      │   │
│              (uvicorn :8000)          (nginx 静态托管) │   │
│              - rosbridge 客户端       - 浏览器访问     │   │
│              - REST + WebSocket         :8000 的 API │   │
│                    │                        │        │   │
│                    └────── WebSocket ───────┘        │   │
│                          实时推送遥测                  │   │
└──────────────────────────────────────────────────────────┘

操作员 PC（浏览器）── http://<jetson-ip>:8000
                   └── 手柄 (Gamepad API) ── WebSocket ──► FastAPI
```

### 2.2 三个进程

| 进程 | 角色 | 端口 |
|------|------|------|
| rosbridge_server | ROS2 ↔ WebSocket 桥接，暴露所有 topic/service | `ws://localhost:9090` |
| FastAPI (uvicorn) | BFF 层：翻译 ROS2 数据为 JSON，提供 REST + WebSocket | `http://0.0.0.0:8000` |
| nginx | 托管 Vue 3 前端静态文件，反向代理到 FastAPI | `:80` / `:8000` |

### 2.3 FastAPI（BFF 层）职责

- **翻译**：将 ROS topic（如 `/mavros/global_position/rel_alt`）整理为前端友好的 JSON（`{"depth": 1.5}`）
- **缓存**：内存中缓存最新遥测数据，前端 REST 请求立即返回
- **控制入口**：收敛所有控制操作（深度设定、定深开关、手柄指令），统一管理
- **手柄超时保护**：手柄数据超过 500ms 未更新时，自动发布全零 ManualControl，ROV 悬停

---

## 3. ROS2 接口对接

### 3.1 rosbridge 协议

FastAPI 以 WebSocket 客户端身份连接 rosbridge（`ws://localhost:9090`），使用 JSON 协议交互。

订阅 topic：
```json
{"op": "subscribe", "topic": "/mavros/global_position/rel_alt", "type": "std_msgs/Float64"}
```

调用 service：
```json
{"op": "call_service", "service": "/rov/depth_ctrl/set_target", "args": {"target": 2.0}}
```

发布 topic（手柄）：
```json
{"op": "publish", "topic": "/rov/joystick/cmd", "msg": {"x": 0, "y": 0, "z": 30.0, "r": 0}}
```

### 3.2 订阅的 Topic

| ROS2 Topic | 类型 | 用途 |
|---|---|---|
| `/mavros/global_position/rel_alt` | Float64 | 取反得到当前深度 |
| `/mavros/global_position/global` | NavSatFix | 经纬度 |
| `/mavros/global_position/compass_hdg` | Float64 | 偏航角 |
| `/rov/depth_ctrl/vertical_cmd` | Float32 | PID 输出值 |

### 3.3 调用的 Service

| ROS2 Service | 类型 | 用途 |
|---|---|---|
| `/rov/depth_ctrl/set_target` | rov_msgs/SetTarget | 设定目标深度 |
| `/rov/depth_ctrl/hold` | std_srvs/Trigger | 定深开关 |

### 3.4 发布的 Topic

| ROS2 Topic | 类型 | 用途 |
|---|---|---|
| `/rov/joystick/cmd` | mavros_msgs/ManualControl | 手柄指令（x/y/z/r） |

---

## 4. API 设计

### 4.1 REST 接口

**获取遥测快照**
```
GET /api/telemetry
→ {
    "depth": 1.5,           // 当前深度(m)，正=水面以下
    "target_depth": 2.0,    // 目标深度
    "hold_enabled": true,   // 定深是否开启
    "vertical_cmd": 45.2,   // PID 输出[-100, 100]
    "lat": 22.1234,         // 纬度
    "lon": 114.5678,        // 经度
    "yaw": 180.5            // 偏航角(度)
  }
```
目标深度和 hold 状态由 FastAPI 跟踪记录（调用 service 时更新）。

**设定目标深度**
```
POST /api/depth/set_target
body: {"target": 2.0}
→ {"success": true, "message": "Target depth set to 2.00m, hold enabled"}
```

**切换定深**
```
POST /api/depth/hold
→ {"success": true, "message": "Hold enabled at 1.52m", "hold_enabled": true}
```

### 4.2 WebSocket 接口

**遥测推送**
```
WS /ws/telemetry
→ 每 100ms 推送，数据格式同 GET /api/telemetry
→ JSON: {"type": "telemetry", "data": {...}}
```

**手柄指令**
```
WS /ws/joystick
← 前端每秒发送 ~60 次（与 Gamepad API 同步）
← JSON: {"type": "joystick", "data": {"x": 0, "y": 0, "z": 30.0, "r": 0}}
```
> 实际整合为同一个 WebSocket `/ws`，通过 type 字段区分 telemetry 和 joystick 方向

---

## 5. 节点改造

### 5.1 depth_ctrl_node 改造

新增 publish `/rov/depth_ctrl/status`（Bool），每次 hold 切换时发布：

```python
# 新增 publisher
self._hold_status_pub = self.create_publisher(Bool, 'depth_ctrl/hold_status', 10)

# _hold_cb 中
self._enabled = not self._enabled
...
msg = Bool()
msg.data = self._enabled
self._hold_status_pub.publish(msg)
```

### 5.2 adhesion_ctrl_node 改造

新增订阅 `/rov/joystick/cmd`（手柄数据）和 `/rov/depth_ctrl/status`（定深状态），合并逻辑：

```
新增订阅:
  - /rov/joystick/cmd              (ManualControl, 来自手柄)
  - /rov/depth_ctrl/status    (Bool, 来自 depth_ctrl)
已有订阅:
  - /rov/depth_ctrl/vertical_cmd   (Float32, 来自 depth_ctrl)

内部缓存:
  - joystick_x, joystick_y, joystick_z, joystick_r  (手柄最新值)
  - vertical_cmd                                      (PID 最新值)
  - hold_enabled                                      (定深最新状态)

合并逻辑（每次收到任一订阅消息时发布到 /mavros/manual_control/send）:
  manual.x = joystick_x
  manual.y = joystick_y
  manual.r = joystick_r
  manual.z = hold_enabled ? vertical_cmd : joystick_z
```
所有输入值独立缓存，任意一个更新都触发一次发布，确保指令及时刷新。


---

## 6. 前端设计

### 6.1 页面布局

单页面应用，无路由。

```
┌──────────────────────────────────────────────────────┐
│  ROV 上位机                     ● ROS   ● Hold  [关] │  ← 状态栏
├──────────────┬──────────────────┬────────────────────┤
│              │                  │                    │
│   深度仪表   │   视频预留区域    │   遥测数据         │
│   (大圆表)   │   "视频功能      │   纬度: 22.xxx     │
│              │    开发中..."    │   经度: 114.xxx    │
│   当前: 1.5m │                  │   偏航: 180.5°     │
│   目标: 2.0m │                  │   PID: 45.2        │
│              │                  │                    │
├──────────────┴──────────────────┴────────────────────┤
│  控制面板                                            │
│  目标深度: [____2.0____] [设定]   [开启定深]         │
│  🎮 手柄状态: 已连接                                  │
└──────────────────────────────────────────────────────┘
```

- **状态栏**：ROS 连接指示灯（绿/红）、Hold 状态
- **深度仪表**：圆弧仪表盘，当前深度数字大号显示，目标深度用小箭头指示
- **视频预留**：灰色占位区域，显示"视频功能开发中"
- **遥测面板**：经纬度、偏航角、PID 输出等数字
- **控制面板**：目标深度输入框 + 设定按钮 + 定深开关 + 手柄连接状态

### 6.2 组件树

```
App.vue
├── StatusBar.vue          # 连接状态灯 + Hold 状态
├── Dashboard.vue          # 主内容区 (左中右三栏)
│   ├── DepthGauge.vue     # 深度仪表盘 (圆弧 + 数字)
│   ├── VideoPlaceholder.vue  # 视频预留
│   └── TelemetryPanel.vue    # 经纬度/偏航/PID
└── ControlPanel.vue       # 目标深度输入 + 定深开关 + 手柄状态
```

### 6.3 数据流

```
FastAPI WebSocket                    Vue 3
/ws ──── telemetry ──► useWebSocket.ts ──► reactive store ──┬──► DepthGauge
     ◄── joystick  ─── useGamepad.ts    ◄── Gamepad API    ├──► TelemetryPanel
                                                           ├──► StatusBar
                                                           └──► ControlPanel

FastAPI REST              用户操作
POST /api/depth/*  ◄────── useApi.ts ◄── ControlPanel 按钮点击
```

- **useWebSocket**：连接 `/ws`，推送遥测写入 store，上传手柄状态
- **useGamepad**：封装 Gamepad API，通过 requestAnimationFrame 读取手柄数据
- **useApi**：封装 REST 调用（setTarget、toggleHold）
- **store**：Pinia reactive store，各组件只读

### 6.4 技术细节

- **构建**：Vite 打包为纯静态文件（`dist/`），Jetson 上 nginx 托管
- **开发代理**：Vite dev server proxy 转发 `/api` 和 `/ws` 到 FastAPI
- **刷新**：WebSocket 100ms 推一帧，仪表盘 CSS transition 平滑
- **断连**：WebSocket 断开 → 状态栏红灯、数值冻结、自动重连
- **手柄超时**：FastAPI 侧 500ms 没收数据 → 发布全零 ManualControl

---

## 7. 项目结构

```
rov-ros/
├── src/
│   ├── rov_msgs/              (已有，不变)
│   ├── rov_control/           (已有，小改)
│   │   ├── rov_control/
│   │   │   ├── depth_ctrl_node.py     ← 新增 publish hold_status
│   │   │   └── adhesion_ctrl_node.py  ← 新增 joystick/hold_status 订阅
│   │   └── ...
│   ├── rov_bringup/           (已有)
│   └── rov_gcs/               ← 新包：Web 上位机
│       ├── package.xml
│       ├── setup.py
│       ├── setup.cfg
│       ├── rov_gcs/
│       │   ├── __init__.py
│       │   ├── backend/
│       │   │   ├── __init__.py
│       │   │   ├── main.py           # FastAPI 入口 + 生命周期
│       │   │   ├── rosbridge.py      # rosbridge 连接管理
│       │   │   ├── models.py         # Pydantic 数据模型
│       │   │   ├── routes.py         # REST 路由
│       │   │   └── telemetry.py      # WebSocket + 遥测缓存
│       │   └── frontend/             # Vue 3 + Vite
│       │       ├── index.html
│       │       ├── package.json
│       │       ├── vite.config.ts
│       │       └── src/
│       │           ├── App.vue
│       │           ├── components/
│       │           ├── composables/
│       │           └── stores/
│       └── launch/
│           └── gcs.launch.py         # 启动 rosbridge + 后端 + nginx
```

---

## 8. 启动与部署

### 8.1 启动流程

```bash
# Jetson 开机后执行
source /opt/ros/foxy/setup.bash
source install/setup.bash

# 1. MAVROS（已有）
ros2 launch rov_bringup rov.launch.py &

# 2. 控制节点（已有，待更新）
ros2 run rov_control depth_ctrl_node &
ros2 run rov_control adhesion_ctrl_node &

# 3. Web 上位机
ros2 launch rov_gcs gcs.launch.py
#   ├─ rosbridge_server (ws://0.0.0.0:9090)
#   ├─ uvicorn (http://0.0.0.0:8000)
#   └─ nginx 托管 frontend/dist/
```

操作员 PC：浏览器打开 `http://<jetson-ip>:8000`，插手柄。

### 8.2 依赖

新增 ROS 包依赖：
- `ros-foxy-rosbridge-server` / `ros-foxy-rosbridge-suite`
- Python：`fastapi`、`uvicorn`、`websockets`、`pydantic`
- 前端：`vue`、`vite`、`pinia`、`chart.js`（如需仪表图表）
- nginx（系统包）

---

## 9. 错误处理与边界情况

| 场景 | 处理 |
|------|------|
| ROS 连接断开 | 状态栏红灯，遥测数据冻结，自动重连 |
| 手柄断连 / 浏览器切后台 | FastAPI 500ms 超时 → 发布全零 ManualControl |
| rosbridge 不可用 | FastAPI 启动时重试连接，运行时断开则自动重连并返回 error 给前端 |
| 设定负深度（无效值） | 前端输入校验（≥0），后端 Pydantic 校验 Field(ge=0) |
| 多个浏览器同时连接 | WebSocket 一对多广播遥测，控制操作以最新为准 |
| depth_ctrl 节点未启动 | FastAPI 调用 service 失败，返回 error message 给前端 |

---

## 10. 实现顺序建议

| 阶段 | 内容 | 依赖 |
|------|------|------|
| 1 | rosbridge 安装验证 + FastAPI 最小骨架（连 rosbridge、订阅一个 topic） | 无 |
| 2 | 后端完整 API（REST + WebSocket + 遥测） | 阶段 1 |
| 3 | Vue 前端骨架 + 遥测显示（仪表盘 + 数字） | 阶段 2 |
| 4 | 控制功能（set_target + hold + 前端控制面板） | 阶段 3 |
| 5 | 节点改造（depth_ctrl + adhesion_ctrl + launch 文件） | 阶段 2 |
| 6 | 手柄链路（Gamepad API → WebSocket → FastAPI → rosbridge → adhesion） | 阶段 4, 5 |
| 7 | 手柄超时保护 | 阶段 6 |
| 8 | 部署整合（launch、nginx、auto-start） | 阶段 3-7 |
