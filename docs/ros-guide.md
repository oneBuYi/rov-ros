# 常用命令速查

## 环境加载

```bash
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

## SSL 证书（HTTPS）

File System Access API（Web 上位机的文件夹选择功能）要求安全上下文（HTTPS 或 localhost）。
从其他电脑远程访问时必须启用 HTTPS，需要生成自签名证书。**证书只需生成一次**，有效期 10 年。

```bash
# 生成自签名 SSL 证书
mkdir -p src/rov_gcs/rov_gcs/backend/certs
openssl req -x509 -newkey rsa:2048 \
  -keyout src/rov_gcs/rov_gcs/backend/certs/key.pem \
  -out src/rov_gcs/rov_gcs/backend/certs/cert.pem \
  -days 3650 -nodes \
  -subj "/CN=rov-gcs"
```

> **注意**：`*.pem` 已加入 `.gitignore`，`git clone` 后需重新生成。`colcon build` 会将证书随包一起安装。

## 构建

```bash
# 构建前端（如修改了 Vue 代码）
# npm run build 生成带哈希文件名，必须再执行 colcon build 才能同步到 install 目录
cd src/rov_gcs/rov_gcs/frontend && npm run build && cd /home/jetson/whj/rov-ros && colcon build --packages-select rov_gcs --symlink-install

