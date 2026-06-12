# BlueROV2 ROS2 移植设计文档

## 概述

将 BlueROV2 Heavy（6推进器）原有 Python MAVLink/UDP 控制程序移植到 ROS2 Foxy，运行在 Jetson Nano（水下） + 水面主机 双机架构上。

## 硬件配置

| 组件 | 型号/配置 |
|------|-----------|
| ROV | BlueROV2 Heavy（6推进器，M1-M6） |
| 飞控 | Pixhawk，固件 ArduSub |
| 伴机计算机 | Jetson Nano（JetPack 5.x / Ubuntu 20.04） |
| 飞控连接 | USB（Jetson → Pixhawk） |
| 摄像头 | USB 摄像头（暂不实现视频节点） |
| 后续传感器 | P30 测距声呐（待扩展） |
| 水面通信 | 系留缆以太网（Fathom-X） |

## 软件环境

- ROS2 Foxy（Ubuntu 20.04）
- 构建工具：colcon
- Python 3.8+

## 双机架构

```
【水下 Jetson Nano】
  roscore / DDS 节点
  ├── mavros（USB → Pixhawk，MAVLink 桥接）
  ├── rov_motor_controller（电机控制 + 守护定时器）
  └── rov_state_publisher（状态聚合）

══════ 系留缆以太网（DDS 自动发现，同一 Domain）══════

【水面主机】
  ├── rov_joystick（手柄输入，纯数据）
  ├── rov_depth_controller（PID 定深，纯计算）
  ├── rov_heading_controller（PID 定向，纯计算）
  └── rov_adhesion（聚合仲裁，唯一电机指令出口）
```

- **水下节点部署在 Jetson Nano**：与 Pixhawk 直接通信的节点
- **水面节点部署在 PC**：需要手柄硬件、人机交互的节点
- **DDS 自动发现**：同一 ROS2 Domain 下所有节点可直接通信，无需 ROS1 的 roscore 指向

## 软件包结构

```
rov_ros2_ws/src/
├── rov_bringup/              # Launch 文件 + 配置
│   ├── launch/
│   │   ├── rov_core.launch.py        # 水下核心（mavros + 状态 + 电机）
│   │   ├── rov_control.launch.py     # 水面控制（手柄 + PID + 仲裁）
│   │   └── rov_full.launch.py        # 全栈启动
│   ├── config/
│   │   ├── mavros_apm.yaml           # ArduSub mavros 配置
│   │   └── motor_params.yaml         # 电机映射 / PWM 参数
│   └── package.xml
│
├── rov_msgs/                 # 自定义消息/服务
│   ├── msg/
│   │   └── RovState.msg               # depth + yaw + 电池 + 状态
│   ├── srv/
│   │   ├── MotorCommand.srv           # arm/disarm/set_motor
│   │   └── SetTarget.srv              # 深度/航向目标
│   └── package.xml
│
├── rov_motor/                # 电机控制节点（替代 hal/motor.py + control.py 混合矩阵）
│   ├── rov_motor/
│   │   ├── __init__.py
│   │   ├── motor_controller.py        # RC override 守护线程 + 混合矩阵
│   │   └── config.py                  # SERVO 映射 / PWM 范围常量
│   └── package.xml
│
├── rov_state/                # 状态聚合节点（替代 state.py + hal/sensor.py）
│   ├── rov_state/
│   │   ├── __init__.py
│   │   └── state_publisher.py         # 订阅 mavros topics → 发布 RovState
│   └── package.xml
│
└── rov_control/              # 高层控制（替代 control.py + adhesion_ctrl/ + alg/pid.py）
    ├── rov_control/
    │   ├── __init__.py
    │   ├── pid.py                     # 离散 PID，从 alg/pid.py 迁移
    │   ├── joystick_node.py           # 手柄输入节点（纯数据提供者）
    │   ├── depth_controller.py        # 定深控制节点（纯 PID 计算）
    │   ├── heading_controller.py      # 定向控制节点（纯 PID 计算）
    │   └── adhesion_node.py           # 聚合仲裁节点（唯一电机指令出口）
    └── package.xml
```

## 数据流总览

```
rov_joystick
    │  /rov/joystick/axes          (Float32MultiArray [surge,sway,heave,yaw])
    └─ /rov/joystick/deadman       (Bool)

rov_depth_controller               rov_heading_controller
    │  /rov/ctrl/depth_output           │  /rov/ctrl/heading_output
    │  (Float32, [-100,+100])           │  (Float32, [-100,+100])
    └────────────────┬──────────────────┘
                     ▼
              rov_adhesion  (聚合仲裁)
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
  /rov/cmd_lateral  /rov/cmd_vertical
  ([surge,sway,yaw])(Float32)
        │            │
        └─────┬──────┘
              ▼
    rov_motor_controller
              │
      mavros/rc/override
              │
           Pixhawk
```

