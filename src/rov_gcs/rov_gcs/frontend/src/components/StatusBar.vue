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
  </div>
</template>

<script setup lang="ts">
defineProps<{
  rosConnected: boolean
  depthHoldEnabled: boolean
  headingHoldEnabled: boolean
}>()
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
</style>
