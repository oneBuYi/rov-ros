<template>
  <div class="grid-target">
    <input
      v-model.number="targetRow"
      type="number"
      min="0"
      placeholder="行"
      class="grid-input"
      @keyup.enter="handleSetTarget"
    />
    <input
      v-model.number="targetCol"
      type="number"
      min="0"
      placeholder="列"
      class="grid-input"
      @keyup.enter="handleSetTarget"
    />
    <button @click="handleSetTarget" :disabled="!canSet">设定</button>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useApi } from '../composables/useApi'

const { setGridTarget } = useApi()

const targetRow = ref<number | null>(null)
const targetCol = ref<number | null>(null)

const canSet = computed(() => targetRow.value != null && targetCol.value != null)

async function handleSetTarget() {
  if (!canSet.value) return
  try {
    await setGridTarget(targetRow.value!, targetCol.value!)
  } catch (e: any) {
    console.error('Grid target set failed:', e.message)
  }
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
.grid-input {
  width: 54px;
  padding: 4px 8px;
  border: 1px solid #2a3040;
  border-radius: 4px;
  background: #0a0e17;
  color: #e0e6ed;
  font-size: 13px;
}
.grid-input:focus {
  outline: none;
  border-color: #00d4ff;
}
.grid-input::placeholder {
  color: #5a6a7e;
  font-size: 12px;
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
button:disabled {
  background: #2a3040;
  color: #5a6a7e;
  cursor: not-allowed;
}
</style>
