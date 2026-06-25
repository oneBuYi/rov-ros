<template>
  <div class="telemetry-panel">
    <div class="telem-item">
      <span class="label">纬度</span>
      <span class="value">{{ lat.toFixed(4) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">经度</span>
      <span class="value">{{ lon.toFixed(4) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">偏航角</span>
      <span class="value">{{ yaw.toFixed(1) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">PID 输出</span>
      <span class="value">{{ verticalPwm.toFixed(1) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  lat: number
  lon: number
  yaw: number
  verticalPwm: number
}>()
</script>

<style scoped>
.telemetry-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 8px;
}
.telem-item {
  display: flex;
  justify-content: space-between;
  padding: 6px 12px;
  background: #141924;
  border-radius: 6px;
}
.label {
  color: #8899aa;
  font-size: 13px;
}
.value {
  color: #e0e6ed;
  font-size: 14px;
  font-weight: 600;
  font-family: monospace;
}
</style>
