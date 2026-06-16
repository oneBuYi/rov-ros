# 第一迭代：定深控制 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在 ROS2 Foxy 中实现定深控制最小闭环，包括 PID 模块、rov_depth_ctrl 节点、rov_adhesion_ctrl 节点，通过 mavros manual_control 控制推进器。

**Architecture:** 两个 ROS2 Python 节点（`depth_ctrl` + `adhesion`）部署在水下 Jetson Nano。depth_ctrl 订阅 mavros 深度数据，PID 计算后发布 vertical_cmd；adhesion 订阅后转发为 manual_control 消息，作为后续手柄仲裁的唯一出口。

**Tech Stack:** ROS2 Foxy, rclpy, mavros, Python 3.8+, colcon

---

## 前置条件

- Jetson Nano 已安装 ROS2 Foxy + mavros
- mavros 已启动，`/mavros/global_position/rel_alt` 有数据
- 工作空间路径：`~/rov_ros`（Jetson 上）

## 文件清单（创建/未创建）

| 文件 | 操作 |
|------|------|
| `rov_ros/src/rov_msgs/package.xml` | 创建 |
| `rov_ros/src/rov_msgs/CMakeLists.txt` | 创建 |
| `rov_ros/src/rov_msgs/srv/SetTarget.srv` | 创建 |
| `rov_ros/src/rov_control/package.xml` | 创建 |
| `rov_ros/src/rov_control/setup.py` | 创建 |
| `rov_ros/src/rov_control/rov_control/__init__.py` | 创建 |
| `rov_ros/src/rov_control/rov_control/pid.py` | 创建 |
| `rov_ros/src/rov_control/rov_control/depth_ctrl_node.py` | 创建 |
| `rov_ros/src/rov_control/rov_control/adhesion_ctrl_node.py` | 创建 |
| `rov_ros/src/rov_control/config/depth_params.yaml` | 创建 |
| `rov_ros/src/rov_bringup/package.xml` | 创建 |
| `rov_ros/src/rov_bringup/launch/depth_control.launch.py` | 创建 |

---

### Task 1: 创建工作空间目录结构

**Files:**
- Create: `rov_ros/src/rov_msgs/package.xml`
- Create: `rov_ros/src/rov_msgs/CMakeLists.txt`
- Create: `rov_ros/src/rov_msgs/srv/SetTarget.srv`

- [ ] **Step 1: 创建所有需要的目录**

```bash
mkdir -p ~/rov_ros/src/rov_msgs/srv
mkdir -p ~/rov_ros/src/rov_control/rov_control
mkdir -p ~/rov_ros/src/rov_control/config
mkdir -p ~/rov_ros/src/rov_bringup/launch
```

- [ ] **Step 2: 创建 SetTarget.srv**

文件：`~/rov_ros/src/rov_msgs/srv/SetTarget.srv`

```
float64 target
---
bool success
string message
```

- [ ] **Step 3: 创建 rov_msgs 的 CMakeLists.txt**

文件：`~/rov_ros/src/rov_msgs/CMakeLists.txt`

```cmake
cmake_minimum_required(VERSION 3.5)
project(rov_msgs)

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "srv/SetTarget.srv"
)

ament_package()
```

- [ ] **Step 4: 创建 rov_msgs 的 package.xml**

文件：`~/rov_ros/src/rov_msgs/package.xml`

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>rov_msgs</name>
  <version>0.1.0</version>
  <description>Custom ROS2 messages and services for BlueROV2</description>
  <maintainer email="user@example.com">user</maintainer>
  <license>Apache-2.0</license>

  <buildtool_depend>ament_cmake</buildtool_depend>
  <build_depend>rosidl_default_generators</build_depend>
  <exec_depend>rosidl_default_runtime</exec_depend>

  <member_of_group>rosidl_interface_packages</member_of_group>

  <export>
    <build_type>ament_cmake</build_type>
  </export>
