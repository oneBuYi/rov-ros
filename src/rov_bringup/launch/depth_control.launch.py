from launch import LaunchDescription
from launch_ros.actions import Node
from ament_index_python.packages import get_package_share_directory
import os


def generate_launch_description():
    config = os.path.join(
        get_package_share_directory('rov_control'),
        'config',
        'depth_params.yaml',
    )

    depth_ctrl_node = Node(
        package='rov_control',
        executable='depth_ctrl',
        name='rov_depth_ctrl',
        parameters=[config],
        output='screen',
    )

    adhesion_ctrl_node = Node(
        package='rov_control',
        executable='adhesion',
        name='rov_adhesion_ctrl',
        output='screen',
    )

    return LaunchDescription([
        depth_ctrl_node,
        adhesion_ctrl_node,
    ])
