import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Telemetry {
  depth: number
  target_depth: number
  depth_hold_enabled: boolean
  vertical_pwm: number
  target_heading: number
  heading_hold_enabled: boolean
  yaw_pwm: number
  lat: number
  lon: number
  yaw: number
  armed: boolean
  ros_connected: boolean
  current_grid: string
  target_grid: string
  grid_reached: boolean
  grid_rows: number
  grid_cols: number
  grid_current_row: number
  grid_current_col: number
  grid_target_row: number
  grid_target_col: number
  gain_level: number
  light_on: boolean
  depth_kp: number
  depth_ki: number
  depth_kd: number
  heading_kp: number
  heading_ki: number
  heading_kd: number
}

export const useTelemetryStore = defineStore('telemetry', () => {
  const telemetry = ref<Telemetry>({
    depth: 0,
    target_depth: 0,
    depth_hold_enabled: false,
    vertical_pwm: 0,
    target_heading: 0,
    heading_hold_enabled: false,
    yaw_pwm: 0,
    lat: 0,
    lon: 0,
    yaw: 0,
    armed: false,
    ros_connected: false,
    current_grid: '',
    target_grid: '',
    grid_reached: false,
    grid_rows: 0,
    grid_cols: 0,
    grid_current_row: -1,
    grid_current_col: -1,
    grid_target_row: -1,
    grid_target_col: -1,
    gain_level: 50,
    light_on: false,
    depth_kp: 100.0,
    depth_ki: 40.0,
    depth_kd: 80.0,
    heading_kp: 80.0,
    heading_ki: 20.0,
    heading_kd: 40.0,
  })

  function updateTelemetry(data: Partial<Telemetry>) {
    Object.assign(telemetry.value, data)
  }

  function setRosConnected(v: boolean) {
    telemetry.value.ros_connected = v
  }

  return { telemetry, updateTelemetry, setRosConnected }
})