</package>
```

- [ ] **Step 5: 构建 rov_msgs 验证**

```bash
cd ~/rov_ros
colcon build --packages-select rov_msgs
source install/setup.bash
ros2 interface show rov_msgs/srv/SetTarget
```

预期输出：
```
float64 target
---
bool success
string message
```

- [ ] **Step 6: 提交**

```bash
cd ~/rov_ros
git init
git add -A
git commit -m "feat: create workspace structure and rov_msgs package"
```

---

### Task 2: 编写 PID 模块

**Files:**
- Create: `rov_ros/src/rov_control/rov_control/pid.py`
- Test: 通过 Python 直接导入验证（纯模块，无 ROS 依赖）

**Spec 要求（ref: docs/superpowers/specs/2026-06-16-rov-ros2-depth-control-design.md §1）:**
- error = setpoint - measurement（正作用）
- 首次调用返回 0.0（尚无 dt）
- 积分项梯形积分，输出域钳位抗饱和
- 微分项直接对误差求导

- [ ] **Step 1: 编写 PID 模块**

文件：`~/rov_ros/src/rov_control/rov_control/pid.py`

```python
"""离散 PID 控制器，带积分抗饱和。

从原 alg/pid.py 迁移。纯 Python 模块，无 ROS 依赖。
"""

import time


class PID:
    """离散 PID 控制器。

    error = setpoint - measurement（正作用）
    积分项使用梯形积分，在输出域钳位抗饱和。
    微分项直接对误差求导。

    Usage:
        pid = PID(kp=100, ki=40, kd=80, out_min=-100, out_max=100)
        output = pid.update(setpoint=0.5, measurement=0.3)
        pid.reset()
    """

    def __init__(self, kp, ki, kd, out_min, out_max):
        self.kp = float(kp)
        self.ki = float(ki)
        self.kd = float(kd)
        self.out_min = float(out_min)
        self.out_max = float(out_max)

        self._integral = 0.0
        self._prev_error = None
        self._prev_time = None

    def update(self, setpoint, measurement):
        """计算 PID 输出。

        Args:
            setpoint: 目标值
            measurement: 当前测量值

        Returns:
            float: 控制输出，范围 [out_min, out_max]
        """
        error = setpoint - measurement  # 正作用
        now = time.time()

        if self._prev_time is None:
            self._prev_error = error
            self._prev_time = now
            return 0.0

        dt = now - self._prev_time
        if dt <= 0:
            return 0.0

        # 比例项
        p_term = self.kp * error

        # 积分项（梯形积分）
        self._integral += self.ki * (error + self._prev_error) * dt / 2.0

        # 输出域钳位抗饱和：积分项被限制在 [out_min, out_max]
        if self._integral > self.out_max:
            self._integral = self.out_max
        elif self._integral < self.out_min:
            self._integral = self.out_min

        i_term = self._integral

        # 微分项（直接对误差求导）
        d_term = self.kd * (error - self._prev_error) / dt

        output = p_term + i_term + d_term

        # 输出钳位
        if output > self.out_max:
            output = self.out_max
        elif output < self.out_min:
            output = self.out_min

        self._prev_error = error
        self._prev_time = now

        return output

    def reset(self):
        """清除积分和微分状态。"""
        self._integral = 0.0
        self._prev_error = None
        self._prev_time = None
```

- [ ] **Step 2: 单元测试——Python 直接验证**

在 Jetson 上运行：

```bash
cd ~/rov_ros/src/rov_control
python3 -c "
import sys
sys.path.insert(0, '.')
from rov_control.pid import PID

# 测试 1: 首次调用返回 0
pid = PID(100, 40, 80, -100, 100)
assert pid.update(0.5, 0.3) == 0.0, 'First call should return 0'

# 测试 2: 正作用——测量值低于目标应输出正值
import time
time.sleep(0.1)
out = pid.update(1.0, 0.0)
assert out > 0, f'Expected positive output for sp>mv, got {out}'

# 测试 3: reset 清零
pid.reset()
assert pid.update(0.5, 0.3) == 0.0, 'After reset, first call should return 0'

# 测试 4: 输出钳位
time.sleep(0.1)
out = pid.update(1000, 0)  # 巨大误差
assert -100 <= out <= 100, f'Output {out} should be clamped within [-100,100]'

