# uv-control.md

本文件为 Claude Code (claude.ai/code) 在此仓库中工作时提供指导。
本地位置：C:\Users\hero king\Desktop\Project\uv-control

## 项目概述

PC 端 MAVLink/UDP 控制程序，用于 BlueROV2 Heavy（6 推进器）水下 ROV。通过 UDP 与运行 MAVProxy 的 Jetson 通信，Jetson 桥接至 Pixhawk/ArduSub。QGroundControl 连接同一 UDP 端点。

## 常用命令

```bash
# 测试 MAVLink 连接（心跳）
python -m hal.connection

# 交互式电机控制 CLI
python -m hal.motor

# MAVLink 监视器（RAW_IMU + ATTITUDE + GLOBAL_POSITION_INT）
python -m hal.sensor

# 处理后的状态监视器（深度 + 偏航角）
python state.py

# 高层运动控制 CLI（方向指令，power 0-100）
python control.py

# 定深控制（目标深度，单位米）
python -m adhesion_ctrl.depth_ctrl 0.5

# 定向控制（目标航向，单位度）
python -m adhesion_ctrl.heading_ctrl 90

# 手柄纯手动控制（Xbox 手柄，4-DOF，无保持）
python -m adhesion_ctrl.joystick_ctrl

# 手柄集成控制（4-DOF + 定深/定向保持）
python -m adhesion_ctrl.main
```

无测试套件、lint 工具或包管理器配置（`requirements.txt` / `pyproject.toml`）。VS Code 使用 Conda（见 `.vscode/settings.json`）。

## 目录结构

```
control.py           # ROVControl — 高层方向运动 API
state.py             # ROVState — 处理后的传感器数据（depth, yaw）
terminal.py          # 跨平台键盘输入 + Panel ANSI 面板渲染（Color / Panel / InputBuffer / dispatch）

alg/                 # 算法原语
  pid.py             # PID — 离散 PID，带积分抗饱和（输出域钳位）

hal/                 # 硬件抽象层
  config.py          # MAVLink/UDP 配置、PWM 范围、电机→RC 映射
  connection.py      # ROVConnection — UDP 监听 + 心跳守护线程
  motor.py           # MotorController — RC 直通模式电机控制
  sensor.py          # SensorReader — 多消息 MAVLink 监视器

adhesion_ctrl/       # 高层控制算法
  pid_ctrl.py        # PidController — PID 控制器抽象基类（模板方法 run()）
  depth_ctrl.py      # DepthController(PidController) — PID 定深
  heading_ctrl.py    # HeadingController(PidController) — PID 定向
  joystick_ctrl.py   # JoystickReader + JoystickController — 手柄 I/O + 纯手动控制
  main.py            # AdhesionController(JoystickController) — 手柄 + 定深/定向集成
```

## 架构

```
ROVControl (control.py)              # 高层方向 API
  ├── ROVConnection (hal/connection.py)   # UDP 连接 + 心跳守护线程
  ├── MotorController (hal/motor.py)      # RC 直通电机控制
  │     ├── arm / disarm
  │     ├── set_motor / set_all / set_group / ramp_motor
  │     └── stop / close
  └── ROVState (state.py)                # 处理后的导航数据
        └── SensorReader (hal/sensor.py)  # MAVLink 消息监视器

外部控制器（接收 ROVControl，独立使用）：
  PID (alg/pid.py)                                    # 离散 PID，所有控制器共用
  PidController (adhesion_ctrl/pid_ctrl.py)          # 抽象基类 — 统一接口 + run() 模板
    ├── DepthController (adhesion_ctrl/depth_ctrl.py)
    └── HeadingController (adhesion_ctrl/heading_ctrl.py)
  JoystickReader (adhesion_ctrl/joystick_ctrl.py)      # 纯手柄 I/O
  JoystickController (adhesion_ctrl/joystick_ctrl.py)  # 纯手动 4-DOF 控制
    └── AdhesionController (adhesion_ctrl/main.py)     # 手柄 + 定深/定向集成
```

**`ROVState`** 封装 `SensorReader`，暴露两个处理后的导航属性：`depth`（米，取自 `GLOBAL_POSITION_INT` 的 `-relative_alt`）和 `yaw`（度 [0, 360)，取自 `ATTITUDE` EKF 估计）。无数据时两者均返回 `None`。`update()` 清空传感器缓冲区。`GLOBAL_POSITION_INT` 和 `ATTITUDE` 在构造时自动注册，无需手动 `add()`。

**`ROVConnection`** 打开 UDP 监听（`udpin:0.0.0.0:14551`）并启动一个 1 Hz 的守护心跳线程，使 ArduSub 知道 GCS 在线。没有心跳，控制指令可能被拒绝或 ROV 可能触发失控保护。

