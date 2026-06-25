<template>
  <div class="control-panel">
    <!-- 深度控制 -->
    <div class="ctrl-group">
      <label>目标深度 (m)</label>
      <div class="input-row">
        <input
          v-model.number="depthTargetInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="输入深度"
          @keyup.enter="handleSetDepthTarget"
        />
        <button :disabled="sending" @click="handleSetDepthTarget">设定</button>
      </div>
      <p v-if="error" class="error">{{ error }}</p>
    </div>
    <button
      class="hold-btn"
      :class="depthHoldEnabled ? 'active' : ''"
      :disabled="sending"
      @click="handleDepthHold"
    >
      {{ depthHoldEnabled ? '关闭定深' : '开启定深' }}
    </button>

    <!-- 航向控制 -->
    <div class="ctrl-group">
      <label>目标航向 (°)</label>
      <div class="input-row">
        <input
          v-model.number="headingTargetInput"
          type="number"
          step="1"
          min="0"
          max="360"
          placeholder="输入航向"
          @keyup.enter="handleSetHeadingTarget"
        />
        <button :disabled="sending" @click="handleSetHeadingTarget">设定</button>
      </div>
    </div>
    <button
      class="hold-btn"
      :class="headingHoldEnabled ? 'active' : ''"
      :disabled="sending"
      @click="handleHeadingHold"
    >
      {{ headingHoldEnabled ? '关闭定航' : '开启定航' }}
    </button>

    <div class="gamepad-status">
      🎮 {{ gamepadConnected ? '手柄已连接' : '手柄未连接' }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useApi } from '../composables/useApi'
import { useTelemetryStore } from '../stores/telemetry'

const props = defineProps<{ gamepadConnected: boolean }>()
const store = useTelemetryStore()
const { setDepthTarget, toggleDepthHold, setHeadingTarget, toggleHeadingHold } =
  useApi()
const depthTargetInput = ref(0)
const headingTargetInput = ref(0)
const sending = ref(false)
const error = ref('')

const depthHoldEnabled = computed(
  () => store.telemetry.value.depth_hold_enabled
)
const headingHoldEnabled = computed(
  () => store.telemetry.value.heading_hold_enabled
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
  align-items: center;
  gap: 16px;
  padding: 10px 16px;
  background: #141924;
  border-top: 1px solid #2a3040;
}
.ctrl-group {
  display: flex;
  align-items: center;
  gap: 8px;
}
.ctrl-group label {
  color: #8899aa;
  font-size: 13px;
  white-space: nowrap;
}
.input-row {
  display: flex;
  gap: 6px;
}
input {
  width: 100px;
  padding: 6px 10px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: #0a0e17;
  color: #e0e6ed;
  font-size: 14px;
}
input:focus {
  outline: none;
  border-color: #00d4ff;
}
button {
  padding: 6px 14px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
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
  background: #00d4ff33;
  color: #00d4ff;
}
.error {
  color: #ff6b6b;
  font-size: 12px;
  margin-left: 8px;
}
.gamepad-status {
  margin-left: auto;
  font-size: 13px;
  color: #8899aa;
}
</style>