print('PID: all tests passed')
"
```

预期输出：`PID: all tests passed`

- [ ] **Step 3: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "feat: add PID module (ported from alg/pid.py)"
```

---

### Task 3: 创建 rov_depth_ctrl 节点

**Files:**
- Create: `rov_ros/src/rov_control/rov_control/depth_ctrl_node.py`
- Create: `rov_ros/src/rov_control/config/depth_params.yaml`

**Spec 要求（ref: design §2）:**
- 10 Hz Timer 控制循环
- 订阅 `/mavros/global_position/global`，取 `rel_alt * -1` 为深度
- `PID.update(target, depth)` → 发布 `std_msgs/Float32`
- hold 禁用时不发布，同时 `PID.reset()`
- 服务：`/rov/depth/set_target`（SetTarget，同时 reset）
- 服务：`/rov/depth/hold`（Trigger，toggle 启用/禁用，启用时以当前深度为目标）

- [ ] **Step 1: 编写 depth_ctrl_node.py**

文件：`~/rov_ros/src/rov_control/rov_control/depth_ctrl_node.py`

```python
"""rov_depth_ctrl — ROS2 定深控制节点。

订阅 /mavros/global_position/rel_alt 获取深度（relative_alt），
PID 计算后发布 /rov/depth/vertical_cmd。

服务:
  /rov/depth/set_target   — 设置目标深度
  /rov/depth/hold         — 切换定深保持启用/禁用
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from std_msgs.msg import Float32, Float64
from std_srvs.srv import Trigger
from rov_msgs.srv import SetTarget

from rov_control.pid import PID


class DepthCtrlNode(Node):
    def __init__(self):
        super().__init__('rov_depth_ctrl')

        # 参数
        self.declare_parameter('kp', 100.0)
        self.declare_parameter('ki', 40.0)
        self.declare_parameter('kd', 80.0)
        self.declare_parameter('out_min', -100.0)
        self.declare_parameter('out_max', 100.0)
        self.declare_parameter('control_rate', 10.0)

        # PID 控制器
        self._pid = PID(
            kp=self.get_parameter('kp').value,
            ki=self.get_parameter('ki').value,
            kd=self.get_parameter('kd').value,
            out_min=self.get_parameter('out_min').value,
            out_max=self.get_parameter('out_max').value,
        )

        self._target = None
        self._hold_enabled = False
        self._current_depth = None

        # 发布者
        self._cmd_pub = self.create_publisher(Float32, '/rov/depth/vertical_cmd', 10)

        # 订阅者：mavros/global_position/rel_alt（Float64 多少米）
        self._sub = self.create_subscription(
            Float64,
            '/mavros/global_position/rel_alt',
            self._depth_callback,
            10,
        )

        # 服务
        svc_cb = MutuallyExclusiveCallbackGroup()
        self._set_target_srv = self.create_service(
            SetTarget, '/rov/depth/set_target', self._set_target_cb, callback_group=svc_cb
        )
        self._hold_srv = self.create_service(
            Trigger, '/rov/depth/hold', self._hold_cb, callback_group=svc_cb
        )

        # 控制 Timer
        rate = self.get_parameter('control_rate').value
        self._timer = self.create_timer(1.0 / rate, self._control_step)

        self.get_logger().info('Depth controller started')

    def _depth_callback(self, msg):
        """mavros global_position/rel_alt: depth = -relative_alt"""
        self._current_depth = msg.data * -1.0

    def _control_step(self):
        """10 Hz PID 控制循环"""
        if not self._hold_enabled:
            return
        if self._current_depth is None:
            self.get_logger().warn('No depth data yet', throttle_duration_sec=5.0)
            return
        if self._target is None:
            return

        output = self._pid.update(self._target, self._current_depth)

        msg = Float32()
        msg.data = output
        self._cmd_pub.publish(msg)

    def _set_target_cb(self, request, response):
        self._target = request.target
        self._pid.reset()
        response.success = True
        response.message = f'Target depth set to {self._target:.2f}m'
        self.get_logger().info(response.message)
        return response

    def _hold_cb(self, request, response):
        self._hold_enabled = not self._hold_enabled

        if self._hold_enabled:
            if self._current_depth is not None:
                self._target = self._current_depth
            self._pid.reset()
            msg = f'Hold enabled, target={self._target}'
        else:
            self._pid.reset()
            msg = 'Hold disabled'

        response.success = True
        response.message = msg
        self.get_logger().info(msg)
        return response


def main(args=None):
    rclpy.init(args=args)
    node = DepthCtrlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 编写 depth_params.yaml**

文件：`~/rov_ros/src/rov_control/config/depth_params.yaml`

```yaml
rov_depth_ctrl:
  ros__parameters:
    kp: 100.0
    ki: 40.0
    kd: 80.0
    out_min: -100.0
    out_max: 100.0
    control_rate: 10.0
