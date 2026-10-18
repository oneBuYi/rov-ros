#!/bin/bash

source /opt/ros/humble/setup.bash
source /home/sunrise/rov-ros/install/setup.bash

ros2 launch rov_bringup rov.launch.py &
sleep 5
ros2 launch rov_gcs gcs.launch.py &

wait
