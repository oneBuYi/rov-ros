from pydantic import BaseModel, Field


class Telemetry(BaseModel):
    depth: float = 0.0              # current depth (m), positive = underwater
    target_depth: float = 0.0       # target depth
    hold_enabled: bool = False      # depth hold toggle
    vertical_pwm: float = 0.0       # PID vertical thrust output
    lat: float = 0.0                # latitude
    lon: float = 0.0                # longitude
    yaw: float = 0.0                # heading (degrees)
    ros_connected: bool = False     # ROS connection status


class SetTargetRequest(BaseModel):
    target: float = Field(
        ..., ge=0.0, description="target depth (m), must be >= 0"
    )


class ApiResponse(BaseModel):
    success: bool
    message: str
