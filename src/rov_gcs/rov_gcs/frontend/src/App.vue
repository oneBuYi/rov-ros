<!-- App.vue -->
<template>
  <div id="gcs-app">
    <!-- 视频层 -->
    <div class="video-layer">
      <img
        v-if="rosConnected && !streamError"
        :src="streamUrl"
        class="video-stream"
        @error="onStreamError"
      />
      <div v-else class="video-fallback">
        <svg
          width="48" height="48" viewBox="0 0 24 24"
          fill="none" stroke="#4a5568" stroke-width="1.5"
        >
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M10 9l5 3-5 3V9z" fill="#4a5568" />
        </svg>
        <p>{{ streamError ? '视频信号丢失' : 'ROS 未连接' }}</p>
      </div>
    </div>

    <!-- HUD 叠加层 -->
    <div class="hud-overlay">
      <div class="hud-top-left">
        <StatusBar
          :ros-connected="rosConnected"
          :depth-hold-enabled="store.telemetry.depth_hold_enabled"
          :heading-hold-enabled="store.telemetry.heading_hold_enabled"
        />
      </div>
      <div class="hud-top-right">
        <TelemetryPanel
          :lat="store.telemetry.lat"
          :lon="store.telemetry.lon"
          :yaw="store.telemetry.yaw"
          :vertical-pwm="store.telemetry.vertical_pwm"
          :yaw-pwm="store.telemetry.yaw_pwm"
        />
      </div>
      <div class="hud-mid-left">
        <div class="gauges-row">
          <DepthGauge
            :depth="store.telemetry.depth"
            :target-depth="store.telemetry.target_depth"
          />
          <HeadingGauge
            :heading="store.telemetry.yaw"
            :target-heading="store.telemetry.target_heading"
          />
        </div>
      </div>
      <div class="hud-mid-right">
        <ControlPanel :gamepad-connected="gamepadConnected" />
      </div>

      <!-- 虚拟摇杆 - 左脸颊（水平移动） -->
      <div class="hud-cheek-left">
        <VirtualJoystick
          :axis-labels="{ up: '前进', down: '后退', left: '左移', right: '右移' }"
          :size="160"
          @update="onLeftJoystick"
        />
      </div>
      <!-- 虚拟摇杆 - 右脸颊（升降/旋转） -->
      <div class="hud-cheek-right">
        <VirtualJoystick
          :axis-labels="{ up: '上升', down: '下降', left: '左转', right: '右转' }"
          :size="160"
          @update="onRightJoystick"
        />
      </div>

      <div class="hud-bot-left">
        <GridStatus />
      </div>
      <div class="hud-bot-center">
        <GridTarget />
      </div>
      <div class="hud-bot-right">
        <GridReached />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import HeadingGauge from './components/HeadingGauge.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import VirtualJoystick from './components/VirtualJoystick.vue'
import GridStatus from './components/GridStatus.vue'
import GridTarget from './components/GridTarget.vue'
import GridReached from './components/GridReached.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useGamepad } from './composables/useGamepad'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const gamepadConnected = ref(false)
const streamError = ref(false)
const streamUrl = '/api/video/stream'

const rosConnected = computed(() => store.telemetry.ros_connected)

watch(rosConnected, (connected) => {
  if (connected) {
    streamError.value = false
  }
})

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => {
  gamepadConnected.value = v
}

function onStreamError() {
  streamError.value = true
}

// ---- 虚拟摇杆 ----

function onLeftJoystick(data: { x: number; y: number }) {
  // 左摇杆：x=左移/右移, y=前进/后退
  send({
    type: 'joystick',
    data: { x: data.y, y: data.x, z: 0, r: 0, buttons: [] },
  })
}

function onRightJoystick(data: { x: number; y: number }) {
  // 右摇杆：x=左转/右转, y=上升/下降
  send({
    type: 'joystick',
    data: { x: 0, y: 0, z: data.y, r: data.x, buttons: [] },
  })
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
/* 全局样式重置 */
html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  background: #0a0e17;
}

#gcs-app {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* ---- 视频层 ---- */
.video-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}
.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.video-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #0a0e17;
  gap: 12px;
}
.video-fallback p {
  color: #4a5568;
  font-size: 14px;
}

/* ---- HUD 叠加层 ---- */
.hud-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-template-rows: auto 1fr auto;
  gap: 8px;
  padding: 8px;
}

.hud-overlay > * {
  pointer-events: auto;
}

.hud-top-left {
  grid-column: 1;
  grid-row: 1;
  justify-self: start;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.gauges-row {
  display: flex;
  gap: 8px;
}

.hud-top-right {
  grid-column: 3;
  grid-row: 1;
  justify-self: end;
}

.hud-mid-left {
  grid-column: 1;
  grid-row: 2;
  align-self: start;
  justify-self: start;
  margin-top: 50px;
}

.hud-mid-right {
  grid-column: 3;
  grid-row: 2;
  align-self: start;
  justify-self: end;
  margin-top: 50px;
}

/* 虚拟摇杆 - 脸颊位置（中下部两侧） */
.hud-cheek-left {
  grid-column: 1;
  grid-row: 2;
  align-self: end;
  justify-self: start;
  margin-bottom: 23vh;
  margin-left: 18vw;
}

.hud-cheek-right {
  grid-column: 3;
  grid-row: 2;
  align-self: end;
  justify-self: end;
  margin-bottom: 23vh;
  margin-right: 18vw;
}

.hud-bot-left {
  grid-column: 1;
  grid-row: 3;
  justify-self: start;
}

.hud-bot-center {
  grid-column: 2;
  grid-row: 3;
  justify-self: center;
}

.hud-bot-right {
  grid-column: 3;
  grid-row: 3;
  justify-self: end;
}

/* 小屏适配 */
@media (max-width: 320px) {
  .hud-mid-left,
  .hud-cheek-left,
  .hud-cheek-right {
    display: none;
  }
  .hud-overlay {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
