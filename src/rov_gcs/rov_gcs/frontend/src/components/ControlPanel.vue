<template>
  <div class="control-panel">
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 深度控制（目标+定深+PID） -->
    <div class="ctrl-group">
      <div class="label-row">
        <label>深度控制 (m)</label>
        <span class="pid-label">PID</span>
        <button class="reset-btn compact-btn" :disabled="sending" @click="handleResetDepthPID">↺</button>
      </div>
      <div class="compact-row">
        <input
          v-model.number="depthTargetInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="目标"
          @keyup.enter="handleSetDepthTarget"
        />
        <button :disabled="sending" @click="handleSetDepthTarget">设定</button>
        <button
          class="hold-btn compact-hold"
          :class="depthHoldEnabled ? 'active' : ''"
          :disabled="sending"
          @click="handleDepthHold"
        >
          {{ depthHoldEnabled ? '定深✓' : '定深' }}
        </button>
      </div>
      <div class="compact-pid-row">
        <input
          v-model.number="depthKpInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Kp"
          @keyup.enter="handleSetDepthPID"
        />
        <input
          v-model.number="depthKiInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Ki"
          @keyup.enter="handleSetDepthPID"
        />
        <input
          v-model.number="depthKdInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Kd"
          @keyup.enter="handleSetDepthPID"
        />
      </div>
    </div>

    <!-- 航向控制（目标+定航+PID） -->
    <div class="ctrl-group">
      <div class="label-row">
        <label>航向控制 (°)</label>
        <span class="pid-label">PID</span>
        <button class="reset-btn compact-btn" :disabled="sending" @click="handleResetHeadingPID">↺</button>
      </div>
      <div class="compact-row">
        <input
          v-model.number="headingTargetInput"
          type="number"
          step="1"
          min="0"
          max="360"
          placeholder="目标"
          @keyup.enter="handleSetHeadingTarget"
        />
        <button :disabled="sending" @click="handleSetHeadingTarget">设定</button>
        <button
          class="hold-btn compact-hold"
          :class="headingHoldEnabled ? 'active' : ''"
          :disabled="sending"
          @click="handleHeadingHold"
        >
          {{ headingHoldEnabled ? '定航✓' : '定航' }}
        </button>
      </div>
      <div class="compact-pid-row">
        <input
          v-model.number="headingKpInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Kp"
          @keyup.enter="handleSetHeadingPID"
        />
        <input
          v-model.number="headingKiInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Ki"
          @keyup.enter="handleSetHeadingPID"
        />
        <input
          v-model.number="headingKdInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="Kd"
          @keyup.enter="handleSetHeadingPID"
        />
      </div>
    </div>

    <!-- 电机增益 -->
    <div class="ctrl-group">
      <label>电机增益</label>
      <div class="gain-row">
        <button
          class="gain-btn"
          @pointerdown.prevent="onGainDown"
          @pointerup.prevent="onGainUp"
          @pointerleave.prevent="onGainUp"
        >−</button>
        <span class="gain-value">{{ store.telemetry.gain_level }}%</span>
        <button
          class="gain-btn"
          @pointerdown.prevent="onGainUpPress"
          @pointerup.prevent="onGainUp"
          @pointerleave.prevent="onGainUp"
        >+</button>
      </div>
    </div>

    <!-- 水下灯 -->
    <div class="ctrl-group">
      <label>水下灯</label>
      <button
        class="light-btn"
        :class="{ active: store.telemetry.light_on }"
        @click="toggleLight"
      >
        {{ store.telemetry.light_on ? '🔆 开' : '🌑 关' }}
      </button>
    </div>

    <!-- Arm/Disarm -->
    <button
      class="arm-btn"
      :class="store.telemetry.armed ? 'armed' : 'disarmed'"
      :disabled="sending"
      @click="handleArmToggle"
    >
      {{ store.telemetry.armed ? '🔴 Disarm' : '🟢 Arm' }}
    </button>

    <div class="gamepad-status">
      <template v-if="gamepadConnected">🎮 手柄已连接</template>
      <template v-else>🎮 按手柄键激活</template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useApi } from '../composables/useApi'
