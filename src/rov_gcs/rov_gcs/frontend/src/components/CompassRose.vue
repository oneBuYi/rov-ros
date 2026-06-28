<template>
  <div class="compass-rose">
    <svg viewBox="0 0 200 200" class="compass-svg">
      <!-- 外圈刻度环 -->
      <circle
        cx="100" cy="100" r="88"
        fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1"
      />
      <!-- 刻度线：每 5° 一条短线，每 30° 一条长线 + 方向标签 -->
      <g v-for="deg in 72" :key="deg">
        <line
          v-if="deg % 6 !== 0"
          :x1="100 + 80 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y1="100 + 80 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          :x2="100 + 86 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y2="100 + 86 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          stroke="rgba(255,255,255,0.2)" stroke-width="1"
        />
        <line
          v-if="deg % 6 === 0"
          :x1="100 + 76 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y1="100 + 76 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          :x2="100 + 86 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y2="100 + 86 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          stroke="rgba(255,255,255,0.35)" stroke-width="1.5"
        />
      </g>
      <!-- 方向标签：每 30° -->
      <g
        v-for="(label, i) in directionLabels"
        :key="label"
        :transform="`rotate(${i * 15}, 100, 100)`"
      >
        <text
          :x="100"
          :y="62"
          text-anchor="middle"
          class="direction-label"
          :class="{ 'direction-main': i % 3 === 0 }"
        >
          {{ label }}
        </text>
      </g>
      <!-- 航向指针（三角形） -->
      <polygon
        :points="pointerPoints"
        fill="#00d4ff"
        :transform="`rotate(${safeHeading}, 100, 100)`"
      />
      <!-- 中心点 -->
      <circle cx="100" cy="100" r="4" fill="#00d4ff" />
      <!-- 底部数值 -->
      <text x="100" y="170" text-anchor="middle" class="heading-text">
        航向 {{ safeHeading.toFixed(1) }}°
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  heading: number
}>()

const safeHeading = computed(() =>
  isNaN(props.heading) ? 0 : props.heading
)

const directionLabels = ['N', '15', '30', 'NE', '60', '75',
  'E', '105', '120', 'SE', '150', '165',
  'S', '195', '210', 'SW', '240', '255',
  'W', '285', '300', 'NW', '330', '345']

const pointerPoints = '100,15 92,35 108,35'
</script>

<style scoped>
.compass-rose {
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  padding: 4px;
}
.compass-svg {
  width: 160px;
  height: 160px;
}
.direction-label {
  font-size: 7px;
  fill: rgba(255, 255, 255, 0.3);
}
.direction-main {
  font-size: 12px;
  font-weight: 700;
  fill: rgba(255, 255, 255, 0.7);
}
.heading-text {
  font-size: 13px;
  font-weight: 600;
  fill: #e0e6ed;
}
</style>