## 各节点详细设计

### 1. rov_motor_controller（电机控制节点）

**部署位置**：水下 Jetson Nano

**对应原始模块**：`hal/motor.py` + `control.py` 混合矩阵部分

**参数（motor_params.yaml）**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| pwm_min | 1100 | PWM 最小值 |
| pwm_max | 1900 | PWM 最大值 |
| pwm_neutral | 1500 | PWM 中位值 |
| pwm_scale | 400 | ±100 功率 → ±400 µs |
| motors_reversed | [3] | 物理倒装的电机 ID 列表 |
| override_rate | 10.0 | RC override 发送频率 (Hz) |
| pwm_step_max | 100 | PWM 变化率限制 (µs/step) |
| servo_mapping | {1:38, 2:34, 3:36, 4:33, 5:35, 6:37} | 电机 → SERVO 原始功能值 |
| rc_mapping | {1:4, 2:2, 3:5, 4:3, 5:6, 6:1} | 电机 → RC 通道 |
| mix_matrix | 4×3 矩阵 | 水平推进器混合矩阵 |

**混合矩阵**：

| 电机 | surge | sway | yaw |
|------|-------|------|-----|
| M1   | +1    | -1   | +1  |
| M2   | +1    | +1   | -1  |
| M3   | +1    | +1   | +1  |
| M4   | +1    | -1   | -1  |

混合后的值钳位到 [-1, +1]，乘以 pwm_scale 加上中位值得到最终 PWM。M3 倒装处理：`pwm = 2 * 1500 - pwm`。

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 发布 | `/rov/pwm_state` | 当前 6 电机 PWM 值，10 Hz |
| 订阅 | `/rov/cmd_lateral` | [surge, sway, yaw] 归一化 [-1, +1] |
| 订阅 | `/rov/cmd_vertical` | 垂直功率 [-100, +100] |
| 订阅 | `/rov/cmd_raw` | 直接 6 通道 PWM（跳过混控） |
| 服务 | `/rov/arm` | 解锁 |
| 服务 | `/rov/disarm` | 加锁 |
| 服务 | `/rov/stop` | 全电机回中位 |

**核心逻辑**：
1. 初始化时设置每个 SERVOn_FUNCTION = 1（RC 直通模式），记录原始值
2. 10 Hz Timer 持续发送 rc_channels_override，绕过 ArduSub 混控器
3. 未分配通道默认中立值 1500
4. PWM 变化率限制：`clamp(target, current - step_max, current + step_max)`
5. 销毁时恢复 SERVOn_FUNCTION 原始值 + disarm

---

### 2. rov_state_publisher（状态聚合节点）

**部署位置**：水下 Jetson Nano

**对应原始模块**：`state.py` + `hal/sensor.py`

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 订阅 | `/mavros/global_position/global` | GPS + relative_alt |
| 订阅 | `/mavros/imu/data` | IMU（四元数 → 偏航） |
| 订阅 | `/mavros/altitude` | 备用深度 |
| 订阅 | `/mavros/battery` | 电池状态 |
| 订阅 | `/mavros/state` | 飞控状态 |
| 订阅 | `/mavros/rc/in` | 遥控器输入 |
| 发布 | `/rov/state` | RovState，10 Hz |

**RovState 消息定义**：

```
std_msgs/Header header
float64 depth              # 深度(m)，0=水面，取自 relative_alt 取反
float64 yaw                # 偏航角(度) [0, 360)
float64 pitch              # 俯仰角(度)
float64 roll               # 横滚角(度)
float32 voltage            # 电池电压(V)
float32 current            # 电池电流(A)
float32 battery_remaining  # 0.0~1.0
bool armed                 # 解锁状态
string mode                # 飞控模式
bool connected             # mavros 连接状态
uint16[8] rc_channels      # 遥控器 8 通道原始值
```

**核心逻辑**：
1. 深度：`GLOBAL_POSITION_INT` 的 relative_alt 取反
2. 偏航：从 IMU 四元数计算，转换到 [0, 360)
3. 10 Hz Timer 聚合最新数据发布
4. 无数据时字段为默认值（NaN / 0 / "" / false）

---

### 3. rov_joystick（手柄输入节点）

**部署位置**：水面 PC（需 pygame + 手柄硬件）