import { useTelemetryStore } from '../stores/telemetry'

const props = defineProps<{ gamepadConnected: boolean }>()
const store = useTelemetryStore()
const {
  setDepthTarget,
  toggleDepthHold,
  setHeadingTarget,
  toggleHeadingHold,
  arm,
  disarm,
  setDepthPIDGains,
  resetDepthPIDGains,
  setHeadingPIDGains,
  resetHeadingPIDGains,
} = useApi()
const depthTargetInput = ref(0)
const headingTargetInput = ref(0)
const depthKpInput = ref(100.0)
const depthKiInput = ref(40.0)
const depthKdInput = ref(80.0)
const headingKpInput = ref(80.0)
const headingKiInput = ref(20.0)
const headingKdInput = ref(40.0)
const sending = ref(false)
const error = ref('')

// Sync inputs with telemetry when it arrives
watch(() => store.telemetry.depth_kp, (v) => { depthKpInput.value = v })
watch(() => store.telemetry.depth_ki, (v) => { depthKiInput.value = v })
watch(() => store.telemetry.depth_kd, (v) => { depthKdInput.value = v })
watch(() => store.telemetry.heading_kp, (v) => { headingKpInput.value = v })
watch(() => store.telemetry.heading_ki, (v) => { headingKiInput.value = v })
watch(() => store.telemetry.heading_kd, (v) => { headingKdInput.value = v })

const depthHoldEnabled = computed(
  () => store.telemetry.depth_hold_enabled
)
const headingHoldEnabled = computed(
  () => store.telemetry.heading_hold_enabled
)

// ----- depth -----

