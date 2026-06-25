from pydantic import BaseModel, Field


class Telemetry(BaseModel):
    depth: float = 0.0              # current depth (m), positive = underwater
    target_depth: float = 0.0       # target depth
    depth_hold_enabled: bool = False  # depth hold toggle
    vertical_pwm: float = 0.0       # PID vertical thrust output
    target_heading: float = 0.0     # target heading (degrees, 0-360)
    heading_hold_enabled: bool = False  # heading hold toggle
    yaw_pwm: float = 0.0            # PID yaw thrust output
    lat: float = 0.0                # latitude
    lon: float = 0.0                # longitude
    yaw: float = 0.0                # current heading (degrees)
    ros_connected: bool = False     # ROS connection status


class SetDepthTargetRequest(BaseModel):
    target: float = Field(
        ..., ge=0.0, description="target depth (m), must be >= 0"
    )


class SetHeadingTargetRequest(BaseModel):
    target: float = Field(
        ..., description="target heading (degrees), will be normalized to 0-360"
    )


class ApiResponse(BaseModel):
    success: bool
    message: str
