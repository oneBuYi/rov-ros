from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        parameters=[{
            'fcu_url': '/dev/pixhawk:115200',
            'gcs_url': 'udp-b://@0.0.0.0:14551',
        }],
        output='screen',
    )

    return LaunchDescription([
        mavros_node,
    ])
