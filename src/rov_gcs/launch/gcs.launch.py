import os
import sys

from launch import LaunchDescription
from launch.actions import ExecuteProcess, LogInfo, RegisterEventHandler
from launch.event_handlers import OnProcessExit
from launch_ros.actions import Node


def generate_launch_description():
    # rosbridge_server — ROS ↔ 非 ROS 世界的桥梁
    rosbridge = Node(
        package='rosbridge_server',
        executable='rosbridge_websocket',
        parameters=[{
            'port': 9090,
            'address': '0.0.0.0',
        }],
        output='screen',
    )

    # SSL certs path（用 realpath 解析 symlink，避免 install/ 软链接指错路径）
    _certs_dir = os.path.join(
        os.path.dirname(os.path.realpath(__file__)), '..', 'rov_gcs', 'backend', 'certs'
    )
    _cert_file = os.path.join(_certs_dir, 'cert.pem')
    _key_file = os.path.join(_certs_dir, 'key.pem')

    # uvicorn (FastAPI + static files)
    uvicorn_args = [
        sys.executable, '-m', 'uvicorn',
        'rov_gcs.backend.main:app',
        '--host', '0.0.0.0',
        '--port', '8000',
    ]

    if os.path.isfile(_cert_file) and os.path.isfile(_key_file):
        uvicorn_args += [
            '--ssl-certfile', _cert_file,
            '--ssl-keyfile', _key_file,
        ]

    uvicorn_cmd = ExecuteProcess(
        cmd=uvicorn_args,
        output='screen',
    )

    return LaunchDescription([
        rosbridge,
        uvicorn_cmd,
        RegisterEventHandler(
            OnProcessExit(
                target_action=rosbridge,
                on_exit=[LogInfo(
                    msg='rosbridge exited, stopping web stack'
                )],
            )
        ),
    ])
