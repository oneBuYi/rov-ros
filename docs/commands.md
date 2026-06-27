# 常用命令速查

## 环境加载

```bash
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

## 构建

```bash
# 构建前端（如修改了 Vue 代码）
# 注意：npm run build 生成带哈希的文件名，必须再执行 colcon build
# 才能将新的 JS/CSS 文件同步到 install 目录，否则页面会空白
cd src/rov_gcs/rov_gcs/frontend
npm install --registry=https://registry.npmmirror.com
npm run build
cd /home/jetson/whj/rov-ros
colcon build --packages-select rov_gcs

# 构建所有包
rm -rf build/ install/ log/ && colcon build --symlink-install

# 构建指定包
colcon build --packages-select rov_msgs
colcon build --packages-select rov_control
colcon build --packages-select rov_gcs
colcon build --packages-select rov_bringup

# 清理重新构建
rm -rf build/ install/ log/
colcon build
source install/setup.bash
```

## 启动

```bash
# 启动完整系统（MAVROS + 控制节点）
ros2 launch rov_bringup rov.launch.py

# 启动 Web 上位机（rosbridge + FastAPI）
ros2 launch rov_gcs gcs.launch.py

# 单独启动各个组件
ros2 run rosbridge_server rosbridge_websocket --ros-args -p port:=9090 -p address:=0.0.0.0
ros2 run rov_control depth_ctrl_node
ros2 run rov_control adhesion_ctrl_node
ros2 run rov_gcs gcs_backend
ros2 run rov_sensor camera_pub_node

# 快速启动 Web 上位机（rosbridge + uvicorn，不使用 launch）
ros2 run rosbridge_server rosbridge_websocket --ros-args -p port:=9090 -p address:=0.0.0.0 &
python3 -m uvicorn rov_gcs.backend.main:app --host 0.0.0.0 --port 8000

# 浏览器打开
# http://192.168.137.72:8000
```

## 调试

```bash
# 查看话题列表
ros2 topic list

# 查看话题内容
ros2 topic echo /mavros/global_position/rel_alt
ros2 topic echo /rov/depth_ctrl/vertical_pwm
ros2 topic echo /rov/depth_ctrl/get_status
ros2 topic echo /rov/heading_ctrl/pid_output
ros2 topic echo /rov/heading_ctrl/status_hold
ros2 topic echo /rov/joystick/cmd
ros2 topic echo /mavros/manual_control/send

# 查看 service 列表
ros2 service list

# 设置深度目标（单位：米）
ros2 service call /rov/depth_ctrl/set_target rov_msgs/srv/SetTarget "{target: 2.0}"

# 切换深度保持
ros2 service call /rov/depth_ctrl/toggle_hold std_srvs/srv/Trigger

# 通过 adhesion_ctrl 切换深度保持
ros2 service call /rov/adhesion_ctrl/toggle_depth std_srvs/srv/Trigger

# 设定航向目标（单位：度）
ros2 service call /rov/heading_ctrl/set_target rov_msgs/srv/SetTarget "{target: 180.0}"

# 切换航向保持
ros2 service call /rov/heading_ctrl/toggle_hold std_srvs/srv/Trigger
```

### 运行相机发布节点（MJPEG）

```bash
# 默认配置（/dev/video0, 640x480, 15fps）
ros2 run rov_sensor camera_pub_node

# 指定设备和 UDP 转发（MJPEG 裸流）
ros2 run rov_sensor camera_pub_node --ros-args -p gcs_url:=udp://192.168.1.100:5600
```

### MJPEG UDP 视频流接收（与 camera_pub_node 配合）

```bash
# GStreamer 接收（PC 端）
gst-launch-1.0 udpsrc port=5600 ! multipartdemux ! jpegdec ! videoconvert ! autovideosink

# OpenCV + GStreamer 后端接收
python3 -c "
import cv2
pipeline = 'udpsrc port=5600 ! multipartdemux ! jpegdec ! videoconvert ! appsink'
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
while True:
    ret, frame = cap.read()
    if ret:
        cv2.imshow('ROV Camera', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
"
```

### 运行 H.264 UDP 转发节点

```bash
# 默认配置（/dev/video1, 640x480, 15fps, → 192.168.3.11:5600）
ros2 run rov_sensor h264_udp_node

# 自定义目标地址和端口
ros2 run rov_sensor h264_udp_node --ros-args -p host:=192.168.1.100 -p port:=5000

# 自定义分辨率和帧率
ros2 run rov_sensor h264_udp_node --ros-args -p width:=1920 -p height:=1080 -p framerate:=30

# 组合自定义参数
ros2 run rov_sensor h264_udp_node --ros-args \
  -p device:=/dev/video1 \
  -p width:=1280 -p height:=720 -p framerate:=25 \
  -p host:=192.168.3.11 -p port:=5600
```

### H.264 RTP 视频流接收（与 h264_udp_node 配合）

```bash
# GStreamer 接收（PC 端）
gst-launch-1.0 udpsrc port=5600 \
  caps="application/x-rtp,media=video,payload=96,encoding-name=H264" ! \
  rtph264depay ! h264parse ! avdec_h264 ! videoconvert ! autovideosink

# OpenCV + GStreamer 后端接收
python3 -c "
import cv2
pipeline = (
    'udpsrc port=5600 '
    'caps=\"application/x-rtp,media=video,payload=96,encoding-name=H264\" ! '
    'rtph264depay ! h264parse ! avdec_h264 ! '
    'videoconvert ! video/x-raw,format=BGR ! '
    'appsink drop=true max-buffers=2'
)
cap = cv2.VideoCapture(pipeline, cv2.CAP_GSTREAMER)
if not cap.isOpened():
    print('Failed to open UDP RTP stream')
    exit(1)
while True:
    ret, frame = cap.read()
    if not ret:
        continue
    cv2.imshow('ROV H.264 Stream', frame)
    if cv2.waitKey(1) & 0xFF == ord('q'):
        break
cap.release()
cv2.destroyAllWindows()
"

# ffplay 接收（需先创建 SDP 文件 stream.sdp）
cat > /tmp/stream.sdp << 'EOF'
v=0
m=video 5600 RTP/AVP 96
c=IN IP4 0.0.0.0
a=rtpmap:96 H264/90000
EOF
ffplay -protocol_whitelist file,udp,rtp /tmp/stream.sdp
```

## Web API

```bash
# 获取遥测快照
curl http://localhost:8000/api/telemetry

# 设定目标深度
curl -X POST http://localhost:8000/api/depth/set_target \
  -H 'Content-Type: application/json' \
  -d '{"target": 2.0}'

# 切换定深
curl -X POST http://localhost:8000/api/depth/hold

# 设定目标航向
curl -X POST http://localhost:8000/api/heading/set_target \
  -H 'Content-Type: application/json' \
  -d '{"target": 180}'

# 切换定航
curl -X POST http://localhost:8000/api/heading/hold

# WebSocket 测试（需安装 wscat: npm i -g wscat）
wscat -c ws://localhost:8000/ws
```

