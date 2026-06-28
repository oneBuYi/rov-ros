<template>
  <div class="heading-gauge">
    <svg viewBox="0 0 200 200" class="gauge-svg">
      <!-- 背景环 -->
      <circle
        cx="100" cy="100" r="80"
        fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12"
      />
      <!-- 当前航向弧 -->
      <circle
        cx="100" cy="100" r="80"
        fill="none"
        :stroke="gaugeColor"
        stroke-width="12"
        stroke-linecap="round"
        :stroke-dasharray="`${headingArc} 502`"
        stroke-dashoffset="0"
        transform="rotate(-90, 100, 100)"
      />
      <!-- 目标航向标记点 -->
      <circle
        v-if="targetHeading > 0 || targetHeading <= 360"
        :cx="100 + 80 * Math.cos((targetHeading - 90) * Math.PI / 180)"
        :cy="100 + 80 * Math.sin((targetHeading - 90) * Math.PI / 180)"
        r="5"
        fill="#ffd93d"
        stroke="#0a0e17"
        stroke-width="1.5"
      />
      <!-- 航向数值 -->
      <text x="100" y="95" text-anchor="middle" class="heading-value">
        {{ safeHeading.toFixed(1) }}
      </text>
      <text x="100" y="115" text-anchor="middle" class="heading-unit">°</text>
      <!-- 目标文字 -->
      <text x="100" y="140" text-anchor="middle" class="target-text">
        目标 {{ targetHeading.toFixed(0) }}°
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  heading: number
  targetHeading: number
}>()

const safeHeading = computed(() =>
  isNaN(props.heading) ? 0 : ((props.heading % 360) + 360) % 360
)

const headingArc = computed(() =>
  Math.round((safeHeading.value / 360) * 502)
)

const gaugeColor = computed(() => {
  // 航向环始终用青色
  return '#00d4ff'
})
</script>

<style scoped>
.heading-gauge {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.gauge-svg {
  width: 130px;
  height: 130px;
}
.heading-value {
  font-size: 28px;
  font-weight: 700;
  fill: #e0e6ed;
}
.heading-unit {
  font-size: 12px;
  fill: #8899aa;
}
.target-text {
  font-size: 10px;
  fill: #8899aa;
}
</style>
