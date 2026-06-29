<template>
  <div class="grid-map" v-if="hasGrid">
    <div class="grid-title">网格地图</div>
    <div
      class="grid-container"
      :style="gridStyle"
    >
      <div
        v-for="(cell, idx) in cells"
        :key="idx"
        class="grid-cell"
        :class="cellClass(cell.row, cell.col)"
        :title="cellTooltip(cell.row, cell.col)"
      >
        <span class="cell-label">{{ cell.row }},{{ cell.col }}</span>
      </div>
    </div>
  </div>
  <div class="grid-map grid-map--empty" v-else>
    <span class="empty-text">等待网格数据...</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

const store = useTelemetryStore()

const hasGrid = computed(() => {
  const t = store.telemetry
  return t.grid_rows > 0 && t.grid_cols > 0
})

interface Cell {
  row: number
  col: number
}

const cells = computed<Cell[]>(() => {
  const rows = store.telemetry.grid_rows
  const cols = store.telemetry.grid_cols
  const result: Cell[] = []
  for (let r = 0; r < rows; r++) {
    for (let c = 0; c < cols; c++) {
      result.push({ row: r, col: c })
    }
  }
  return result
})

const gridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${store.telemetry.grid_cols}, 1fr)`,
  gridTemplateRows: `repeat(${store.telemetry.grid_rows}, 1fr)`,
}))

function cellClass(row: number, col: number): string {
  const t = store.telemetry
  const isCurrent = row === t.grid_current_row && col === t.grid_current_col
  const isTarget = row === t.grid_target_row && col === t.grid_target_col

  if (isCurrent && isTarget && t.grid_reached) return 'cell-reached'
  if (isCurrent && isTarget) return 'cell-current-target'
  if (isCurrent) return 'cell-current'
  if (isTarget) return 'cell-target'
  return 'cell-normal'
}

function cellTooltip(row: number, col: number): string {
  const t = store.telemetry
  const parts = [`R${row}C${col}`]
  if (row === t.grid_current_row && col === t.grid_current_col) {
    parts.push('(当前位置)')
  }
  if (row === t.grid_target_row && col === t.grid_target_col) {
    parts.push('(目标)')
  }
  return parts.join(' ')
}
</script>

<style scoped>
.grid-map {
  padding: 10px 14px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.grid-map--empty {
  align-items: center;
  justify-content: center;
  min-width: 160px;
  min-height: 60px;
}
.empty-text {
  color: #5a6a7e;
  font-size: 13px;
}
.grid-title {
  color: #8899aa;
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.grid-container {
  display: grid;
  gap: 3px;
}
.grid-cell {
  aspect-ratio: 1;
  min-width: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 3px;
  cursor: default;
  transition: background 0.2s;
}
.cell-label {
  font-size: 10px;
  color: #8899aa;
  font-family: monospace;
  pointer-events: none;
}

/* Cell states */
.cell-normal {
  background: rgba(42, 48, 64, 0.5);
  border: 1px solid #2a3040;
}
.cell-current {
  background: rgba(0, 212, 255, 0.2);
  border: 1px solid #00d4ff;
}
.cell-current .cell-label {
  color: #00d4ff;
}
.cell-target {
  background: rgba(255, 217, 61, 0.2);
  border: 1px solid #ffd93d;
}
.cell-target .cell-label {
  color: #ffd93d;
}
.cell-current-target {
  background: rgba(255, 217, 61, 0.25);
  border: 1px solid #ffd93d;
  box-shadow: 0 0 4px rgba(0, 212, 255, 0.4);
}
.cell-current-target .cell-label {
  color: #ffd93d;
}
.cell-reached {
  background: rgba(76, 175, 80, 0.25);
  border: 1px solid #4caf50;
  box-shadow: 0 0 6px rgba(76, 175, 80, 0.4);
}
.cell-reached .cell-label {
  color: #4caf50;
}
</style>
