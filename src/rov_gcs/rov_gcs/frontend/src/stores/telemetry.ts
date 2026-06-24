import { defineStore } from 'pinia'
import { reactive, toRefs } from 'vue'

export interface Telemetry {
  depth: number
  target_depth: number
  hold_enabled: boolean
  vertical_cmd: number
  lat: number
  lon: number
  yaw: number
  ros_connected: boolean
}

function defaultTelemetry(): Telemetry {
  return {
    depth: 0,
    target_depth: 0,
    hold_enabled: false,
    vertical_cmd: 0,
    lat: 0,
    lon: 0,
    yaw: 0,
    ros_connected: false,
  }
}

export const useTelemetryStore = defineStore('telemetry', () => {
  const state = reactive<{ telemetry: Telemetry }>({
    telemetry: defaultTelemetry(),
  })

  function updateTelemetry(data: Partial<Telemetry>) {
    Object.assign(state.telemetry, data)
  }

  function setRosConnected(v: boolean) {
    state.telemetry.ros_connected = v
  }

  return {
    ...toRefs(state),
    updateTelemetry,
    setRosConnected,
  }
})
