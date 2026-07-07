<template>
  <div class="telemetry-panel">
    <div class="telem-item">
      <span class="label">纬度</span>
      <span class="value">{{ lat.toFixed(7) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">经度</span>
      <span class="value">{{ lon.toFixed(7) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">偏航角</span>
      <span class="value">{{ yaw.toFixed(1) }}°</span>
    </div>
    <div class="telem-item">
      <span class="label">深度PID</span>
      <span class="value">{{ verticalPwm.toFixed(1) }}</span>
    </div>
    <div class="telem-item">
      <span class="label">航向PID</span>
      <span class="value">{{ yawPwm.toFixed(1) }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  lat: number
  lon: number
  yaw: number
  verticalPwm: number
  yawPwm: number
}>()
</script>

<style scoped>
.telemetry-panel {
  display: flex;
  flex-wrap: nowrap;
  gap: 4px;
  padding: 6px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  overflow: hidden;
  user-select: none;
}

.telem-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
  white-space: nowrap;
  flex-shrink: 0;
}

.label {
  color: #8899aa;
  font-size: 11px;
}

.value {
  color: #e0e6ed;
  font-size: 12px;
  font-weight: 600;
  font-family: monospace;
}
</style>