**对应原始模块**：`adhesion_ctrl/joystick_ctrl.py` 的 JoystickReader 部分

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 发布 | `/rov/joystick/axes` | Float32MultiArray [surge, sway, heave, yaw]，归一化 [-1,+1] |
| 发布 | `/rov/joystick/deadman` | Bool，RB+LB 同时按住 |
| 服务调用 | `/rov/arm` | A 键触发 |
| 服务调用 | `/rov/disarm` | B 键触发 |
| 服务调用 | `/rov/adhesion/toggle_depth` | X 键触发 |
| 服务调用 | `/rov/adhesion/toggle_heading` | Y 键触发 |

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| dead_zone | 0.1 | 摇杆死区 |
| rate | 20.0 | 读取/发布频率 (Hz) |

**轴映射**：
- 左摇杆 Y → surge（进退）
- 左摇杆 X → yaw（偏航）
- 右摇杆 X → sway（横移）
- 右摇杆 Y → heave（升降）

**按键映射**：
- RB+LB → deadman 安全开关
- A → arm
- B → disarm
- X → 切换定深保持
- Y → 切换定向保持
- Start → 退出

---

### 4. rov_depth_controller（定深控制节点）

**部署位置**：水面 PC

**对应原始模块**：`adhesion_ctrl/depth_ctrl.py`

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 订阅 | `/rov/state` | RovState，取 depth |
| 发布 | `/rov/ctrl/depth_output` | Float32，垂直建议功率 [-100, +100] |
| 服务 | `/rov/depth/set_target` | SetTarget（depth: float64） |
| 服务 | `/rov/depth/enable` | Trigger，启用定深 |
| 服务 | `/rov/depth/disable` | Trigger，禁用定深 |

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| kp | 100.0 | 比例增益 |
| ki | 40.0 | 积分增益 |
| kd | 80.0 | 微分增益 |
| out_min | -100.0 | PID 输出下限 |
| out_max | 100.0 | PID 输出上限 |
| control_rate | 10.0 | 控制频率 (Hz) |

**核心逻辑**：
1. 10 Hz Timer：`PID.update(target, depth)` → 发布 `/rov/ctrl/depth_output`
2. `set_target` 同时 `PID.reset()`
3. PID 使用 `alg/pid.py` 移植的离散 PID，带积分抗饱和
4. depth > 0 表示在水面以下

---

### 5. rov_heading_controller（定向控制节点）

**部署位置**：水面 PC

**对应原始模块**：`adhesion_ctrl/heading_ctrl.py`

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 订阅 | `/rov/state` | RovState，取 yaw |
| 发布 | `/rov/ctrl/heading_output` | Float32，偏航建议功率 [-100, +100] |
| 服务 | `/rov/hdg/set_target` | SetTarget（yaw: float64, 0-360） |
| 服务 | `/rov/hdg/enable` | Trigger |
| 服务 | `/rov/hdg/disable` | Trigger |

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| kp | 1.0 | 比例增益 |
| ki | 0.2 | 积分增益 |
| kd | 0.5 | 微分增益 |
| out_min | -100.0 | PID 输出下限 |
| out_max | 100.0 | PID 输出上限 |
| control_rate | 10.0 | 控制频率 (Hz) |

**核心逻辑**：
1. `_angle_error(target, current)` 计算最短有符号角度差（±180°）
2. 角度差作为 PID measurement，setpoint 恒为 0
3. PID 输出直接是纠正功率
4. 10 Hz Timer 发布 `/rov/ctrl/heading_output`

---

### 6. rov_adhesion（聚合仲裁节点）

**部署位置**：水面 PC

**对应原始模块**：`adhesion_ctrl/main.py` 的 AdhesionController

**接口**：

| 类型 | 名称 | 说明 |
|------|------|------|
| 订阅 | `/rov/joystick/axes` | 手柄轴值 |
| 订阅 | `/rov/joystick/deadman` | 安全开关 |
| 订阅 | `/rov/ctrl/depth_output` | 定深建议功率 |
| 订阅 | `/rov/ctrl/heading_output` | 定向建议功率 |
| 订阅 | `/rov/state` | 用于切换时的当前 depth/yaw 值 |
| 发布 | `/rov/cmd_lateral` | Float32MultiArray [surge, sway, yaw] |
| 发布 | `/rov/cmd_vertical` | Float32 |
| 服务 | `/rov/adhesion/toggle_depth` | Trigger |
| 服务 | `/rov/adhesion/toggle_heading` | Trigger |