**`MotorController`** 使用 RC 直通模式（`SERVOn_FUNCTION=1`）绕过 ArduSub 混控器，然后通过 `rc_channels_override_send` 直接控制电机。原始 `SERVOn_FUNCTION` 值预定义在 `hal/config.py` 的 `SERVO_FUNCTIONS` 中（{1:38, 2:34, 3:36, 4:33, 5:35, 6:37}），`close()` 时恢复。选择此方案的原因：
- `DO_SET_SERVO` 失败（"Channel N is already in use"，被混控器占用）
- `DO_MOTOR_TEST` 有 3 秒超时和 10 秒冷却
- RC 直通：无超时、无冷却，适合持续控制

**守护线程以 10 Hz 持续发送 `rc_channels_override`**——ArduSub 在约 3-5 秒无信号后会丢弃覆盖值，因此单次发送无法维持电机输出。线程在构造时启动，`close()` 时停止。所有 8 个 RC 通道都会被发送；未在电机映射中的通道默认为中立值（1500）。

**`_wait_command_ack` 会丢弃过期的 COMMAND_ACK 消息**，循环等待直到找到与期望 `command` 字段匹配的 ACK。如果不这样做，上一次指令的过期 ACK 会导致 arm/disarm 误报失败。

**`SensorReader`** 是一个仿 QGC 风格的多消息监视器。通过 `add()` 追踪一个或多个 MAVLink 消息类型（RAW_IMU、ATTITUDE、GLOBAL_POSITION_INT）。两种访问模式：控制循环中使用非阻塞的 `update()`/`get()`，或交互式显示使用阻塞的 `poll()` 配合 `run()`。每种消息有滑动窗口接收速率。扩展时需在 `sensor.py` 的 `MSG_REGISTRY`（解析器）和 `FORMATTERS`（显示）中同时添加条目——缺任何一个都会导致 `run()` 显示 "(waiting...)"。

**`DepthController`** 从 GLOBAL_POSITION_INT（`relative_alt` 取反）读取深度，通过 `ROVControl.set_vertical()` 驱动垂直推进器（M5、M6）。depth > 0 表示在 home 位置（水面）以下。使用 `alg/pid.py` 的 `PID`（默认值：Kp=100、Ki=40、Kd=80，输出限制 [-100, 100]）。两种模式：`update()` 供外部循环使用（以 10 Hz 调用），`run()` 为独立阻塞运行，带实时双行状态显示（深度/目标/PID 各项 + 输入提示；按键绑定：数字/Enter 设置目标，+/- 步进 0.1m，q/Esc 退出）。`set_target(depth)` 更改设定值并重置 PID 状态。`stop()` 将垂直推进器置为中位。`compute()` 返回 [-100, +100] 范围的垂直功率但不发送电机指令——供需要发送统一 `set_all()` 指令的外部控制器（如手柄）使用。

**`HeadingController`** 通过 `ROVControl.state.yaw` 从 ATTITUDE（EKF 估计）读取偏航角，通过 `ROVControl.set_yaw()` 驱动水平推进器（M1-M4）。航向 0-360 度，以磁北为参考。使用 `alg/pid.py` 的 `PID`（默认值：Kp=1、Ki=0.2、Kd=0.5，输出限制 [-100, 100]）。PID 设定值恒为 0（即目标误差为零），测量值为 `_angle_error(target, current)` 计算的最短有符号角度差——将角度差作为"测量值"输入 PID，使得 PID 输出直接是纠正功率。`compute()` 返回 [-100, +100] 范围的偏航功率但不发送电机指令——与需要统一 `set_all()` 的外部控制器配合使用。`run()` 提供交互式 CLI（双行状态 + 输入提示；按键绑定：数字/Enter 设置目标，+/- 步进 5 度，q/Esc 退出）。`_control_step()` 仅调用 `set_yaw()`，垂直推进器（M5-M6）保持中位，因此可与 `DepthController` 同时使用。注意：`stop()` 调用 `ROVControl.stop()` 会使所有电机回中——若需仅停止偏航而保留深度控制，直接设置 `_running = False` 即可。

**`JoystickReader`** 使用 `pygame` 读取 Xbox 风格手柄，纯数据提供者——不依赖 `ROVControl`，不发送电机指令。`read()` 返回 `JoystickState` dataclass：四个归一化轴值（surge/sway/heave/yaw，已应用死区）、deadman 布尔值（RB+LB 同时按住）、五个按钮上升沿标志（A/B/X/Y/Start）、connected 标志。自动处理 pygame 初始化、手柄检测和重连。

