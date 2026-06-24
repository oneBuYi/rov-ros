import sys

from launch import LaunchDescription
from launch.actions import ExecuteProcess, LogInfo, RegisterEventHandler
from launch.event_handlers import OnProcessExit


def generate_launch_description():
    # rosbridge_server
    rosbridge = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'rosbridge_server', 'rosbridge_websocket',
            '--ros-args',
            '-p', 'port:=9090',
            '-p', 'address:=0.0.0.0',
        ],
        output='screen',
    )

    # uvicorn (FastAPI + static files)
    uvicorn_cmd = ExecuteProcess(
        cmd=[
            sys.executable, '-m', 'uvicorn',
            'rov_gcs.backend.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
        ],
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
