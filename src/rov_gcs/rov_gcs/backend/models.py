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
    armed: bool = False             # vehicle armed state (from /mavros/state)
    ros_connected: bool = False     # ROS connection status
    # Grid data
    current_grid: str = ""          # current grid cell label, e.g. "R0C3"
    target_grid: str = ""           # target grid cell label
    grid_reached: bool = False      # ROV is within target cell thresholds
    grid_rows: int = 0              # total rows in grid config
    grid_cols: int = 0              # total cols in grid config
    grid_current_row: int = -1      # current ROV cell row (-1 = none)
    grid_current_col: int = -1      # current ROV cell col (-1 = none)
    grid_target_row: int = -1       # target cell row (-1 = none)
    grid_target_col: int = -1       # target cell col (-1 = none)
    gain_level: int = 50            # motor gain level (percent)
    light_on: bool = False          # underwater light state


class SetDepthTargetRequest(BaseModel):
    target: float = Field(
        ..., ge=0.0, description="target depth (m), must be >= 0"
    )


class SetHeadingTargetRequest(BaseModel):
    target: float = Field(
        ..., description="target heading (degrees), will be normalized to 0-360"
    )


class SetGridTargetRequest(BaseModel):
    row: int = Field(
        ..., ge=0, description="target grid row index"
    )
    col: int = Field(
        ..., ge=0, description="target grid col index"
    )


class ApiResponse(BaseModel):
    success: bool
    message: str
