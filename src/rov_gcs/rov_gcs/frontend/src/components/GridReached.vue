<template>
  <div class="grid-reached">
    <span class="label">到达状态</span>
    <span
      class="dot"
      :class="dotColor"
    ></span>
    <span class="text">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

const store = useTelemetryStore()

const dotColor = computed(() => {
  if (!store.telemetry.target_grid) return 'gray'
  return store.telemetry.grid_reached ? 'green' : 'yellow'
})

const statusText = computed(() => {
  if (!store.telemetry.target_grid) return '未设定'
  return store.telemetry.grid_reached ? '已到达' : '行进中'
})
</script>

<style scoped>
.grid-reached {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.label {
  color: #8899aa;
  font-size: 12px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.green {
  background: #4caf50;
  box-shadow: 0 0 6px #4caf50;
}
.dot.yellow {
  background: #ffd93d;
  box-shadow: 0 0 6px #ffd93d;
}
.dot.gray {
  background: #4a5568;
}
.text {
  color: #e0e6ed;
  font-size: 13px;
}
</style>
