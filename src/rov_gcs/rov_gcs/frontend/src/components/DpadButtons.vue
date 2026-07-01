<template>
  <div class="dpad-container">
    <!-- 上：增益+ -->
    <button
      class="dpad-btn dpad-up"
      :class="{ active: pressed[BTN_UP] }"
      @pointerdown.prevent="onPress(BTN_UP)"
      @pointerup.prevent="onRelease(BTN_UP)"
      @pointerleave.prevent="onRelease(BTN_UP)"
      @pointercancel.prevent="onRelease(BTN_UP)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 19V5M5 12l7-7 7 7" />
      </svg>
      <span class="dpad-label">增益+</span>
    </button>

    <!-- 左：关灯 -->
    <button
      class="dpad-btn dpad-left"
      :class="{ active: pressed[BTN_LEFT] }"
      @pointerdown.prevent="onPress(BTN_LEFT)"
      @pointerup.prevent="onRelease(BTN_LEFT)"
      @pointerleave.prevent="onRelease(BTN_LEFT)"
      @pointercancel.prevent="onRelease(BTN_LEFT)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M19 12H5M12 19l-7-7 7-7" />
      </svg>
      <span class="dpad-label">关灯</span>
    </button>

    <!-- 中心空位 -->
    <div class="dpad-center" />

    <!-- 右：开灯 -->
    <button
      class="dpad-btn dpad-right"
      :class="{ active: pressed[BTN_RIGHT] }"
      @pointerdown.prevent="onPress(BTN_RIGHT)"
      @pointerup.prevent="onRelease(BTN_RIGHT)"
      @pointerleave.prevent="onRelease(BTN_RIGHT)"
      @pointercancel.prevent="onRelease(BTN_RIGHT)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
      <span class="dpad-label">开灯</span>
    </button>

    <!-- 下：增益- -->
    <button
      class="dpad-btn dpad-down"
      :class="{ active: pressed[BTN_DOWN] }"
      @pointerdown.prevent="onPress(BTN_DOWN)"
      @pointerup.prevent="onRelease(BTN_DOWN)"
      @pointerleave.prevent="onRelease(BTN_DOWN)"
      @pointercancel.prevent="onRelease(BTN_DOWN)"
    >
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
        <path d="M12 5v14M5 12l7 7 7-7" />
      </svg>
      <span class="dpad-label">增益-</span>
    </button>
  </div>
</template>

<script setup lang="ts">
import { reactive } from 'vue'

const emit = defineEmits<{
  (e: 'update', buttons: number[]): void
}>()

// SDL2 按钮索引：与物理手柄十字键一致
const BTN_UP = 11     // 1<<11 = 2048  增益+25%
const BTN_DOWN = 12   // 1<<12 = 4096  增益-25%
const BTN_LEFT = 13   // 1<<13 = 8192  关灯
const BTN_RIGHT = 14  // 1<<14 = 16384 开灯

const BUTTON_COUNT = 15

// 当前按下状态
const pressed = reactive<Record<number, number>>({
  [BTN_UP]: 0,
  [BTN_DOWN]: 0,
  [BTN_LEFT]: 0,
  [BTN_RIGHT]: 0,
})

// 防止 pointerup + pointerleave 对同一次触摸重复触发
const tracking = reactive<Record<number, boolean>>({
  [BTN_UP]: false,
  [BTN_DOWN]: false,
  [BTN_LEFT]: false,
  [BTN_RIGHT]: false,
})

function buildButtons(): number[] {
  const arr = new Array(BUTTON_COUNT).fill(0)
  arr[BTN_UP] = pressed[BTN_UP]
  arr[BTN_DOWN] = pressed[BTN_DOWN]
  arr[BTN_LEFT] = pressed[BTN_LEFT]
  arr[BTN_RIGHT] = pressed[BTN_RIGHT]
  return arr
}

function onPress(idx: number) {
  if (tracking[idx]) return
  tracking[idx] = true
  pressed[idx] = 1
  emit('update', buildButtons())
}

function onRelease(idx: number) {
  if (!tracking[idx]) return
  tracking[idx] = false
  pressed[idx] = 0
  emit('update', buildButtons())
}
</script>

<style scoped>
.dpad-container {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  grid-template-rows: repeat(3, 1fr);
  gap: 4px;
  width: 150px;
  height: 150px;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}

.dpad-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  border: 1px solid #2a3040;
  border-radius: 8px;
  background: rgba(20, 25, 36, 0.65);
  color: #4a5568;
  cursor: pointer;
  padding: 0;
  margin: 0;
  outline: none;
  -webkit-tap-highlight-color: transparent;
  touch-action: none;
  transition: background 0.15s ease, border-color 0.15s ease, color 0.15s ease;
}

.dpad-btn:hover {
  border-color: #4a5568;
  color: #8899aa;
}

.dpad-btn:active,
.dpad-btn.active {
  background: rgba(0, 212, 255, 0.2);
  border-color: #00d4ff;
  color: #00d4ff;
}

.dpad-up    { grid-column: 2; grid-row: 1; }
.dpad-down  { grid-column: 2; grid-row: 3; }
.dpad-left  { grid-column: 1; grid-row: 2; }
.dpad-right { grid-column: 3; grid-row: 2; }

.dpad-center {
  grid-column: 2;
  grid-row: 2;
}

.dpad-label {
  font-size: 10px;
  letter-spacing: 0.03em;
  line-height: 1;
}
</style>
