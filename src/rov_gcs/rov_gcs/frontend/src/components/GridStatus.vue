<template>
  <div class="grid-status">
    <span class="label">当前网格</span>
    <span class="value">{{ store.telemetry.current_grid || '---' }}</span>
  </div>
</template>

<script setup lang="ts">
import { useTelemetryStore } from '../stores/telemetry'
const store = useTelemetryStore()
</script>

<style scoped>
.grid-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.label {
  color: #8899aa;
  font-size: 12px;
}
.value {
  color: #00d4ff;
  font-size: 14px;
  font-weight: 600;
  font-family: monospace;
}
</style>
