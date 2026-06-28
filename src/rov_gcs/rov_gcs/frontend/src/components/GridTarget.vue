<template>
  <div class="grid-target">
    <input
      v-model="targetInput"
      type="text"
      placeholder="输入目标网格 ID"
      @keyup.enter="handleSetTarget"
    />
    <button @click="handleSetTarget">设定</button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const targetInput = ref('')

function handleSetTarget() {
  // 预留：后续对接 POST /api/grid/set_target
  console.log('Grid target set (placeholder):', targetInput.value)
}
</script>

<style scoped>
.grid-target {
  display: flex;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
input {
  width: 120px;
  padding: 4px 8px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: #0a0e17;
  color: #e0e6ed;
  font-size: 13px;
}
input:focus {
  outline: none;
  border-color: #00d4ff;
}
button {
  padding: 4px 12px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 13px;
  background: #00d4ff;
  color: #0a0e17;
  font-weight: 600;
}
</style>
