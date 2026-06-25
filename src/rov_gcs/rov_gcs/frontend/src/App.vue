<template>
  <div id="gcs-app">
    <StatusBar
      :ros-connected="store.telemetry.ros_connected"
      :hold-enabled="store.telemetry.depth_hold_enabled || store.telemetry.heading_hold_enabled"
    />
    <div class="dashboard">
      <DepthGauge
        :depth="store.telemetry.depth"
        :target-depth="store.telemetry.target_depth"
      />
      <VideoPlaceholder />
      <TelemetryPanel
        :lat="store.telemetry.lat"
        :lon="store.telemetry.lon"
        :yaw="store.telemetry.yaw"
        :vertical-pwm="store.telemetry.vertical_pwm"
      />
    </div>
    <ControlPanel :gamepad-connected="gamepadConnected" />
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import VideoPlaceholder from './components/VideoPlaceholder.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useGamepad } from './composables/useGamepad'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const gamepadConnected = ref(false)

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => {
  gamepadConnected.value = v
}

onMounted(() => {
  connect()
  try {
    const gamepad = useGamepad({
      onData: (data) => {
        send({ type: 'joystick', data })
      },
      onConnect: (v) => {
        gamepadConnected.value = v
      },
    })
    gamepad.start()
  } catch (e) {
    console.warn('Gamepad API unavailable:', e)
  }
})

onUnmounted(() => close())
</script>

<style>
#gcs-app {
  display: flex;
  flex-direction: column;
  height: 100vh;
  max-width: 960px;
  margin: 0 auto;
  overflow: hidden;
}
.dashboard {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: grid;
  grid-template-columns: 1fr 1fr 1fr;
  gap: 8px;
  padding: 8px;
}
@media (max-width: 700px) {
  .dashboard {
    grid-template-columns: 1fr;
  }
}
</style>
