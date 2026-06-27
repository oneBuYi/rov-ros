<template>
  <div class="video-container">
    <img
      v-if="rosConnected"
      :src="streamUrl"
      alt="Camera Stream"
      class="video-stream"
      @error="onStreamError"
    />
    <div v-else class="placeholder-content">
      <svg
        width="48" height="48" viewBox="0 0 24 24"
        fill="none" stroke="#4a5568" stroke-width="1.5"
      >
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M10 9l5 3-5 3V9z" fill="#4a5568" />
      </svg>
      <p>ROS 未连接</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

const store = useTelemetryStore()
const streamError = ref(false)

const rosConnected = computed(() => store.telemetry.ros_connected && !streamError.value)
const streamUrl = '/api/video/stream'

function onStreamError() {
  streamError.value = true
}
</script>

<style scoped>
.video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 200px;
  background: #141924;
  border: 1px solid #2a3040;
  border-radius: 8px;
  margin: 8px 0;
  overflow: hidden;
}
.video-stream {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.placeholder-content {
  text-align: center;
}
.placeholder-content p {
  margin-top: 8px;
  color: #4a5568;
  font-size: 13px;
}
</style>
