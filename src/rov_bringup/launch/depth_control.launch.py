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
