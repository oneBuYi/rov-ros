import { defineStore } from 'pinia'
import { ref } from 'vue'

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

export const useTelemetryStore = defineStore('telemetry', () => {
  const telemetry = ref<Telemetry>({
    depth: 0,
    target_depth: 0,
    hold_enabled: false,
    vertical_cmd: 0,
    lat: 0,
    lon: 0,
    yaw: 0,
    ros_connected: false,
  })

  function updateTelemetry(data: Partial<Telemetry>) {
    Object.assign(telemetry.value, data)
  }

  function setRosConnected(v: boolean) {
    telemetry.value.ros_connected = v
  }

  return { telemetry, updateTelemetry, setRosConnected }
})
