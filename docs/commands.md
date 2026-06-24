# 常用命令速查

## 环境加载

```bash
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

## 构建

```bash
# 构建前端（如修改了 Vue 代码）
cd src/rov_gcs/rov_gcs/frontend
npm install --registry=https://registry.npmmirror.com
npm run build
cd /home/jetson/whj/rov-ros

# 构建所有包
colcon build

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

# 快速启动 Web 上位机（rosbridge + uvicorn，不使用 launch）
ros2 run rosbridge_server rosbridge_websocket --ros-args -p port:=9090 -p address:=0.0.0.0 &
python3 -m uvicorn rov_gcs.backend.main:app --host 0.0.0.0 --port 8000

# 浏览器打开
# http://<jetson-ip>:8000
```

## 调试

```bash
# 查看话题列表
ros2 topic list

# 查看话题内容
ros2 topic echo /mavros/global_position/rel_alt
ros2 topic echo /rov/depth_ctrl/vertical_cmd
ros2 topic echo /rov/depth_ctrl/status
ros2 topic echo /rov/joystick/cmd
ros2 topic echo /mavros/manual_control/send

# 查看 service 列表
ros2 service list

# 设置深度目标（单位：米）
ros2 service call /rov/depth_ctrl/set_target rov_msgs/srv/SetTarget "{target: 2.0}"

# 切换深度保持
ros2 service call /rov/depth_ctrl/hold std_srvs/srv/Trigger

# 通过 adhesion_ctrl 切换深度保持
ros2 service call /rov/adhesion_ctrl/toggle_depth std_srvs/srv/Trigger
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

# WebSocket 测试（需安装 wscat: npm i -g wscat）
wscat -c ws://localhost:8000/ws
```
