from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    mavros_node = Node(
        package='mavros',
        executable='mavros_node',
        parameters=[{
            'fcu_url': '/dev/pixhawk:115200',
            'gcs_url': 'udp-b://@0.0.0.0:14551',
            'system_id': 255,
            'component_id': 190,
        }],
        output='screen',
    )

    depth_ctrl_node = Node(
        package='rov_control',
        executable='depth_ctrl_node',
        output='screen',
    )

    heading_ctrl_node = Node(
        package='rov_control',
        executable='heading_ctrl_node',
        output='screen',
    )

    adhesion_ctrl_node = Node(
        package='rov_control',
        executable='adhesion_ctrl_node',
        output='screen',
    )

    camera_pub_node = Node(
        package='rov_sensor',
        executable='camera_pub_node',
        parameters=[{
            'device': '/dev/video0',
            'width': 640,
            'height': 480,
            'framerate': 15,
            'publish_rate': 15.0,
            'gcs_url': 'udp-b://@0.0.0.0:5600',
        }],
        output='screen',
    )

    return LaunchDescription([
        mavros_node,
        depth_ctrl_node,
        heading_ctrl_node,
        adhesion_ctrl_node,
        camera_pub_node,
    ])
