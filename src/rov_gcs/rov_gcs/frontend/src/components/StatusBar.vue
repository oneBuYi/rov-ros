<template>
  <div class="status-bar">
    <span class="indicator">
      <span class="dot" :class="rosConnected ? 'green' : 'red'"></span>
      ROS
    </span>
    <span class="hold-badge" :class="depthHoldEnabled ? 'active' : ''">
      定深
    </span>
    <span class="hold-badge" :class="headingHoldEnabled ? 'active' : ''">
      定航
    </span>
    <button
      v-if="fullscreenSupported"
      class="fs-btn"
      :title="isFullscreen ? '退出全屏' : '全屏'"
      @click="toggle"
    >
      <!-- 进入全屏图标 -->
      <svg v-if="!isFullscreen" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M8 3H5a2 2 0 00-2 2v3m18 0V5a2 2 0 00-2-2h-3m0 18h3a2 2 0 002-2v-3M3 16v3a2 2 0 002 2h3" />
      </svg>
      <!-- 退出全屏图标 -->
      <svg v-else width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M8 3v3a2 2 0 01-2 2H3m18 0h-3a2 2 0 01-2-2V3m0 18v-3a2 2 0 012-2h3M3 16h3a2 2 0 012 2v3" />
      </svg>
    </button>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useFullscreen } from '../composables/useFullscreen'

defineProps<{
  rosConnected: boolean
  depthHoldEnabled: boolean
  headingHoldEnabled: boolean
}>()

const { isFullscreen, toggle } = useFullscreen()

const fullscreenSupported = computed(() => {
  return typeof document !== 'undefined' && document.documentElement.requestFullscreen
})
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 4px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  font-size: 13px;
}
.dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
}
.green {
  background: #00e676;
  box-shadow: 0 0 6px #00e676;
}
.red {
  background: #ff1744;
  box-shadow: 0 0 6px #ff1744;
}
.hold-badge {
  padding: 1px 8px;
  border-radius: 4px;
  background: #2a3040;
  color: #8899aa;
  font-size: 11px;
}
.hold-badge.active {
  background: #00d4ff33;
  color: #00d4ff;
}
.fs-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: transparent;
  color: #8899aa;
  cursor: pointer;
  margin-left: auto;
}
.fs-btn:hover {
  color: #00d4ff;
  border-color: #00d4ff;
}
</style>
