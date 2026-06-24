<template>
  <div id="gcs-app">
    <StatusBar
      :ros-connected="t.ros_connected"
      :hold-enabled="t.hold_enabled"
    />
    <div class="dashboard">
      <DepthGauge :depth="t.depth" :target-depth="t.target_depth" />
      <VideoPlaceholder />
      <TelemetryPanel
        :lat="t.lat"
        :lon="t.lon"
        :yaw="t.yaw"
        :vertical-cmd="t.vertical_cmd"
      />
    </div>
    <ControlPanel :gamepad-connected="gamepadConnected" />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import VideoPlaceholder from './components/VideoPlaceholder.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useGamepad } from './composables/useGamepad'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const t = computed(() => store.telemetry.value)
const gamepadConnected = ref(false)

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => {
  gamepadConnected.value = v
}

onMounted(() => {
  connect()
  const gamepad = useGamepad({
    onData: (data) => {
      send({ type: 'joystick', data })
    },
    onConnect: (v) => {
      gamepadConnected.value = v
    },
  })
  gamepad.start()
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
}
.dashboard {
  flex: 1;
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
