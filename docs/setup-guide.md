# ROV ROS2 深度控制系统 — 从零搭建指南

本文档面向从头开始搭建 ROV（水下机器人）ROS2 深度控制系统的开发者，覆盖硬件配置、系统安装、环境搭建、项目构建与运行的完整流程。

---

## 目录

1. [硬件概述](#1-硬件概述)
2. [Jetson Nano 系统安装](#2-jetson-nano-系统安装)
3. [ROS2 Foxy 安装](#3-ros2-foxy-安装)
4. [MAVROS 安装](#4-mavros-安装)
5. [创建工作空间并克隆项目](#5-创建工作空间并克隆项目)
6. [构建项目](#6-构建项目)
7. [硬件连接](#7-硬件连接)

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
    → /rov/depth_ctrl/vertical_cmd（垂直推力指令）
    → RovAdhesionCtrlNode（桥接节点）
    → /mavros/manual_control/send（ManualControl.z）
    → MAVROS → Pixhawk → 电机
```

---

## 2. Jetson Nano 系统安装

### 2.1 烧录 Ubuntu 20.04

Jetson Nano 官方支持 Ubuntu 18.04（JetPack 4.x），但 ROS2 Foxy 需要 Ubuntu 20.04。推荐使用社区移植镜像。

**手动烧录镜像**

```bash
# 1. 从 NVIDIA 官网下载 Jetson Nano 的 Ubuntu 20.04 镜像
# 2. 使用 balenaEtcher 或 dd 写入 microSD 卡（至少 64 GB）
# 3. 插入 microSD 卡到 Jetson Nano 并上电
```

---

## 3. ROS2 Foxy 安装

### 3.1 设置 Locale

```bash
sudo apt update && sudo apt install -y locales
sudo locale-gen en_US en_US.UTF-8
sudo update-locale LC_ALL=en_US.UTF-8 LANG=en_US.UTF-8
export LANG=en_US.UTF-8
```

### 3.2 添加 ROS2 仓库

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

### 3.3 安装 ROS2 Foxy 基础版

```bash
sudo apt update
sudo apt install -y ros-foxy-ros-base
```

### 3.4 安装 Python 依赖

```bash
sudo apt install -y python3-rosdep python3-colcon-common-extensions
```

### 3.5 初始化 rosdep

```bash
sudo rosdep init
rosdep update
```

> **常见问题**：国内网络访问 GitHub 可能超时，导致 `rosdep update` 失败。
> 可使用清华镜像源解决：
> ```bash
> # 1. 删除旧源（如果失败可跳过）
> sudo rm -rf /etc/ros/rosdep/sources.list.d/*
> 
> # 2. 重新写入 sources（使用国内镜像）
> sudo curl -o /etc/ros/rosdep/sources.list.d/20-default.list \
>   https://mirrors.tuna.tsinghua.edu.cn/git/rosdistro/rosdep/sources.list.d/20-default.list
> 
> # 3. 修改 rosdep 数据源
> sudo mkdir -p /etc/ros/rosdep/sources.cache
> export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml
> echo "export ROSDISTRO_INDEX_URL=https://mirrors.tuna.tsinghua.edu.cn/rosdistro/index-v4.yaml" >> ~/.bashrc
> source ~/.bashrc
> 
> # 4. 再运行
> rosdep update
> ```

### 3.6 设置环境变量

将以下内容添加到 `~/.bashrc`：

```bash
echo "source /opt/ros/foxy/setup.bash" >> ~/.bashrc
echo "source ~/ros2_ws/install/setup.bash" >> ~/.bashrc  # 工作空间路径，按需修改
source ~/.bashrc
```

### 3.7 验证安装

```bash
# 已安装 ros-foxy-ros-base，不包含 demo 包，用以下方式验证：
echo $ROS_DISTRO
# 应输出 foxy
ros2 topic list
# 应看到 /parameter_events 和 /rosout
```

---

## 4. MAVROS 安装

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

> **网络问题**：该脚本需要从 `sourceforge.net` 等境外源下载数据文件。如果 Jetson
> 通过 PC 的 WiFi 共享（NAT）上网，而 PC 上运行了 Clash 等代理软件，Jetson 的流量
> **默认不会经 Clash 代理**（WiFi 共享仅提供普通 NAT，不带透明代理），导致下载卡住。
>
> **解决方案**：让 Jetson 通过 PC 的局域网代理下载。
>
> ```bash
> # 1. 在 PC 上确认 Clash 的 HTTP 代理端口（通常为 7890）并开启"允许局域网连接"（Allow LAN）
> # 2. 在 PC 上查看局域网 IP（WiFi 共享一般为 192.168.137.1）
> #    ipconfig
> # 3. 在 Jetson 上设置代理后运行脚本
> export http_proxy=http://192.168.137.1:7890
> export https_proxy=http://192.168.137.1:7890
> sudo -E bash ./install_geographiclib_datasets.sh
> ```
>
> 如果 PC IP 或端口不同，将 `192.168.137.1:7890` 替换为实际值。

---

## 5. 创建工作空间并克隆项目

### 5.1 创建工作空间目录

```bash
mkdir -p ~/ros2_ws/src
cd ~/ros2_ws
```

### 5.2 克隆项目

```bash
# 将项目代码克隆到 src 目录
cd ~/ros2_ws/src
git clone <your-repo-url> rov-ros
```

克隆后的目录结构应为：

```
~/ros2_ws/
└── src/
    └── rov-ros/
        ├── src/
        │   ├── rov_msgs/       # 自定义 ROS2 接口定义
        │   ├── rov_control/    # 核心控制节点
        │   └── rov_bringup/    # 启动文件
        └── docs/               # 文档
```

> **说明**：本项目的三个 ROS 包（`rov_msgs`、`rov_control`、`rov_bringup`）均在 `rov-ros/src/` 目录下。构建时需确保 `colcon` 能发现这些包。

### 5.3 设置软链接（推荐方式）

为了让 colcon 能正确发现这些包，有两种方式：

**方式一：软链接**

```bash
cd ~/ros2_ws/src
ln -s rov-ros/src/rov_msgs .
ln -s rov-ros/src/rov_control .
ln -s rov-ros/src/rov_bringup .
```

**方式二：直接在 ros2_ws 根目录操作**

```bash
cd ~/ros2_ws
git clone <your-repo-url> src/rov-ros
# 然后创建软链接
ln -s rov-ros/src/rov_msgs src/
ln -s rov-ros/src/rov_control src/
ln -s rov-ros/src/rov_bringup src/
```

### 5.4 安装 ROS 依赖

```bash
cd ~/ros2_ws
rosdep install --from-paths src --ignore-src -r -y
```

---

## 6. 构建项目

### 6.1 完整构建

```bash
cd ~/ros2_ws

# 确保 ROS2 环境已加载
source /opt/ros/foxy/setup.bash

# 构建所有包
colcon build

# 构建成功后加载工作空间
source install/setup.bash
```

### 6.2 单独构建某个包

```bash
# 先构建消息包
colcon build --packages-select rov_msgs

# 再构建控制包
colcon build --packages-select rov_control

# 构建启动包
colcon build --packages-select rov_bringup
```

### 6.3 清理并重新构建

```bash
rm -rf build/ install/ log/
colcon build
source install/setup.bash
```

---

## 7. 硬件连接

### 7.1 Pixhawk 与 Jetson Nano 连接

Pixhawk 通过 **TELEM2** 串口连接至 Jetson Nano：

```
Pixhawk TELEM2       Jetson Nano（J41 排针）
  TX  ─────────────────→  RX（Pin 10，UART2 RX）
  RX  ─────────────────→  TX（Pin 8，UART2 TX）
  GND ─────────────────→  GND（Pin 6）
```

### 7.2 配置串口设备

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

### 7.3 验证串口通信

```bash
# 拔出再插入 Pixhawk USB 线，检查设备是否出现
ls -la /dev/pixhawk
# 应显示: lrwxrwxrwx ... /dev/pixhawk -> ttyUSB0
```
