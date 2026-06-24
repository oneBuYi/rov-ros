import os
import sys

from launch import LaunchDescription
from launch.actions import (
    ExecuteProcess,
    LogInfo,
    OpaqueFunction,
    RegisterEventHandler,
)
from launch.event_handlers import OnProcessExit


def _launch_web_stack(context, *args, **kwargs):
    """Launch rosbridge, uvicorn, and nginx."""
    actions = []

    # 1. rosbridge_server
    rosbridge = ExecuteProcess(
        cmd=[
            'ros2', 'run', 'rosbridge_server', 'rosbridge_websocket',
            '--ros-args',
            '-p', 'port:=9090',
            '-p', 'address:=0.0.0.0',
        ],
        output='screen',
    )
    actions.append(rosbridge)

    # 2. uvicorn (FastAPI backend)
    uvicorn_cmd = ExecuteProcess(
        cmd=[
            sys.executable, '-m', 'uvicorn',
            'rov_gcs.backend.main:app',
            '--host', '0.0.0.0',
            '--port', '8000',
        ],
        output='screen',
    )
    actions.append(uvicorn_cmd)

    # 3. nginx (serve frontend static files)
    frontend_dist = os.path.join(
        os.path.dirname(__file__),
        '..', 'rov_gcs', 'frontend', 'dist'
    )
    # Ensure the path exists
    if not os.path.isdir(frontend_dist):
        # Fallback: try installed share path
        frontend_dist = os.path.join(
            os.path.dirname(__file__),
            '..', '..', '..', '..', 'share', 'rov_gcs', 'frontend', 'dist'
        )

    nginx_conf = os.path.join('/tmp', 'rov_gcs_nginx.conf')
    with open(nginx_conf, 'w') as f:
        f.write(f"""
worker_processes 1;
pid /tmp/rov_gcs_nginx.pid;
error_log /tmp/rov_gcs_nginx_error.log;
events {{ worker_connections 64; }}
http {{
    access_log /tmp/rov_gcs_nginx_access.log;
    server {{
        listen 80;
        location / {{
            root {frontend_dist};
            index index.html;
            try_files $uri $uri/ /index.html;
        }}
        location /api {{
            proxy_pass http://127.0.0.1:8000;
        }}
        location /ws {{
            proxy_pass http://127.0.0.1:8000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
        }}
    }}
}}
""")
    nginx_cmd = ExecuteProcess(
        cmd=['nginx', '-c', nginx_conf, '-g', 'daemon off;'],
        output='screen',
    )
    actions.append(nginx_cmd)

    # Log when rosbridge exits
    actions.append(RegisterEventHandler(
        OnProcessExit(
            target_action=rosbridge,
            on_exit=[LogInfo(msg='rosbridge exited, shutting down web stack')],
        )
    ))

    return actions


def generate_launch_description():
    return LaunchDescription([
        OpaqueFunction(function=_launch_web_stack),
    ])
