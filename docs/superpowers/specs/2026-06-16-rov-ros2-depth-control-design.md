# BlueROV2 ROS2 移植 — 第一迭代：定深控制

## 概述

将原 BlueROV2 Python MAVLink/UDP 控制程序逐步移植到 ROS2 Foxy。第一迭代实现定深控制最小闭环：`rov_depth_ctrl` + `rov_adhesion_ctrl` 两个节点，通过 `/mavros/manual_control/control` 控制 ArduSub 混控器，替代原代码的 RC override 方案。

## 硬件配置

| 组件 | 型号/配置 |
|------|-----------|
| ROV | BlueROV2 Heavy（6推进器，M1-M6） |
| 飞控 | Pixhawk，固件 ArduSub |
| 伴机计算机 | Jetson Nano（JetPack 5.x / Ubuntu 20.04，ROS2 Foxy） |
| 飞控连接 | USB（Jetson → Pixhawk） |
| 水面通信 | 系留缆以太网（Fathom-X） |

## 软件环境

- ROS2 Foxy（Ubuntu 20.04）
- 构建工具：colcon
- Python 3.8+
- mavros 已安装并配置

## 部署架构

```
【水下 Jetson Nano】
  mavros（已运行）
  rov_depth_ctrl          ← PID 定深计算
  rov_adhesion_ctrl       ← 仲裁转发，manual_control 唯一出口

══════ 系留缆以太网（DDS 同一 Domain）══════

【水面 PC】本迭代无部署节点，后续手柄节点接入
```

深度控制闭环全在水下，水面 PC 掉线不影响定深保持。

## 包结构

```
rov_ros/src/
├── rov_bringup/              # 功能包（配置）
│   ├── launch/
│   │   └── depth_control.launch.py
│   ├── config/
│   │   └── depth_params.yaml
│   └── package.xml
│
├── rov_msgs/                 # 功能包（自定义消息）
│   ├── srv/
│   │   └── SetTarget.srv     # float64 target
│   ├── CMakeLists.txt
│   └── package.xml
│
└── rov_control/              # 功能包（Python 代码）
    ├── rov_control/
    │   ├── __init__.py
    │   ├── pid.py            # 离散 PID 模块（纯 Python）
    │   ├── depth_ctrl_node.py
    │   └── adhesion_ctrl_node.py
    ├── package.xml
    └── setup.py
```

共 3 个功能包：`rov_bringup`（配置）、`rov_msgs`（消息定义）、`rov_control`（代码 + 节点）。

## 数据流

```
【水下 Jetson Nano】
  mavros（已运行）
    /mavros/global_position/global  ──┐
    /mavros/manual_control/control  ←─┼─── 订阅
                                       │
  rov_depth_ctrl                       │
    订阅: /mavros/global_position/global│
    发布: /rov/depth/vertical_cmd       │  (std_msgs/Float32, [-100, +100])
    服务:  /rov/depth/set_target        │  (rov_msgs/SetTarget)
    服务:  /rov/depth/hold              │  (std_srvs/Trigger)
                                        │
  rov_adhesion_ctrl                     │
    订阅: /rov/depth/vertical_cmd  ◀───┘
    发布: /mavros/manual_control/control  (mavros_msgs/ManualControl)
    服务:  /rov/adhesion/toggle_depth   (std_srvs/Trigger)
```

两个节点均部署在水下 Jetson Nano。同一 ROS2 Domain 下 DDS 自动发现。

## 节点详细设计

### 1. PID 模块 (`rov_control/pid.py`)

从原始 `alg/pid.py` 直接迁移，纯 Python 模块，无 ROS 依赖。

```python
class PID:
    def __init__(self, kp, ki, kd, out_min, out_max)
    def update(self, setpoint, measurement) -> float
    def reset(self)
```

- `error = setpoint - measurement`（正作用）
- 首次调用返回 0.0（尚无 dt）
- 积分项梯形积分，输出域钳位抗饱和（`_integral` 限制在 `[out_min, out_max]`）
- 微分项直接对误差求导

### 2. rov_depth_ctrl 节点

**参数（depth_params.yaml）**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| kp | 100.0 | 比例增益 |
| ki | 40.0 | 积分增益 |
| kd | 80.0 | 微分增益 |
| out_min | -100.0 | PID 输出下限 |
| out_max | 100.0 | PID 输出上限 |
| control_rate | 10.0 | 控制频率 (Hz) |

**核心逻辑**：

1. 10 Hz Timer 触发控制循环
2. 从 `/mavros/global_position/global` 取 `relative_alt * -1` 作为当前深度（depth > 0 表示水面以下）
3. `PID.update(target, depth)` 计算控制量
4. 发布 `std_msgs/Float32` 到 `/rov/depth/vertical_cmd`
5. hold 禁用时不发布，同时 `PID.reset()` 清除积累误差

**服务**：

- `/rov/depth/set_target`（SetTarget）：设置目标深度，同时 `PID.reset()`
- `/rov/depth/hold`（Trigger）：切换定深保持启用/禁用，启用时以当前深度为目标，同时 `PID.reset()`；禁用时停止发布

### 3. rov_adhesion_ctrl 节点

**核心逻辑**：

1. 订阅 `/rov/depth/vertical_cmd`
2. 每收到一次 vertical_cmd，组装 `manual_control` 消息：x=0, y=0, z=vertical_cmd, r=0，发布到 `/mavros/manual_control/control`
3. 其他轴（x/y/r）一律置零，留待后续手柄/PID 扩展

**服务**：

- `/rov/adhesion/toggle_depth`（Trigger）：转发到 `/rov/depth/hold`

**设计意图**：adhesion 是本迭代唯一的 manual_control 发布者，预留为后续手柄 + PID 的仲裁汇合点。

## 关键设计决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 控制方式 | manual_control | ArduSub 混控足够，无需自定义混合矩阵 |
| PID 部署位置 | 水下 Jetson | 靠近 mavros 数据源，水面断连不影响定深 |
| 控制频率 | 10 Hz | 与原代码保持一致 |
| 深度数据源 | `global_position/global.rel_alt` | 直接来自 mavros，无需中间聚合节点 |
| 服务交互 | 纯 ROS2 服务 | 无内置终端 CLI，通过 `ros2 service call` 操作 |
| hold 语义 | toggle | 一个服务切换启用/停用，简洁 |

## 原始代码映射

| 原始文件 | ROS2 对应 | 说明 |
|----------|-----------|------|
| `hal/connection.py` | mavros 节点 | 心跳由 mavros 原生处理 |
| `hal/motor.py` | 不移植 | 用 manual_control 替代 RC override |
| `hal/sensor.py` | 不移植 | 直接订阅 mavros topics |
| `control.py` (ROVControl) | `rov_adhesion_ctrl_node` | 方向方法 → manual_control 轴值 |
| `alg/pid.py` | `rov_control/pid.py` | 直接迁移 |
| `adhesion_ctrl/pid_ctrl.py` | 不移植 | 抽象基类不再需要 |
| `adhesion_ctrl/depth_ctrl.py` | `rov_depth_ctrl_node` | PID 定深 |
| `adhesion_ctrl/main.py` | `rov_adhesion_ctrl_node` | 简化为转发 + 仲裁汇合点 |
| `terminal.py` | 不移植 | 纯 ROS2 服务交互，无终端 UI |

## 后续迭代

- 第二迭代：`rov_heading_ctrl_node` 定向控制
- 第三迭代：`rov_joystick_node` 手柄输入（水面 PC）
- adhesion_ctrl 逐步成为完整仲裁节点，合并手柄 + 定深 + 定向
