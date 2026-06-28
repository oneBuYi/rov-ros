<template>
  <div class="depth-gauge">
    <svg viewBox="0 0 200 200" class="gauge-svg">
      <!-- Background arc -->
      <circle
        cx="100" cy="100" r="85"
        fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12"
      />
      <!-- Value arc -->
      <circle
        cx="100" cy="100" r="85"
        fill="none"
        :stroke="gaugeColor"
        stroke-width="12"
        stroke-linecap="round"
        :stroke-dasharray="`${arcLength} 534`"
        stroke-dashoffset="0"
        transform="rotate(135, 100, 100)"
      />
      <!-- Depth reading -->
      <text x="100" y="95" text-anchor="middle" class="depth-value">
        {{ depth.toFixed(1) }}
      </text>
      <text x="100" y="115" text-anchor="middle" class="depth-unit">m</text>
      <!-- Target indicator -->
      <text x="100" y="140" text-anchor="middle" class="target-text">
        目标 {{ targetDepth.toFixed(1) }} m
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  depth: number
  targetDepth: number
  maxDepth?: number
}>()

const maxDepth = computed(() => props.maxDepth || 10)
const ratio = computed(() =>
  Math.max(0, Math.min(props.depth / maxDepth.value, 1.0))
)
const arcLength = computed(() => Math.round(ratio.value * 400))

const gaugeColor = computed(() => {
  if (ratio.value > 0.7) return '#ff6b6b'
  if (ratio.value > 0.4) return '#ffd93d'
  return '#00d4ff'
})
</script>

<style scoped>
.depth-gauge {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.gauge-svg {
  width: 140px;
  height: 140px;
}
.depth-value {
  font-size: 32px;
  font-weight: 700;
  fill: #e0e6ed;
}
.depth-unit {
  font-size: 13px;
  fill: #8899aa;
}
.target-text {
  font-size: 11px;
  fill: #8899aa;
}
</style>