**`AdhesionController`** 为集成层，继承 `JoystickController`，组合 `JoystickReader` + `ROVControl` + `DepthController` + `HeadingController`。左摇杆控制进退（Y 轴）和转向（X 轴），右摇杆控制横移（X 轴）和升降（Y 轴）。通过 `ROVControl.mix_lateral()` 混控水平三轴到 M1-M4，垂直轴通过 `rov.power_to_pwm()` 转为 PWM，所有 6 电机经过变化率限制后由 `ROVControl.set_motors()` 原子性发送。按下 X 键切换定深保持（以当前深度为目标），按下 Y 键切换定向保持（以当前航向为目标）。定深/定向开启时会在终端显示实时 ANSI 状态行（目标值、误差、功率、P/I/D 各项），并支持键盘输入调整目标值（键入数字+Enter 直接设置，+/- 步进；`_kb_focus` 追踪最近切换的模式以路由键盘输入）。安全特性：RB+LB 双保险开关（同时按住才有电机输出，松开 → `rov.stop()` 回中）、PWM 变化率限制（100 µs/步，定义在基类 `JoystickController.PWM_STEP_MAX`）。A 键解锁，B 键上锁，Start 退出。`run()` 阻塞运行（20 Hz）；`update()` 为单次迭代供外部循环使用。

**电机 → SERVO → RC 映射**（来自 `docs/image.png`）：
| 电机 | SERVO | RC 通道 | 分组     |
|------|-------|---------|----------|
| M1   | 4     | RC4     | lateral  |
| M2   | 2     | RC2     | lateral  |
| M3   | 5     | RC5     | lateral  |
| M4   | 3     | RC3     | lateral  |
| M5   | 6     | RC6     | vertical |
| M6   | 1     | RC1     | vertical |

**水平推进器混合矩阵**（`control.py` 中 `MIX_MATRIX`，surge/sway/yaw 各轴在 [-1, +1]）：
| 电机 | surge | sway | yaw  |
|------|-------|------|------|
| M1   | +1    | -1   | +1   |
| M2   | +1    | +1   | -1   |
| M3   | +1    | +1   | +1   |
| M4   | +1    | -1   | -1   |

混合后的值再钳位到 [-1, +1]，乘以 `PWM_SCALE`（400 µs）加上中立值 1500 得到最终 PWM。此矩阵确保了四台水平推进器的推力矢量正确合成进退、横移、偏航三个自由度的运动。

## 依赖

- `pymavlink` — MAVLink 协议库
- `pygame` — 游戏手柄/摇杆输入（仅 `joystick_ctrl.py` 使用）
- Conda 环境（见 `.vscode/settings.json`）

## 硬件配置 (`hal/config.py`)

- Jetson IP：`192.168.137.72`，MAVProxy UDP 端口：`14551`
- 源端：system=255/comp=1（GCS PC），目标端：system=1/comp=1（Pixhawk/ArduSub）
- PWM 范围：1100–1900，中立 1500
- 心跳超时：5s，指令重试次数：3
- `MOTORS_REVERSED = [3]` — M3 物理上倒装；其 PWM 需以 1500 为轴镜像翻转，使逻辑"前进"对应正确的物理方向。`set_motor`/`set_all`/`set_group` 会自动应用此修正。

## `ROVControl` (control.py)

高层方向运动 API，内部组合 hal 各模块。管理连接、电机和传感器的生命周期。

```python
with ROVControl() as rov:
    rov.arm()
    rov.forward(power=50)     # 进退前进
    rov.backward(power=50)    # 进退后退
    rov.strafe_right(30)      # 横移右移
    rov.strafe_left(30)       # 横移左移
    rov.turn_left(50)         # 偏航逆时针
    rov.turn_right(50)        # 偏航顺时针
    rov.ascend(30)            # 上浮（PWM < 中位）
    rov.descend(50)           # 下潜（PWM > 中位）
    rov.stop()
    rov.disarm()
```

方向方法使用 [0, 100] 范围的 `power` 参数（默认 50）。后台 RC 流会维持最后一次指令，直到调用 `stop()` 或其他方向方法。通过 `rov.state` 暴露 `depth` 和 `yaw` 属性。

对外部控制器提供的公共工具方法：
- `power_to_pwm(power, scale)` — `@staticmethod`，将 [-100, +100] 功率转为 PWM 值。默认 `scale=PWM_SCALE=400`，即 ±100 功率对应 ±400 µs 偏离中立值
- `mix_lateral(surge, sway, yaw)` — 将归一化轴值按混合矩阵计算为 M1-M4 的 PWM 列表，仅计算不发指令
- `set_motors(lateral_pwms, vertical_pwm)` — 原子性发送全部 6 个电机指令

## 关键模式

