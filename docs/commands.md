# 常用命令速查

## 环境加载

```bash
source /opt/ros/foxy/setup.bash
source install/setup.bash
```

## 构建

```bash
# 构建所有包
colcon build

# 构建所有包（软链接安装，修改 Python/launch/config 无需重新编译）
colcon build --symlink-install

# 构建指定包
colcon build --packages-select rov_msgs
colcon build --packages-select rov_control
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

# 单独启动 MAVROS
ros2 run mavros mavros_node --ros-args -p fcu_url:=/dev/pixhawk:115200 -p gcs_url:=udp-b://@0.0.0.0:14551

# 单独运行控制节点
ros2 run rov_control depth_ctrl_node
ros2 run rov_control adhesion_ctrl_node
```

## 调试

```bash
# 查看话题列表
ros2 topic list

# 查看话题内容
ros2 topic echo /mavros/global_position/rel_alt
ros2 topic echo /rov/depth_ctrl/vertical_cmd
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