<template>
  <div
    class="virtual-joystick"
    :style="{ width: size + 'px', height: size + 'px' }"
    @pointerdown.prevent="onPointerDown"
    @pointermove.prevent="onPointerMove"
    @pointerup.prevent="onPointerUp"
    @pointerleave.prevent="onPointerUp"
    @pointercancel.prevent="onPointerUp"
  >
    <!-- 轴标签 -->
    <span class="joystick-label label-up">{{ axisLabels.up }}</span>
    <span class="joystick-label label-down">{{ axisLabels.down }}</span>
    <span class="joystick-label label-left">{{ axisLabels.left }}</span>
    <span class="joystick-label label-right">{{ axisLabels.right }}</span>

    <svg :width="svgSize" :height="svgSize" viewBox="0 0 200 200" class="joystick-svg">
      <!-- 轨道 -->
      <circle
        cx="100" cy="100" r="85"
        fill="none"
        :stroke="active ? 'rgba(0, 212, 255, 0.35)' : 'rgba(255,255,255,0.08)'"
        stroke-width="8"
      />
      <!-- 十字参考线 -->
      <line x1="100" y1="15" x2="100" y2="185" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
      <line x1="15" y1="100" x2="185" y2="100" stroke="rgba(255,255,255,0.06)" stroke-width="1" />
      <!-- 拇指 -->
      <circle
        :cx="thumbCx"
        :cy="thumbCy"
        r="24"
        :fill="active ? '#00d4ff' : 'rgba(0, 212, 255, 0.45)'"
        stroke="rgba(10, 14, 23, 0.8)"
        stroke-width="2"
        class="joystick-thumb"
      />
    </svg>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface JoystickOutput {
  x: number // -100 ~ 100
  y: number // -100 ~ 100
}

const props = withDefaults(defineProps<{
  axisLabels?: { up: string; down: string; left: string; right: string }
  size?: number
  deadZone?: number
}>(), {
  axisLabels: () => ({ up: '', down: '', left: '', right: '' }),
  size: 160,
  deadZone: 0.1,
})

const emit = defineEmits<{
  (e: 'update', data: JoystickOutput): void
}>()

const svgSize = computed(() => props.size)

// Thumb position in SVG coords (100 = center)
const thumbCx = ref(100)
const thumbCy = ref(100)
const active = ref(false)

let capturedPointerId: number | null = null
let lastEmitTime = 0
const THROTTLE_MS = 50

function clamp(value: number, min: number, max: number) {
  return Math.max(min, Math.min(max, value))
}

function getSvgCoords(e: PointerEvent): { cx: number; cy: number } {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  const scale = 200 / rect.width
  const cx = 100 + (e.clientX - (rect.left + rect.width / 2)) * scale
  const cy = 100 + (e.clientY - (rect.top + rect.height / 2)) * scale
  // Clamp to track radius (85)
  const dx = cx - 100
  const dy = cy - 100
  const dist = Math.sqrt(dx * dx + dy * dy)
  if (dist > 85) {
    const ratio = 85 / dist
    return { cx: 100 + dx * ratio, cy: 100 + dy * ratio }
  }
  return { cx, cy }
}

function svgToOutput(cx: number, cy: number): JoystickOutput {
  // Map SVG coords to -100..100
  let x = ((cx - 100) / 85) * 100
  let y = -((cy - 100) / 85) * 100 // invert y (screen y goes down)

  // Apply dead zone
  const mag = Math.sqrt(x * x + y * y)
  if (mag < props.deadZone * 100) {
    x = 0
    y = 0
  }

  return {
    x: Math.round(clamp(x, -100, 100)),
    y: Math.round(clamp(y, -100, 100)),
  }
}

function emitThrottled(data: JoystickOutput) {
  const now = performance.now()
  if (now - lastEmitTime >= THROTTLE_MS) {
    lastEmitTime = now
    emit('update', data)
  }
}

function onPointerDown(e: PointerEvent) {
  if (capturedPointerId !== null) return // already tracking
  capturedPointerId = e.pointerId
  active.value = true
  const { cx, cy } = getSvgCoords(e)
  thumbCx.value = cx
  thumbCy.value = cy
  emitThrottled(svgToOutput(cx, cy))
}

function onPointerMove(e: PointerEvent) {
  if (e.pointerId !== capturedPointerId) return
  const { cx, cy } = getSvgCoords(e)
  thumbCx.value = cx
  thumbCy.value = cy
  emitThrottled(svgToOutput(cx, cy))
}

function onPointerUp(e: PointerEvent) {
  if (e.pointerId !== capturedPointerId) return
  capturedPointerId = null
  active.value = false
  thumbCx.value = 100
  thumbCy.value = 100
  emit('update', { x: 0, y: 0 })
}
</script>

<style scoped>
.virtual-joystick {
  position: relative;
  display: flex;
  justify-content: center;
  align-items: center;
  touch-action: none;
  user-select: none;
  -webkit-user-select: none;
}

.joystick-svg {
  width: 100%;
  height: 100%;
  pointer-events: none;
}

.joystick-thumb {
  transition: fill 0.15s ease;
}

.joystick-label {
  position: absolute;
  color: #4a5568;
  font-size: 10px;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.label-up {
  top: 0;
  left: 50%;
  transform: translateX(-50%);
}

.label-down {
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
}

.label-left {
  left: 2px;
  top: 50%;
  transform: translateY(-50%);
}

.label-right {
  right: 2px;
  top: 50%;
  transform: translateY(-50%);
}
</style>