```

- [ ] **Step 3: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "feat: add rov_depth_ctrl node"
```

---

### Task 4: 编写 rov_adhesion_ctrl_node

**Files:**
- Create: `rov_ros/src/rov_control/rov_control/adhesion_ctrl_node.py`

**Spec 要求（ref: design §3）:**
- 订阅 `/rov/depth/vertical_cmd`
- 组装 manual_control: x=0, y=0, z=vertical_cmd, r=0
- toggle_depth 服务转发到 `/rov/depth/hold`
- 是 manual_control 唯一发布者

- [ ] **Step 1: 编写 adhesion_ctrl_node.py**

文件：`~/rov_ros/src/rov_control/rov_control/adhesion_ctrl_node.py`

```python
"""rov_adhesion_ctrl — ROS2 仲裁节点。

订阅 /rov/depth/vertical_cmd，转发为 /mavros/manual_control/control。
manual_control 唯一发布者，预留为手柄 + PID 仲裁汇合点。

服务:
  /rov/adhesion/toggle_depth  — 转发到 /rov/depth/hold
"""

import rclpy
from rclpy.node import Node
from rclpy.callback_groups import MutuallyExclusiveCallbackGroup

from std_msgs.msg import Float32
from std_srvs.srv import Trigger
from mavros_msgs.msg import ManualControl


class AdhesionCtrlNode(Node):
    def __init__(self):
        super().__init__('rov_adhesion_ctrl')

        # manual_control 发布者（唯一出口）
        self._mc_pub = self.create_publisher(ManualControl, '/mavros/manual_control/control', 10)

        # 订阅 depth vertical_cmd
        self._cmd_sub = self.create_subscription(
            Float32,
            '/rov/depth/vertical_cmd',
            self._vertical_cmd_callback,
            10,
        )

        # 服务：toggle_depth
        self._hold_client = self.create_client(Trigger, '/rov/depth/hold')

        svc_cb = MutuallyExclusiveCallbackGroup()
        self._toggle_srv = self.create_service(
            Trigger, '/rov/adhesion/toggle_depth', self._toggle_cb, callback_group=svc_cb
        )

        self.get_logger().info('Adhesion controller started')

    def _vertical_cmd_callback(self, msg):
        """转发 vertical_cmd → manual_control.z"""
        mc = ManualControl()
        mc.x = 0.0
        mc.y = 0.0
        mc.z = float(msg.data)
        mc.r = 0.0
        self._mc_pub.publish(mc)

    def _toggle_cb(self, request, response):
        """转发 toggle 到 /rov/depth/hold"""
        if not self._hold_client.wait_for_service(timeout_sec=2.0):
            response.success = False
            response.message = '/rov/depth/hold service not available'
            return response

        future = self._hold_client.call_async(Trigger.Request())
        rclpy.spin_until_future_complete(self, future, timeout_sec=1.0)

        if future.done() and future.result() is not None:
            response = future.result()
        else:
            response.success = False
            response.message = 'Call to /rov/depth/hold failed'

        return response


def main(args=None):
    rclpy.init(args=args)
    node = AdhesionCtrlNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
```

