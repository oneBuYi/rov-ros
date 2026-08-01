<template>
  <div class="gauges-panel">
    <!-- 深度列 -->
    <div class="gauge-col">
      <div class="gauge-label">深度</div>
      <div class="depth-visual">
        <div class="bar-track">
          <div
            class="bar-target"
            :style="{ bottom: (targetRatio * 100) + '%' }"
          ></div>
          <div
            class="bar-fill"
            :style="{ height: (ratio * 100) + '%', background: barColor }"
          ></div>
        </div>
      </div>
      <div class="gauge-value">
        <span class="gauge-num" :style="{ color: barColor }">{{ depth.toFixed(1) }}</span>
        <span class="gauge-unit">m</span>
      </div>
      <div class="gauge-target">目标 {{ targetDepth.toFixed(1) }} m</div>
    </div>

    <!-- 航向列 -->
    <div class="gauge-col">
      <div class="gauge-label">航向</div>
      <div class="heading-visual">
        <svg viewBox="0 0 200 200" class="gauge-svg">
          <circle
            cx="100" cy="100" r="80"
            fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12"
          />
          <circle
            cx="100" cy="100" r="80"
            fill="none"
            stroke="#00d4ff"
            stroke-width="12"
            stroke-linecap="round"
            :stroke-dasharray="`${headingArc} 502`"
            stroke-dashoffset="0"
            transform="rotate(-90, 100, 100)"
          />
          <circle
            v-if="targetHeading > 0 || targetHeading <= 360"
            :cx="100 + 80 * Math.cos((targetHeading - 90) * Math.PI / 180)"
            :cy="100 + 80 * Math.sin((targetHeading - 90) * Math.PI / 180)"
            r="5"
            fill="#ffd93d"
            stroke="#0a0e17"
            stroke-width="1.5"
          />
          <text x="100" y="105" text-anchor="middle" class="heading-num-svg">
            {{ safeHeading.toFixed(1) }}
          </text>
          <text x="100" y="125" text-anchor="middle" class="heading-unit-svg">°</text>
        </svg>
      </div>
      <div class="gauge-target">目标 {{ targetHeading.toFixed(0) }}°</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  depth: number
  targetDepth: number
  heading: number
  targetHeading: number
  maxDepth?: number
}>()

// ---- depth ----
const maxDepth = computed(() => props.maxDepth || 10)
const ratio = computed(() =>
  Math.max(0, Math.min(props.depth / maxDepth.value, 1.0))
)
const targetRatio = computed(() =>
  Math.max(0, Math.min(props.targetDepth / maxDepth.value, 1.0))
)
const barColor = computed(() => {
  if (ratio.value > 0.7) return '#ff6b6b'
  if (ratio.value > 0.4) return '#ffd93d'
  return '#00d4ff'
})

// ---- heading ----
const safeHeading = computed(() =>
  isNaN(props.heading) ? 0 : ((props.heading % 360) + 360) % 360
)
const headingArc = computed(() =>
  Math.round((safeHeading.value / 360) * 502)
)
</script>

<style scoped>
.gauges-panel {
  display: flex;
  gap: 6px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  padding: 8px 10px;
  height: 195px;
  box-sizing: content-box;
}

/* ---- column ---- */
.gauge-col {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 2px;
  flex: 1;
}

/* ---- shared ---- */
.gauge-label {
  color: #8899aa;
  font-size: 11px;
}
.gauge-target {
  font-size: 10px;
  color: #8899aa;
}
.gauge-num {
  font-size: 22px;
  font-weight: 700;
  color: #e0e6ed;
}
.gauge-unit {
  font-size: 11px;
  color: #8899aa;
}

/* ---- depth bar ---- */
.depth-visual {
  display: flex;
  justify-content: center;
  align-items: flex-end;
  flex: 1;
  min-height: 100px;
}
.bar-track {
  position: relative;
  width: 20px;
  height: 100%;
  background: rgba(255, 255, 255, 0.06);
  border-radius: 4px;
  overflow: hidden;
}
.bar-fill {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  border-radius: 4px;
  transition: height 0.3s ease, background 0.3s ease;
}
.bar-target {
  position: absolute;
  left: -6px;
  right: -6px;
  height: 2px;
  background: rgba(255, 255, 255, 0.5);
  z-index: 1;
}
.bar-target::after {
  content: '';
  position: absolute;
  left: 50%;
  top: -3px;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 5px solid transparent;
  border-right: 5px solid transparent;
  border-top: 6px solid rgba(255, 255, 255, 0.5);
}
.gauge-value {
  display: flex;
  justify-content: center;
  align-items: baseline;
  gap: 2px;
}

/* ---- heading compass ---- */
.heading-visual {
  display: flex;
  justify-content: center;
  align-items: center;
  flex: 1;
  min-height: 100px;
}
.gauge-svg {
  width: 110px;
  height: 110px;
}
.heading-num-svg {
  font-size: 26px;
  font-weight: 700;
  fill: #e0e6ed;
}
.heading-unit-svg {
  font-size: 12px;
  fill: #8899aa;
}
</style>