**参数**：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| pwm_step_max | 100 | PWM 变化率限制 (µs/step) |
| rate | 20.0 | 仲裁循环频率 (Hz) |

**仲裁逻辑**（每 20ms）：

```
surge  = joystick.axes[0]              # 始终手柄
sway   = joystick.axes[1]              # 始终手柄
heave  = depth_output  if depth_enabled  else joystick.axes[2]
yaw    = heading_output if heading_enabled else joystick.axes[3]

if not deadman → 全部归零

变化率限制 → /rov/cmd_lateral + /rov/cmd_vertical
```

**切换逻辑**：
- `toggle_depth`：以当前 `/rov/state` 的 depth 值为目标，调用 `/rov/depth/set_target` + `/rov/depth/enable`；如已启用则 disable
- `toggle_heading`：以当前 `/rov/state` 的 yaw 值为目标，调用 `/rov/hdg/set_target` + `/rov/hdg/enable`；如已启用则 disable

---

## PID 算法

`rov_control/pid.py`，从原始 `alg/pid.py` 移植，纯 Python 模块，无 ROS 依赖：

```python
class PID:
    """离散 PID，带积分抗饱和（输出域钳位）"""
    def __init__(self, kp, ki, kd, out_min, out_max):
        ...
    def update(self, setpoint, measurement) -> float:
        """error = setpoint - measurement，返回控制量"""
        ...
    def reset(self):
        """清除积分/微分状态"""
        ...
```

- error = setpoint - measurement（正作用）
- 首次调用返回 0.0（尚无 dt）
- 积分项梯形积分，输出域钳位抗饱和（`_integral` 限制在 `[out_min, out_max]`）
- 微分项直接对误差求导

---

## 原始代码映射

| 原始文件 | ROS2 对应 |
|----------|-----------|
| `hal/connection.py` | mavros 节点（原生 MAVLink 桥接，含心跳） |
| `hal/motor.py` | `rov_motor/motor_controller.py` |
| `hal/sensor.py` | mavros topics + `rov_state/state_publisher.py` |
| `hal/config.py` | `rov_bringup/config/motor_params.yaml` |
| `state.py` (ROVState) | `rov_state/state_publisher.py` + `rov_msgs/msg/RovState.msg` |
| `control.py` (ROVControl) | `rov_motor/motor_controller.py`（底层）+ `rov_control/adhesion_node.py`（高层） |
| `alg/pid.py` | `rov_control/pid.py`（原地迁移） |
| `adhesion_ctrl/pid_ctrl.py` | 功能分散到各控制节点，不再需要抽象基类 |
| `adhesion_ctrl/depth_ctrl.py` | `rov_control/depth_controller.py` |
| `adhesion_ctrl/heading_ctrl.py` | `rov_control/heading_controller.py` |
| `adhesion_ctrl/joystick_ctrl.py` | `rov_control/joystick_node.py` + `rov_control/adhesion_node.py` |
| `adhesion_ctrl/main.py` | `rov_control/adhesion_node.py` |
| `terminal.py` | 不移植（水面主机用 rviz2/rqt 替代终端 UI） |

---

## 关键设计决策

1. **ROS2 Foxy（非 Noetic）**：匹配用户 Jetson 上已安装的 ROS2 版本
2. **多机 DDS 通信（非 ROS1 roscore）**：ROS2 原生多机，无需配置 ROS_MASTER_URI
3. **一个 topic 一个发布者**：电机指令（cmd_lateral/cmd_vertical）只有 rov_adhesion 发布，避免多源冲突
4. **控制节点拆分为计算/仲裁两层**：定深/定向 → 纯计算输出建议值，rov_adhesion → 仲裁决定最终指令
5. **mavros 替代自定义 UDP 连接**：标准化 MAVLink 桥接，心跳由 mavros 原生处理
6. **终端 UI 不移植**：水面 PC 使用 ROS2 生态工具（rviz2/rqt）替代原始 ANSI 终端渲染

## 原始依赖处理

| 原始依赖 | ROS2 处理 |
|----------|-----------|
| `pymavlink` | mavros 内部使用，应用层不直接依赖 |
| `pygame`（手柄） | `rov_joystick` 节点继续使用 |
| Conda 环境 | 替换为 colcon workspace + rosdep |

## 后续扩展

- **视频流**（`rov_video` 包）：USB 摄像头驱动 + UDP 桥接 + 水面接收节点
- **P30 声呐**（`rov_sonar` 包）：声呐驱动 + 数据处理节点
- **自主导航**：可利用 ROS2 导航栈扩展
