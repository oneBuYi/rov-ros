# 常用命令速查

## 环境加载

```bash
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

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

# 浏览器打开
# http://192.168.137.100:8000
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
ros2 run rov_grid grid_monitor_node --ros-args -p grid_config:=src/rov_grid/config/pool_wall_grid.yaml

# 相机发布节点（MJPEG，默认 /dev/video0 640x480 15fps）
ros2 run rov_sensor camera_pub_node
# 指定 UDP 转发目标
ros2 run rov_sensor camera_pub_node --ros-args -p gcs_url:=udp://192.168.1.100:5600

# H.264 UDP 转发节点（默认 /dev/video1 640x480 15fps → 192.168.3.11:5600）
ros2 run rov_sensor h264_udp_node
# 自定义参数
ros2 run rov_sensor h264_udp_node --ros-args -p host:=192.168.1.100 -p port:=5000 -p width:=1280 -p height:=720 -p framerate:=25

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
# 垂直推力输出（PWM）
ros2 topic echo /rov/depth_ctrl/vertical_pwm
# 定深状态
ros2 topic echo /rov/depth_ctrl/get_status
# 航向 PID 输出
ros2 topic echo /rov/heading_ctrl/pid_output
# 定航状态
ros2 topic echo /rov/heading_ctrl/status_hold
# 摇杆指令输入
ros2 topic echo /rov/joystick_ctrl/cmd
# 发送至飞控的控制指令
ros2 topic echo /mavros/manual_control/send
# 网格当前行
ros2 topic echo /grid/current_row
# 网格当前列
ros2 topic echo /grid/current_col
# 网格目标行
ros2 topic echo /grid/target_row
# 网格目标列
ros2 topic echo /grid/target_col
# 是否到达目标网格
ros2 topic echo /grid/in_target
# 相机图像
ros2 topic echo /camera/image_raw

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

# 设定网格目标（row, col）
ros2 service call /grid/set_grid_target rov_msgs/srv/SetGridTarget "{row: 1, col: 2}"
```

## Web API

```bash
# 获取遥测快照
curl http://localhost:8000/api/telemetry

# 设定目标深度（m）
curl -X POST http://localhost:8000/api/depth/set_target -H 'Content-Type: application/json' -d '{"target": 2.0}'

# 切换定深
curl -X POST http://localhost:8000/api/depth/hold

# 设定目标航向（度）
curl -X POST http://localhost:8000/api/heading/set_target -H 'Content-Type: application/json' -d '{"target": 180}'

# 切换定航
curl -X POST http://localhost:8000/api/heading/hold

# WebSocket 测试（需安装 wscat: npm i -g wscat）
wscat -c ws://localhost:8000/ws
```