# 如果 colcon build 报 "No such file or directory"，是因 install 残留了旧软链接，清掉 dist 重构建
rm -rf install/rov_gcs/share/rov_gcs/frontend/dist/* && colcon build --packages-select rov_gcs --symlink-install

# 合并版：先清 dist（避免旧软链接残留），再构建，一条命令覆盖两种场景
rm -rf install/rov_gcs/share/rov_gcs/frontend/dist/* && cd src/rov_gcs/rov_gcs/frontend && npm run build && cd /home/jetson/whj/rov-ros && colcon build --packages-select rov_gcs --symlink-install

# 清理重新构建
rm -rf build/ install/ log/ && colcon build --symlink-install && source install/setup.bash

# 构建指定包
colcon build --packages-select rov_msgs --symlink-install && source install/setup.bash
colcon build --packages-select rov_control --symlink-install && source install/setup.bash
colcon build --packages-select rov_gcs --symlink-install && source install/setup.bash
colcon build --packages-select rov_bringup --symlink-install && source install/setup.bash
colcon build --packages-select rov_grid --symlink-install && source install/setup.bash
colcon build --packages-select rov_sensor --symlink-install && source install/setup.bash
```

## 启动

```bash
# 启动完整系统（MAVROS + 控制节点）
source install/setup.bash && ros2 launch rov_bringup rov.launch.py

# 启动 Web 上位机（rosbridge + FastAPI）
source install/setup.bash && ros2 launch rov_gcs gcs.launch.py

# 浏览器打开（HTTPS，首次需接受自签名证书警告）
# https://192.168.137.100:8000
```

### 单独启动各个组件

```bash
# MAVROS 飞控通信桥接（串口 Pixhawk，UDP 地面站）
ros2 run mavros mavros_node --ros-args -p fcu_url:=/dev/pixhawk:115200 -p gcs_url:="udp-b://@0.0.0.0:14551" -p system_id:=255 -p component_id:=190

# rosbridge WebSocket 服务（端口 9090）
ros2 run rosbridge_server rosbridge_websocket --ros-args -p port:=9090 -p address:=0.0.0.0

# 深度 PID 控制节点
ros2 run rov_control depth_ctrl_node

# 推力桥接节点（将控制指令转发至 MAVROS）
ros2 run rov_control adhesion_ctrl_node

# GCS 后端（FastAPI，端口 8000）
ros2 run rov_gcs gcs_backend

# 网格监测节点（泳池网格定位）
ros2 run rov_grid grid_monitor_node --ros-args --params-file src/rov_grid/config/pool_wall_grid.yaml

# 相机发布节点（MJPEG 直通，默认 /dev/video0 640x480 15fps）
ros2 run rov_sensor camera_pub_node

# UGPS 桥接节点（UDP→UART NMEA 过滤转发，默认 :52120→/dev/ttyTHS1 38400）
ros2 run rov_sensor ugps_bridge_node

# 快速启动 Web 上位机（rosbridge + uvicorn，不使用 launch）
ros2 run rosbridge_server rosbridge_websocket --ros-args -p port:=9090 -p address:=0.0.0.0 &
python3 -m uvicorn rov_gcs.backend.main:app --host 0.0.0.0 --port 8000
```

## 调试

```bash
# 查看话题列表
ros2 topic list

# 查看话题内容
# 当前相对高度（m）
ros2 topic echo /mavros/global_position/rel_alt
# MAVROS 连接状态
ros2 topic echo /mavros/state
# 深度 PID 输出
ros2 topic echo /rov/depth_ctrl/pid_output
# 定深状态
ros2 topic echo /rov/depth_ctrl/status_hold
# 航向 PID 输出
ros2 topic echo /rov/heading_ctrl/pid_output
# 定航状态
ros2 topic echo /rov/heading_ctrl/status_hold
# 摇杆指令输入
ros2 topic echo /rov/joystick_ctrl/cmd
# 发送至飞控的控制指令
ros2 topic echo /mavros/manual_control/send
# 网格行数/列数
ros2 topic echo /rov/grid/rows
ros2 topic echo /rov/grid/cols
# 网格当前行/列
ros2 topic echo /rov/grid/current_row
ros2 topic echo /rov/grid/current_col
# 网格目标行/列
ros2 topic echo /rov/grid/target_row
ros2 topic echo /rov/grid/target_col
# 是否到达目标网格
ros2 topic echo /rov/grid/in_target
# 相机图像
ros2 topic echo /rov/camera/image_raw/compressed

# 查看 service 列表
ros2 service list

# 设置深度目标（单位：米）
ros2 service call /rov/depth_ctrl/set_target rov_msgs/srv/SetTarget "{target: 2.0}"

# 切换深度保持
ros2 service call /rov/depth_ctrl/toggle_hold std_srvs/srv/Trigger

# 通过 adhesion_ctrl 切换深度保持
ros2 service call /rov/adhesion_ctrl/toggle_depth std_srvs/srv/Trigger

# 通过 adhesion_ctrl 切换航向保持
ros2 service call /rov/adhesion_ctrl/toggle_heading std_srvs/srv/Trigger

# 设定航向目标（单位：度）
ros2 service call /rov/heading_ctrl/set_target rov_msgs/srv/SetTarget "{target: 180.0}"

# 切换航向保持
ros2 service call /rov/heading_ctrl/toggle_hold std_srvs/srv/Trigger

# 设定网格目标（row, col）
ros2 service call /rov/grid/set_grid_target rov_msgs/srv/SetGridTarget "{row: 1, col: 2}"
```

## Web API

```bash
# 获取遥测快照
curl -k https://192.168.137.100:8000/api/telemetry

# 设定目标深度（m）
curl -k -X POST https://192.168.137.100:8000/api/depth/set_target -H 'Content-Type: application/json' -d '{"target": 2.0}'

# 切换定深
curl -k -X POST https://192.168.137.100:8000/api/depth/hold

# 设定目标航向（度）
curl -k -X POST https://192.168.137.100:8000/api/heading/set_target -H 'Content-Type: application/json' -d '{"target": 180}'

# 切换定航
curl -k -X POST https://192.168.137.100:8000/api/heading/hold

# WebSocket 测试（需安装 wscat: npm i -g wscat）
wscat -c wss://192.168.137.100:8000/ws
```

## 浏览器单独获取视频

`/api/video/stream` 返回 MJPEG 流（`multipart/x-mixed-replace`），无需前端界面即可在各种场景下获取视频。

### 方式一：浏览器直接打开

在浏览器地址栏输入以下 URL，即可看到实时视频流：

```
https://192.168.137.100:8000/api/video/stream
```

> 首次访问 HTTPS 自签名证书会有安全警告，点击"高级"→"继续访问"即可。

### 方式二：HTML `<img>` 标签嵌入

```html
<img src="https://192.168.137.100:8000/api/video/stream"
     alt="ROV Video Stream"
     style="width: 640px; height: 480px;" />
```

> 浏览器 `<img>` 标签原生支持 MJPEG 流，无需 JavaScript 或 WebSocket。

### 方式三：命令行工具

```bash
# wget 拉取单帧 JPEG（配合 --no-check-certificate 跳过证书验证）
wget --no-check-certificate -O frame.jpg https://192.168.137.100:8000/api/video/stream

# ffplay 实时播放
ffplay -f mjpeg https://192.168.137.100:8000/api/video/stream

# curl 持续拉取 MJPEG 流
curl -k -N https://192.168.137.100:8000/api/video/stream
```

### 方式四：Python 脚本获取

```python
import requests

# 获取单帧（MJPEG 流会持续返回数据，设置 stream=True 手动读取第一帧）
resp = requests.get("https://192.168.137.100:8000/api/video/stream",
                    stream=True, verify=False)
boundary = b"--frame\r\n"
chunks = resp.iter_content(chunk_size=1024)
body = b""
for chunk in chunks:
    body += chunk
    if b"\r\n\r\n" in body and body.startswith(boundary):
        # 去掉 boundary 和 headers，剩余部分是 JPEG 数据
        _, jpeg_data = body.split(b"\r\n\r\n", 1)
        jpeg_data = jpeg_data.rsplit(b"\r\n", 1)[0]
        with open("frame.jpg", "wb") as f:
            f.write(jpeg_data)
        break
```

