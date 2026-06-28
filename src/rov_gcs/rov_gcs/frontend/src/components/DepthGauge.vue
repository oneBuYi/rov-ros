<template>
  <div class="depth-bar">
    <div class="bar-label">深度</div>
    <div class="bar-track">
      <!-- 目标深度标记线 -->
      <div
        class="bar-target"
        :style="{ bottom: (targetRatio * 100) + '%' }"
      ></div>
      <!-- 填充条 -->
      <div
        class="bar-fill"
        :style="{ height: (ratio * 100) + '%', background: barColor }"
      ></div>
    </div>
    <div class="bar-readings">
      <span class="bar-value" :style="{ color: barColor }">{{ depth.toFixed(1) }}</span>
      <span class="bar-unit">m</span>
    </div>
    <div class="bar-target-text">目标 {{ targetDepth.toFixed(1) }} m</div>
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
const targetRatio = computed(() =>
  Math.max(0, Math.min(props.targetDepth / maxDepth.value, 1.0))
)

const barColor = computed(() => {
  if (ratio.value > 0.7) return '#ff6b6b'
  if (ratio.value > 0.4) return '#ffd93d'
  return '#00d4ff'
})
</script>

<style scoped>
.depth-bar {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  padding: 10px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  width: 70px;
}

.bar-label {
  color: #8899aa;
  font-size: 12px;
}

.bar-track {
  position: relative;
  width: 24px;
  height: 120px;
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

.bar-readings {
  display: flex;
  align-items: baseline;
  gap: 2px;
}

.bar-value {
  font-size: 24px;
  font-weight: 700;
}

.bar-unit {
  font-size: 12px;
  color: #8899aa;
}

.bar-target-text {
  font-size: 10px;
  color: #8899aa;
}
</style>
