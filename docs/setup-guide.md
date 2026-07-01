# ROV ROS2 深度控制系统 — 从零搭建指南

本文档面向从头开始搭建 ROV（水下机器人）ROS2 深度控制系统的开发者，覆盖硬件配置、系统安装、环境搭建、项目构建与运行的完整流程。

---

## 目录

1. [硬件概述](#1-硬件概述)
2. [系统要求](#2-系统要求)
3. [网络问题](#3-网络问题)
4. [ROS2 Foxy 安装](#4-ros2-foxy-安装)
5. [MAVROS 安装](#5-mavros-安装)
6. [cv_bridge 编译安装](#6-cv_bridge-编译安装)
7. [创建工作空间并克隆项目](#7-创建工作空间并克隆项目)
8. [构建项目](#8-构建项目)
9. [硬件连接](#9-硬件连接)

---

## 1. 硬件概述

本系统基于以下硬件平台：

| 硬件 | 型号/说明 |
|------|----------|
| 机载计算机 | NVIDIA Jetson Nano（4 GB） |
| 飞控 | Pixhawk（运行 ArduSub 固件） |
| 机体 | BlueROV2 或兼容机架 |
| 连接方式 | Pixhawk 通过串口（USB-TTL）连接至 Jetson Nano，波特率 115200 |

### 系统数据流

```
Pixhawk/ArduSub → MAVROS → /mavros/global_position/rel_alt（高度）
    → RovDepthCtrlNode（PID 控制器，10 Hz）
    → /rov/depth_ctrl/vertical_pwm（垂直推力指令）
    → RovAdhesionCtrlNode（桥接节点）
    → /mavros/manual_control/send（ManualControl.z）
    → MAVROS → Pixhawk → 电机
```

---

## 2. 系统要求

本系统可运行在以下平台：

| 平台 | 系统 | 说明 |
|------|------|------|
| Jetson Nano | Ubuntu 20.04（JetPack 4.x 社区移植镜像） | 机载计算机 |
| 虚拟机（VMware） | Ubuntu 20.04 | 开发/测试环境 |

### 2.1 Jetson Nano 烧录 Ubuntu 20.04

Jetson Nano 官方支持 Ubuntu 18.04（JetPack 4.x），但 ROS2 Foxy 需要 Ubuntu 20.04。推荐使用社区移植镜像。

**手动烧录镜像**

```bash
# 1. 从 NVIDIA 官网下载 Jetson Nano 的 Ubuntu 20.04 镜像
# 2. 使用 balenaEtcher 或 dd 写入 microSD 卡（至少 64 GB）
# 3. 插入 microSD 卡到 Jetson Nano 并上电
```

### 2.2 虚拟机环境（VMware）

如果使用 VMware 虚拟机作为开发环境，需安装 open-vm-tools 以启用剪贴板共享、拖放文件、窗口自适应等功能：

```bash
sudo apt update
sudo apt install -y open-vm-tools open-vm-tools-desktop
```

安装后重启虚拟机使工具生效。

---

## 3. 网络问题

本项目的安装过程需要从境外源（GitHub、sourceforge.net 等）下载文件。如果 Jetson / 虚拟机通过 PC 的 WiFi 共享（NAT）上网，而 PC 上运行了 Clash 等代理软件，设备流量**默认不会经 Clash 代理**（WiFi 共享仅提供普通 NAT，不带透明代理），导致下载卡住。

### 3.1 局域网代理

让设备通过 PC 的局域网代理下载：

```bash
# 1. 在 PC 上确认 Clash 的 HTTP 代理端口（通常为 7897）并开启"允许局域网连接"（Allow LAN）
# 2. 在 PC 上查看局域网 IP（WiFi 共享一般为 192.168.137.1）
#    ipconfig  # Windows
#    ip addr   # Linux
# 3. 在设备上设置代理
export http_proxy=http://192.168.137.1:7897
export https_proxy=http://192.168.137.1:7897
```

之后运行需要联网的命令时，加上 `sudo -E` 保留环境变量：

```bash
sudo -E curl -sSL https://...   # sudo 时保留代理设置
sudo -E bash ./some_script.sh   # 脚本也需要代理
```

如果 PC IP 或端口不同，将 `192.168.137.1:7897` 替换为实际值。

### 3.2 rosdep 清华镜像源

国内网络访问 GitHub 可能超时，导致 `rosdep update` 失败。可使用清华镜像源：

```bash
# 1. 删除旧源（如果失败可跳过）
sudo rm -rf /etc/ros/rosdep/sources.list.d/*

# 2. 重新写入 sources（使用国内镜像）
sudo curl -o /etc/ros/rosdep/sources.list.d/20-default.list \
  https://mirrors.tuna.tsinghua.edu.cn/git/rosdistro/rosdep/sources.list.d/20-default.list

# 3. 修改 rosdep 数据源
sudo mkdir -p /etc/ros/rosdep/sources.cache
export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml
echo "export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml" >> ~/.bashrc
source ~/.bashrc

# 4. 再运行
rosdep update
```

---

## 4. ROS2 Foxy 安装

### 4.1 设置 Locale

```bash
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

### 4.2 添加 ROS2 仓库

```bash
# 确保 Ubuntu Universe 仓库已启用
sudo apt install -y software-properties-common
sudo add-apt-repository universe

# 添加 ROS2 GPG Key
sudo apt update && sudo apt install -y curl
sudo curl -sSL https://raw.githubusercontent.com/ros/rosdistro/master/ros.key -o /usr/share/keyrings/ros-archive-keyring.gpg

# 添加 ROS2 仓库到 sources.list
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/ros-archive-keyring.gpg] http://packages.ros.org/ros2/ubuntu $(lsb_release -cs) main" | sudo tee /etc/apt/sources.list.d/ros2.list > /dev/null
```

### 4.3 安装 ROS2 Foxy 基础版

```bash
sudo apt update
sudo apt install -y ros-foxy-ros-base
```

### 4.4 安装 Python 依赖

```bash
sudo apt install -y python3-rosdep python3-colcon-common-extensions
```

### 4.5 初始化 rosdep

```bash
sudo rosdep init
rosdep update
```

### 4.6 设置环境变量

将以下内容添加到 `~/.bashrc`：

```bash
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc  # 工作空间路径，按需修改
source ~/.bashrc
```

### 4.7 验证安装

```bash
# 已安装 ros-foxy-ros-base，不包含 demo 包，用以下方式验证：
echo $ROS_DISTRO
# 应输出 foxy
ros2 topic list
# 应看到 /parameter_events 和 /rosout
```

---

## 5. MAVROS 安装

MAVROS 是 ROS 与 MAVLink 飞控（如 Pixhawk）之间的通信桥接包。

```bash
sudo apt install -y ros-foxy-mavros ros-foxy-mavros-extras
```

### 安装 GeographicLib 数据集（MAVROS 依赖）

```bash
# 下载并运行安装脚本
wget https://raw.githubusercontent.com/mavlink/mavros/master/mavros/scripts/install_geographiclib_datasets.sh
sudo bash ./install_geographiclib_datasets.sh
```

---

## 6. cv_bridge 编译安装

Jetson Nano 的 JetPack 自带 OpenCV 4.2.0（含 CUDA 优化），而 apt 安装的 ros-foxy-cv-bridge 链接的是标准 x86 编译的 OpenCV 版本，ABI 不兼容，需从源码编译。

### 6.1 卸载 apt 版本

```bash
sudo apt remove ros-foxy-cv-bridge python3-cv-bridge
```

### 6.2 创建编译工作空间

```bash
mkdir -p ~/cv_bridge_ws/src
cd ~/cv_bridge_ws/src
git clone -b foxy https://github.com/ros-perception/vision_opencv.git
```

### 6.3 修复 OpenCV 4.x 兼容性问题

问题一：`module_opencv3.cpp` 包含了 OpenCV 4 已移除的 C API 头文件：

```bash
nano ~/cv_bridge_ws/src/vision_opencv/cv_bridge/src/module_opencv3.cpp
```

找到：

```cpp
#include "opencv2/core/types_c.h"
```

改为：

```cpp
#if CV_VERSION_MAJOR < 4
#include "opencv2/core/types_c.h"
#endif
```

问题二：`module.hpp` 的 `import_array()` 在 Python3 下返回类型不兼容：

```bash
nano ~/cv_bridge_ws/src/vision_opencv/cv_bridge/src/module.hpp
```

找到：

```cpp
static void * do_numpy_import()
{
  import_array();
  return nullptr;
}
```

改为：

```cpp
static void do_numpy_import()
{
  if (_import_array() < 0) {
    PyErr_Print();
    PyErr_SetString(PyExc_ImportError, "numpy.core.multiarray failed to import");
  }
}
```

### 6.4 编译安装

```bash
cd ~/cv_bridge_ws
source /opt/ros/foxy/setup.bash

colcon build \
  --packages-select cv_bridge \
  --cmake-args \
    -DPYTHON_EXECUTABLE=/usr/bin/python3 \
    -DOpenCV_DIR=/usr/lib/aarch64-linux-gnu/cmake/opencv4 \
    -DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON \
    -DCMAKE_INSTALL_RPATH=/usr/lib/aarch64-linux-gnu
```

### 6.5 配置环境变量

将以下内容添加到 `~/.bashrc`，注意顺序：

```bash
echo "export LD_PRELOAD=/usr/lib/aarch64-linux-gnu/libGLdispatch.so.0:/usr/lib/aarch64-linux-gnu/libgomp.so.1" >> ~/.bashrc
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
echo "source ~/cv_bridge_ws/install/setup.bash" >> ~/.bashrc
source ~/.bashrc
```

说明：
- `LD_PRELOAD` 预加载 `libGLdispatch.so.0` 和 `libgomp.so.1`，解决 ARM 平台 static TLS 空间不足的问题（NVIDIA GStreamer 插件如 nvv4l2decoder、nvvidconv 依赖这两个库，若未预加载会加载失败）
- `cv_bridge_ws` 需在 ROS2 之后 source，overlay 机制会优先使用自编译版本

### 6.6 验证

```bash
python3 -c "from cv_bridge import CvBridge; print('ok')"
# 应输出 ok

python3 -c "import cv_bridge; print(cv_bridge.__file__)"
# 应显示 /home/jetson/cv_bridge_ws/install/... 而非 /opt/ros/foxy/...
```

---

## 7. 创建工作空间并克隆项目

### 7.1 创建工作空间目录

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
```

### 7.2 克隆项目

```bash
# 将项目代码克隆到用户目录
cd ~
git clone https://gitee.com/oneBuYi/rov-ros.git
```

克隆后的目录结构应为：

```
~/
└── rov-ros/
    ├── src/
    │   ├── rov_msgs/       # 自定义 ROS2 接口定义
    │   ├── rov_control/    # 核心控制节点
    │   ├── rov_bringup/    # 启动文件
    │   └── rov_gcs/        # 地面站（GCS）
    └── docs/               # 文档
```

> **说明**：本项目的四个 ROS 包（`rov_msgs`、`rov_control`、`rov_bringup`、`rov_gcs`）均在 `rov-ros/src/` 目录下。

---

## 8. 构建项目

### 8.1 完整构建

```bash
cd ~/ros2_ws

# 确保 ROS2 环境已加载
source /opt/ros/foxy/setup.bash

# 构建 GCS 前端（首次需安装依赖）
cd ~/rov-ros/src/rov_gcs/rov_gcs/frontend
npm install --registry=https://registry.npmmirror.com
npm run build

# 构建所有包
cd ~/ros2_ws
colcon build --paths ~/rov-ros/src/*

# 构建成功后加载工作空间
source install/setup.bash
```

### 8.2 单独构建某个包

```bash
# 先构建消息包
colcon build --paths ~/rov-ros/src/rov_msgs

# 再构建控制包
colcon build --paths ~/rov-ros/src/rov_control

# 构建启动包
colcon build --paths ~/rov-ros/src/rov_bringup

# 构建地面站包
colcon build --paths ~/rov-ros/src/rov_gcs
```

### 8.3 清理并重新构建

```bash
rm -rf build/ install/ log/
colcon build --paths ~/rov-ros/src/*
source install/setup.bash
```

---

## 9. 硬件连接

### 9.1 Pixhawk 与 Jetson Nano 连接

Pixhawk 通过 **TELEM2** 串口连接至 Jetson Nano：

```
Pixhawk TELEM2       Jetson Nano（J41 排针）
  TX  ─────────────────→  RX（Pin 10，UART2 RX）
  RX  ─────────────────→  TX（Pin 8，UART2 TX）
  GND ─────────────────→  GND（Pin 6）
```

### 9.2 配置串口设备

```bash
# 查看串口设备
ls -la /dev/tty*

# 创建 udev 规则，使 Pixhawk 串口固定为 /dev/pixhawk
sudo vim /etc/udev/rules.d/99-pixhawk.rules
```

添加以下内容（将 `idVendor` 和 `idProduct` 替换为实际值，可通过 `lsusb` 查看）：

```
SUBSYSTEM=="tty", ATTRS{idVendor}=="0403", ATTRS{idProduct}=="6001", SYMLINK+="pixhawk", MODE="0666"
```

```bash
# 重新加载 udev 规则
sudo udevadm control --reload-rules
sudo udevadm trigger

# 添加当前用户到 dialout 组，使串口可访问
sudo usermod -a -G dialout $USER
# 注销并重新登录使生效
```

### 9.3 验证串口通信

```bash
# 拔出再插入 Pixhawk USB 线，检查设备是否出现
ls -la /dev/pixhawk
# 应显示: lrwxrwxrwx ... /dev/pixhawk -> ttyUSB0
```