- `ROVControl` 是推荐的入口——它在内部组装连接、电机和传感器。使用 `with ROVControl() as rov:` 以自动清理。
- `MotorController` 是上下文管理器——始终使用 `with MotorController(rov) as mc:` 以确保退出时恢复 SERVOn_FUNCTION。
- 电机 ID 从 1 开始；RC 通道索引内部从 0 开始。
- `set_group("vertical" | "lateral" | "all", pwm)` 按逻辑分组控制推进器。
- `ramp_motor(n, target, steps, delay)` 为单个电机提供平滑过渡。
- `mc.pwm_state` 返回 `{motor_id: pwm}` 字典用于诊断；`mc.print_state()` 打印格式化表格。
- `PID` 位于 `alg/pid.py`——`DepthController` 和 `HeadingController` 均导入使用。使用 `PID(kp, ki, kd, out_min, out_max)` 构造。每步调用 `update(setpoint, measurement)`；`reset()` 清除积分/微分状态。
- `PID.update()` 计算 `error = setpoint - measurement`（正作用）。首次调用返回 0.0（尚无 dt）。积分项使用梯形积分并在输出域做钳位抗饱和（`_integral` 被限制在 `[out_min, out_max]`），微分项直接对误差求导。
- `PidController` 位于 `adhesion_ctrl/pid_ctrl.py` — 所有 PID 控制器的抽象基类。定义统一接口：`update()`（单次迭代）、`stop()`（安全停机）、`set_target()`（设定目标）、`target` 属性、`_status_lines()`（ANSI 状态行）。子类必须实现类常量 `CTRL_LABEL`（`'DEPTH'` | `'HDG'`）和 4 个抽象成员（`_motor_data()`、`pid_terms`、`_current_value()`、`_status_lines()`）。`run()` 为模板方法，使用 `Panel.compact()` + `command_prompt` 渲染 6 行 ANSI 面板 + 键盘输入处理。新增控制器只需继承并实现抽象成员 + 覆盖钩子方法（`_prompt_label`、`_print_startup`、`_print_help`）即可获得完整 CLI 交互能力。
- `InputBuffer` 位于 `terminal.py` — 非阻塞键盘数字输入缓冲器。封装键入缓冲、退格、Enter 确认、+/- 步进、Esc/q 退出等逻辑。`poll()` 返回 `None`（无操作）、`'\x1b'`（退出信号）、`'+step'`/`'-step'`（步进信号）或确认的字符串值。`dispatch(buf, on_quit, on_step, on_confirm)` 封装 poll→回调分发模板。
- `Menu` 位于 `terminal.py` — 单级交互式键盘菜单。显示标题横幅和编号选项，阻塞直到用户选择有效选项，返回选项的 key。`show()` 在非终端环境下自动返回首选项。
- `CLI` 位于 `terminal.py` — 阻塞式命令 REPL，支持声明式命令注册（`add()`）、别名、帮助文本（`set_help()`），`?`/`help` 内建命令。供各处 CLI 调试入口使用。
- `Panel` 位于 `terminal.py` — 无状态 ANSI 面板渲染器。`Panel.full()` 返回 11 行完整面板（深度行/航向行/摇杆轴/电机/状态），`Panel.compact()` 返回 7 行简化面板（控制行/电机/状态），`Panel.command_prompt(label, buf)` 返回命令输入提示行。宽度默认 60 列，通过 dict 参数传入数据，纯字符串输出。各控制器在 `run()` 主循环中调用 Panel → `sys.stdout.write("\033[N}A")` 光标上移重绘。
- 所有控制器 docstring 遵循"用法(静态) / `---` / 键盘交互(动态)"模板。
- `JoystickReader` 为纯手柄 I/O，返回 `JoystickState` dataclass。`JoystickController` 为纯手动 4-DOF 控制，无 PID 保持，可单独运行 (`python -m adhesion_ctrl.joystick_ctrl`)。`AdhesionController` 继承 `JoystickController`，组合手柄 + 定深/定向，是后者的超集。两者均通过 `ROVControl` 的 `mix_lateral()`、`power_to_pwm()`、`set_motors()` 统一发送 6 个电机指令，变化率限制（`PWM_STEP_MAX=100`）在基类 `JoystickController` 中定义，保险开关回中调用 `rov.stop()`。
- `DepthController.compute()` 返回 [-100, +100] 范围的垂直功率——外部控制器在自行管理统一电机指令时用它替代 `update()`。
- `HeadingController.compute()` 返回 [-100, +100] 范围的偏航功率——与手柄进退/横移和深度垂直 PWM 合并到统一的 `set_all()` 调用。
- `HeadingController` 的 `set_yaw()` 内部调用 `_apply_lateral()`，它会保留当前垂直 PWM——因此定深和定向可以同时工作。
- `adhesion_ctrl/__init__.py` 条件导入控制器——若依赖项缺失（`pygame`、`adhesion_ctrl.depth_ctrl`），`JoystickController` 和 `HeadingController` 会静默跳过。`DepthController` 始终可用。
- `hal/__init__.py` 从 `config.py` 导出所有常量，从子模块导出 `ROVConnection`、`MotorController`、`SensorReader` 和 `sensor_run`。
