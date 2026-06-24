<template>
  <div class="status-bar">
    <span class="indicator">
      <span class="dot" :class="rosConnected ? 'green' : 'red'"></span>
      {{ rosConnected ? 'ROS 已连接' : 'ROS 未连接' }}
    </span>
    <span class="spacer"></span>
    <span class="hold-badge" :class="holdEnabled ? 'active' : ''">
      HOLD {{ holdEnabled ? '开' : '关' }}
    </span>
  </div>
</template>

<script setup lang="ts">
defineProps<{
  rosConnected: boolean
  holdEnabled: boolean
}>()
</script>

<style scoped>
.status-bar {
  display: flex;
  align-items: center;
  padding: 6px 16px;
  background: #141924;
  border-bottom: 1px solid #2a3040;
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
.spacer {
  flex: 1;
}
.hold-badge {
  padding: 2px 10px;
  border-radius: 4px;
  background: #2a3040;
  color: #8899aa;
}
.hold-badge.active {
  background: #00d4ff33;
  color: #00d4ff;
}
</style>