- [ ] **Step 2: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "feat: add rov_adhesion_ctrl node"
```

---

### Task 5: 编写 setup.py 和 package.xml（rov_control 包）

**Files:**
- Create: `rov_ros/src/rov_control/setup.py`
- Create: `rov_ros/src/rov_control/package.xml`
- Create: `rov_ros/src/rov_control/rov_control/__init__.py`

- [ ] **Step 1: 创建 package.xml**

文件：`~/rov_ros/src/rov_control/package.xml`

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>rov_control</name>
  <version>0.1.0</version>
  <description>BlueROV2 control nodes: PID, depth_ctrl, adhesion_ctrl</description>
  <maintainer email="user@example.com">user</maintainer>
  <license>Apache-2.0</license>

  <exec_depend>rclpy</exec_depend>
  <exec_depend>std_msgs</exec_depend>
  <exec_depend>std_srvs</exec_depend>
  <exec_depend>mavros_msgs</exec_depend>
  <exec_depend>rov_msgs</exec_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

- [ ] **Step 2: 创建 setup.py**

文件：`~/rov_ros/src/rov_control/setup.py`

```python
from setuptools import find_packages, setup
import os
from glob import glob

package_name = 'rov_control'

setup(
    name=package_name,
    version='0.1.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='BlueROV2 control nodes',
    license='Apache-2.0',
    entry_points={
        'console_scripts': [
            'depth_ctrl = rov_control.depth_ctrl_node:main',
            'adhesion = rov_control.adhesion_ctrl_node:main',
        ],
    },
)
```

- [ ] **Step 3: 创建 resource 目录和 marker 文件**

```bash
mkdir -p ~/rov_ros/src/rov_control/resource
touch ~/rov_ros/src/rov_control/resource/rov_control
```

- [ ] **Step 4: 创建 __init__.py**

文件：`~/rov_ros/src/rov_control/rov_control/__init__.py`

```python
"""rov_control — BlueROV2 control nodes."""
```

- [ ] **Step 5: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "feat: add rov_control package manifest and setup.py"
```

---

### Task 6: 创建 rov_bringup 包 + launch 文件

**Files:**
- Create: `rov_ros/src/rov_bringup/package.xml`
- Create: `rov_ros/src/rov_bringup/launch/depth_control.launch.py`

- [ ] **Step 1: 创建 package.xml**

文件：`~/rov_ros/src/rov_bringup/package.xml`

```xml
<?xml version="1.0"?>
<?xml-model href="http://download.ros.org/schema/package_format3.xsd" schematypens="http://www.w3.org/2001/XMLSchema"?>
<package format="3">
  <name>rov_bringup</name>
  <version>0.1.0</version>
  <description>Launch files and configuration for BlueROV2 ROS2 system</description>
  <maintainer email="user@example.com">user</maintainer>
  <license>Apache-2.0</license>

  <exec_depend>rov_control</exec_depend>

  <export>
    <build_type>ament_python</build_type>
  </export>
</package>
```

- [ ] **Step 2: 创建 depth_control.launch.py**

文件：`~/rov_ros/src/rov_bringup/launch/depth_control.launch.py`

```python
"""Launch depth control nodes with parameters.

启动 rov_depth_ctrl + rov_adhesion_ctrl。
mavros 节点单独启动。
"""

from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    """Launch depth_ctrl + adhesion_ctrl."""
    config_file = os.path.join(
        get_package_share_directory('rov_control'),
        'config', 'depth_params.yaml'
    )

    return LaunchDescription([
        Node(
            package='rov_control',
            executable='depth_ctrl',
            name='rov_depth_ctrl',
            parameters=[config_file],
            output='screen',
        ),
        Node(
            package='rov_control',
            executable='adhesion',
            name='rov_adhesion_ctrl',
            output='screen',
        ),
    ])
```

- [ ] **Step 3: 创建 resource marker**

```bash
mkdir -p ~/rov_ros/src/rov_bringup/resource
touch ~/rov_ros/src/rov_bringup/resource/rov_bringup
```

- [ ] **Step 4: 创建 setup.py（bringup 需要 ament_python）

文件：`~/rov_ros/src/rov_bringup/setup.py`

```python
from setuptools import setup
from glob import glob
import os

package_name = 'rov_bringup'

setup(
    name=package_name,
    version='0.1.0',
    packages=[],
    data_files=[
        ('share/ament_index/resource_index/packages',
            ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.py')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='user',
    maintainer_email='user@example.com',
    description='BlueROV2 bringup launch files',
    license='Apache-2.0',
    entry_points={},
)
```