async function handleSetDepthTarget() {
  error.value = ''
  if (depthTargetInput.value < 0) {
    error.value = '深度不能为负数'
    return
  }
  sending.value = true
  try {
    await setDepthTarget(depthTargetInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleDepthHold() {
  error.value = ''
  sending.value = true
  try {
    await toggleDepthHold()
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}

// ----- arm/disarm -----

async function handleArmToggle() {
  error.value = ''
  sending.value = true
  try {
    if (store.telemetry.armed) {
      await disarm()
    } else {
      await arm()
    }
    // 状态会通过 /mavros/state 遥测回传同步，无需本地切换
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}

// ----- PID gains -----

async function handleSetDepthPID() {
  error.value = ''
  sending.value = true
  try {
    await setDepthPIDGains(depthKpInput.value, depthKiInput.value, depthKdInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleResetDepthPID() {
  error.value = ''
  sending.value = true
  try {
    await resetDepthPIDGains()
  } catch (e: any) {
    error.value = e.message || '重置失败'
  } finally {
    sending.value = false
  }
}

async function handleSetHeadingPID() {
  error.value = ''
  sending.value = true
  try {
    await setHeadingPIDGains(headingKpInput.value, headingKiInput.value, headingKdInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleResetHeadingPID() {
  error.value = ''
  sending.value = true
  try {
    await resetHeadingPIDGains()
  } catch (e: any) {
    error.value = e.message || '重置失败'
  } finally {
    sending.value = false
  }
}

// ----- gain & light -----

const BTN_GAIN_UP = 11    // 1<<11 = 2048  gain +25%
const BTN_GAIN_DOWN = 12  // 1<<12 = 4096  gain -25%
const BTN_LIGHT_OFF = 13  // 1<<13 = 8192  light off
const BTN_LIGHT_ON = 14   // 1<<14 = 16384 light on
const BUTTON_COUNT = 15

function sendGainLightButtons(btn: number) {
  const arr = new Array(BUTTON_COUNT).fill(0)
  arr[btn] = 1
  const send = (window as any).__gcsSend
  if (send) {
    send({ type: 'joystick', data: { x: 0, y: 0, z: 0, r: 0, buttons: arr } })
  }
}

function sendReleaseButtons() {
  const send = (window as any).__gcsSend
  if (send) {
    send({ type: 'joystick', data: { x: 0, y: 0, z: 0, r: 0, buttons: new Array(BUTTON_COUNT).fill(0) } })
  }
}

function onGainDown() { sendGainLightButtons(BTN_GAIN_DOWN) }
function onGainUpPress() { sendGainLightButtons(BTN_GAIN_UP) }
function onGainUp() { sendReleaseButtons() }

function toggleLight() {
  const btn = store.telemetry.light_on ? BTN_LIGHT_OFF : BTN_LIGHT_ON
  sendGainLightButtons(btn)
  setTimeout(() => sendReleaseButtons(), 50)
}

// ----- heading -----

async function handleSetHeadingTarget() {
  error.value = ''
  sending.value = true
  try {
    await setHeadingTarget(headingTargetInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleHeadingHold() {
  error.value = ''
  sending.value = true
  try {
    await toggleHeadingHold()
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.ctrl-group label {
  color: #8899aa;
  font-size: 11px;
}
.label-row {
  display: flex;
  align-items: center;
  gap: 6px;
}
.label-row label {
  flex: 1;
}
.input-row {
  display: flex;
  gap: 6px;
}
input {
  width: 70px;
  padding: 4px 6px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: #0a0e17;
  color: #e0e6ed;
  font-size: 12px;
}
input:focus {
  outline: none;
  border-color: #00d4ff;
}
button {
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: #00d4ff;
  color: #0a0e17;
  font-weight: 600;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.hold-btn {
  background: #2a3040;
  color: #8899aa;
}
.hold-btn.active {
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}
.error {
  color: #ff6b6b;
  font-size: 11px;
  margin: 0;
}
.arm-btn {
  background: #2a3040;
  color: #8899aa;
  font-weight: 600;
}
.arm-btn.armed {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}
.arm-btn.disarmed {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}
.gamepad-status {
  font-size: 11px;
  color: #8899aa;
}
.gain-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.gain-btn {
  width: 28px;
  height: 28px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: rgba(20, 25, 36, 0.8);
  color: #e0e6ed;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
  transition: background 0.15s ease, border-color 0.15s ease;
}
.gain-btn:hover {
  border-color: #4a5568;
}
.gain-btn:active {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
  color: #00d4ff;
}
.gain-value {
  font-size: 16px;
  font-weight: 700;
  font-family: monospace;
  color: #00d4ff;
  min-width: 42px;
  text-align: center;
}
.light-btn {
  padding: 4px 10px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: rgba(20, 25, 36, 0.8);
  color: #8899aa;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  width: 100%;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}
.light-btn:hover {
  border-color: #4a5568;
}
.light-btn.active {
  background: rgba(255, 193, 7, 0.15);
  border-color: #ffc107;
  color: #ffc107;
}
.compact-row {
  display: flex;
  gap: 4px;
  align-items: center;
}
.compact-row input {
  flex: 1;
  min-width: 0;
}
.compact-hold {
  font-size: 10px;
  padding: 4px 5px;
  white-space: nowrap;
}
.compact-pid-row {
  display: flex;
  gap: 4px;
}
.compact-pid-row input {
  width: 54px;
  flex: none;
  padding: 3px 4px;
  font-size: 11px;
}
.compact-btn {
  padding: 2px 5px;
  font-size: 13px;
  line-height: 1;
  flex-shrink: 0;
}
.pid-label {
  font-size: 10px;
  color: #667788;
  flex-shrink: 0;
}
.reset-btn {
  background: rgba(255, 107, 107, 0.15);
  color: #ff6b6b;
  border: 1px solid rgba(255, 107, 107, 0.3);
}
.reset-btn:hover {
  background: rgba(255, 107, 107, 0.25);
}
</style>