- [ ] **Step 5: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "feat: add rov_bringup package with depth_control launch"
```

---

### Task 7: 构建 + 集成测试

- [ ] **Step 1: 完整构建**

```bash
cd ~/rov_ros
colcon build --symlink-install
source install/setup.bash
```

预期：所有 3 个包编译成功，无错误。

- [ ] **Step 2: 验证节点可发现**

```bash
source ~/rov_ros/install/setup.bash
ros2 pkg list | grep rov
```

预期输出：
```
rov_bringup
rov_control
rov_msgs
```

- [ ] **Step 3: 验证可执行入口**

```bash
ros2 run rov_control depth_ctrl --help
ros2 run rov_control adhesion --help
```

预期：能看到 rclpy 的通用 help 或节点启动。

- [ ] **Step 4: 启动节点并验证 ros2 工具链**

```bash
# 终端 1：启动 mavros（如果未运行）
# roslaunch mavros apm.launch fcu_url:=/dev/ttyACM0:115200

# 终端 2：启动定深节点
source ~/rov_ros/install/setup.bash
ros2 launch rov_bringup depth_control.launch.py
```

- [ ] **Step 5: 验证 topic 和服务**

```bash
source ~/rov_ros/install/setup.bash

# 检查节点
ros2 node list
# 预期：看到 rov_depth_ctrl, rov_adhesion_ctrl

# 检查服务
ros2 service list | grep depth
# 预期：
# /rov/depth/set_target
# /rov/depth/hold
# /rov/adhesion/toggle_depth

# 调用 set_target 设置目标深度 0.5m
ros2 service call /rov/depth/set_target rov_msgs/srv/SetTarget "{target: 0.5}"

# 启用 hold
ros2 service call /rov/depth/hold std_srvs/srv/Trigger

# 检查 vertical_cmd topic
ros2 topic echo /rov/depth/vertical_cmd
# 预期：看到 Float32 数据

# 检查 manual_control topic
ros2 topic echo /mavros/manual_control/control
# 预期：看到 x=0, y=0, z=<PID输出>, r=0 的消息流
```

- [ ] **Step 6: 功能验证——在水中或模拟中测试**

1. `ros2 service call /rov/depth/set_target rov_msgs/srv/SetTarget "{target: 0.5}"`
2. `ros2 service call /rov/depth/hold std_srvs/srv/Trigger`（启用）
3. 观察 `/rov/depth/vertical_cmd` 是否输出合理的 PID 控制量
4. 观察 ROV 是否向目标深度移动
5. 再次调用 `/rov/depth/hold` 切换禁用
6. 验证 `/rov/depth/vertical_cmd` 停止发布
7. 验证 `/mavros/manual_control/control.z` 归零（adhesion 不再收到数据则停止发送）

- [ ] **Step 7: 提交**

```bash
cd ~/rov_ros
git add -A
git commit -m "chore: verify integration after colcon build"
```

---

### Task 8: 深度数据源备用方案（如需要）

**已知：** `/mavros/global_position/rel_alt` 在 mavros 中由 `GLOBAL_POSITION_INT` 消息派生，如果发现 topic 无数据，可改用 `/mavros/altitude`（`mavros_msgs/Altitude`，字段 `relative`）。两者都是相对 home 的高度（米）。

无需修改代码。如需备用方案，可自行替换订阅。此 Task 仅供参考，不作为必须执行的步骤。

---

## 完成后验证清单

- [ ] `colcon build` 全部通过
- [ ] `ros2 node list` 显示 `rov_depth_ctrl` 和 `rov_adhesion_ctrl`
- [ ] `/rov/depth/set_target` 服务可调用
- [ ] `/rov/depth/hold` toggle 服务可切换启用/禁用
- [ ] 启用时 `/rov/depth/vertical_cmd` 有数据发布
- [ ] `/mavros/manual_control/control` 的 z 轴跟随 vertical_cmd
- [ ] 禁用时 vertical_cmd 停止，manual_control.z 归零
