# GCS HUD 重设计 — 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将 Web GCS 前端从 3 列网格布局改造为视频全屏背景 + 半透明 HUD 叠加的沉浸式界面

**Architecture:** 两层叠加 — z-index 0 视频 `<img>` 全屏 `object-fit: cover`，z-index 1 CSS Grid (3 列 × 3 行) 半透明 HUD。新增 CompassRose 罗盘组件，3 个网格占位组件，改造 4 个现有组件样式，删除 VideoPlaceholder

**Tech Stack:** Vue 3 + TypeScript + Vite + Pinia，纯前端改动

## 全局约束

- 不修改任何后端文件（`backend/`、`composables/useApi.ts`、`composables/useWebSocket.ts`、`composables/useGamepad.ts`）
- 视频流保持现有 `<img src="/api/video/stream">` MJPEG 方案
- HUD 始终可见，不实现自动淡入淡出
- 所有 HUD 组件背景 `rgba(20, 25, 36, 0.65)`，圆角 `8px`
- 强调色保持现有：青 `#00d4ff` / 红 `#ff6b6b` / 黄 `#ffd93d` / 绿 `#4caf50`

---

### Task 1: 扩展 Telemetry Store 接口

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/stores/telemetry.ts`

**Interfaces:**
- Consumes: 无
- Produces: `Telemetry.current_grid: string`, `Telemetry.target_grid: string`, `Telemetry.grid_reached: boolean`

- [ ] **Step 1: 在 Telemetry 接口和 store 初始值中添加 3 个网格字段**

```typescript
// stores/telemetry.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface Telemetry {
  depth: number
  target_depth: number
  depth_hold_enabled: boolean
  vertical_pwm: number
  target_heading: number
  heading_hold_enabled: boolean
  yaw_pwm: number
  lat: number
  lon: number
  yaw: number
  ros_connected: boolean
  current_grid: string
  target_grid: string
  grid_reached: boolean
}

export const useTelemetryStore = defineStore('telemetry', () => {
  const telemetry = ref<Telemetry>({
    depth: 0,
    target_depth: 0,
    depth_hold_enabled: false,
    vertical_pwm: 0,
    target_heading: 0,
    heading_hold_enabled: false,
    yaw_pwm: 0,
    lat: 0,
    lon: 0,
    yaw: 0,
    ros_connected: false,
    current_grid: '',
    target_grid: '',
    grid_reached: false,
  })

  function updateTelemetry(data: Partial<Telemetry>) {
    Object.assign(telemetry.value, data)
  }

  function setRosConnected(v: boolean) {
    telemetry.value.ros_connected = v
  }

  return { telemetry, updateTelemetry, setRosConnected }
})
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/stores/telemetry.ts
git commit -m "feat: add grid fields to Telemetry interface for HUD redesign"
```

---

### Task 2: 创建 CompassRose 罗盘组件

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/CompassRose.vue`

**Interfaces:**
- Consumes: 无（纯 props 驱动）
- Produces: `<CompassRose :heading="number" />` 组件

- [ ] **Step 1: 创建 CompassRose.vue 组件**

```vue
<!-- components/CompassRose.vue -->
<template>
  <div class="compass-rose">
    <svg viewBox="0 0 200 200" class="compass-svg">
      <!-- 外圈刻度环 -->
      <circle
        cx="100" cy="100" r="88"
        fill="none" stroke="rgba(255,255,255,0.12)" stroke-width="1"
      />
      <!-- 刻度线：每 5° 一条短线，每 30° 一条长线 + 方向标签 -->
      <g v-for="deg in 72" :key="deg">
        <line
          v-if="deg % 6 !== 0"
          :x1="100 + 80 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y1="100 + 80 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          :x2="100 + 86 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y2="100 + 86 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          stroke="rgba(255,255,255,0.2)" stroke-width="1"
        />
        <line
          v-if="deg % 6 === 0"
          :x1="100 + 76 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y1="100 + 76 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          :x2="100 + 86 * Math.cos((deg * 5 - 90) * Math.PI / 180)"
          :y2="100 + 86 * Math.sin((deg * 5 - 90) * Math.PI / 180)"
          stroke="rgba(255,255,255,0.35)" stroke-width="1.5"
        />
      </g>
      <!-- 方向标签：每 30° -->
      <g
        v-for="(label, i) in directionLabels"
        :key="label"
        :transform="`rotate(${i * 30}, 100, 100)`"
      >
        <text
          :x="100"
          :y="62"
          text-anchor="middle"
          class="direction-label"
          :class="{ 'direction-main': i % 3 === 0 }"
        >
          {{ label }}
        </text>
      </g>
      <!-- 航向指针（三角形） -->
      <polygon
        :points="pointerPoints"
        fill="#00d4ff"
        :transform="`rotate(${safeHeading}, 100, 100)`"
      />
      <!-- 中心点 -->
      <circle cx="100" cy="100" r="4" fill="#00d4ff" />
      <!-- 底部数值 -->
      <text x="100" y="170" text-anchor="middle" class="heading-text">
        航向 {{ safeHeading.toFixed(1) }}°
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  heading: number
}>()

const safeHeading = computed(() =>
  isNaN(props.heading) ? 0 : props.heading
)

const directionLabels = ['N', '5', '10', 'NE', '20', '25',
  'E', '35', '40', 'SE', '50', '55',
  'S', '65', '70', 'SW', '80', '85',
  'W', '105', '110', 'NW', '120', '125']

const pointerPoints = computed(() => {
  // 三角指针：顶点在圆周，底部两个角靠近圆心
  return '100,15 92,35 108,35'
})
</script>

<style scoped>
.compass-rose {
  display: flex;
  justify-content: center;
  align-items: center;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  padding: 4px;
}
.compass-svg {
  width: 160px;
  height: 160px;
}
.direction-label {
  font-size: 7px;
  fill: rgba(255, 255, 255, 0.3);
}
.direction-main {
  font-size: 12px;
  font-weight: 700;
  fill: rgba(255, 255, 255, 0.7);
}
.heading-text {
  font-size: 13px;
  font-weight: 600;
  fill: #e0e6ed;
}
</style>
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/CompassRose.vue
git commit -m "feat: add CompassRose SVG heading component"
```

---

### Task 3: 创建网格占位组件

**Files:**
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/GridStatus.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/GridTarget.vue`
- Create: `src/rov_gcs/rov_gcs/frontend/src/components/GridReached.vue`

**Interfaces:**
- Consumes: `useTelemetryStore().telemetry` (current_grid, target_grid, grid_reached)
- Produces: `<GridStatus />`, `<GridTarget />`, `<GridReached />` 三个占位组件

- [ ] **Step 1: 创建 GridStatus.vue**

```vue
<!-- components/GridStatus.vue -->
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
```

- [ ] **Step 2: 创建 GridTarget.vue**

```vue
<!-- components/GridTarget.vue -->
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
```

- [ ] **Step 3: 创建 GridReached.vue**

```vue
<!-- components/GridReached.vue -->
<template>
  <div class="grid-reached">
    <span class="label">到达状态</span>
    <span
      class="dot"
      :class="dotColor"
    ></span>
    <span class="text">{{ statusText }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

const store = useTelemetryStore()

const dotColor = computed(() => {
  if (!store.telemetry.target_grid) return 'gray'
  return store.telemetry.grid_reached ? 'green' : 'yellow'
})

const statusText = computed(() => {
  if (!store.telemetry.target_grid) return '未设定'
  return store.telemetry.grid_reached ? '已到达' : '行进中'
})
</script>

<style scoped>
.grid-reached {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.label {
  color: #8899aa;
  font-size: 12px;
}
.dot {
  width: 10px;
  height: 10px;
  border-radius: 50%;
}
.dot.green {
  background: #4caf50;
  box-shadow: 0 0 6px #4caf50;
}
.dot.yellow {
  background: #ffd93d;
  box-shadow: 0 0 6px #ffd93d;
}
.dot.gray {
  background: #4a5568;
}
.text {
  color: #e0e6ed;
  font-size: 13px;
}
</style>
```

- [ ] **Step 4: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 5: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/GridStatus.vue \
        src/rov_gcs/rov_gcs/frontend/src/components/GridTarget.vue \
        src/rov_gcs/rov_gcs/frontend/src/components/GridReached.vue
git commit -m "feat: add grid placeholder components for HUD redesign"
```

---

### Task 4: 改造 StatusBar 样式

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/components/StatusBar.vue`

**Interfaces:**
- Consumes: 无变化（props 不变）
- Produces: 无变化（接口不变，仅样式改变）

- [ ] **Step 1: 替换 StatusBar.vue 的模板和样式**

```vue
<!-- components/StatusBar.vue -->
<template>
  <div class="status-bar">
    <span class="indicator">
      <span class="dot" :class="rosConnected ? 'green' : 'red'"></span>
      ROS
    </span>
    <span class="hold-badge" :class="holdEnabled ? 'active' : ''">
      HOLD
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
  margin-right: 4px;
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
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}
</style>
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/StatusBar.vue
git commit -m "refactor: restyle StatusBar with HUD semi-transparent theme"
```

---

### Task 5: 改造 DepthGauge 样式

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/components/DepthGauge.vue`

**Interfaces:**
- Consumes: 无变化（props 不变）
- Produces: 无变化

- [ ] **Step 1: 替换 DepthGauge.vue 的模板和样式**

```vue
<!-- components/DepthGauge.vue -->
<template>
  <div class="depth-gauge">
    <svg viewBox="0 0 200 200" class="gauge-svg">
      <!-- Background arc -->
      <circle
        cx="100" cy="100" r="85"
        fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="12"
      />
      <!-- Value arc -->
      <circle
        cx="100" cy="100" r="85"
        fill="none"
        :stroke="gaugeColor"
        stroke-width="12"
        stroke-linecap="round"
        :stroke-dasharray="`${arcLength} 534`"
        stroke-dashoffset="0"
        transform="rotate(135, 100, 100)"
      />
      <!-- Depth reading -->
      <text x="100" y="95" text-anchor="middle" class="depth-value">
        {{ depth.toFixed(1) }}
      </text>
      <text x="100" y="115" text-anchor="middle" class="depth-unit">m</text>
      <!-- Target indicator -->
      <text x="100" y="140" text-anchor="middle" class="target-text">
        目标 {{ targetDepth.toFixed(1) }} m
      </text>
    </svg>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{
  depth: number
  targetDepth: number
  maxDepth?: number
}>()

const maxDepth = computed(() => props.maxDepth || 10)
const ratio = computed(() =>
  Math.max(0, Math.min(props.depth / maxDepth.value, 1.0))
)
const arcLength = computed(() => Math.round(ratio.value * 400))

const gaugeColor = computed(() => {
  if (ratio.value > 0.7) return '#ff6b6b'
  if (ratio.value > 0.4) return '#ffd93d'
  return '#00d4ff'
})
</script>

<style scoped>
.depth-gauge {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 8px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.gauge-svg {
  width: 140px;
  height: 140px;
}
.depth-value {
  font-size: 32px;
  font-weight: 700;
  fill: #e0e6ed;
}
.depth-unit {
  font-size: 13px;
  fill: #8899aa;
}
.target-text {
  font-size: 11px;
  fill: #8899aa;
}
</style>
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/DepthGauge.vue
git commit -m "refactor: restyle DepthGauge with HUD semi-transparent theme, add maxDepth prop"
```

---

### Task 6: 改造 TelemetryPanel 样式

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/components/TelemetryPanel.vue`

**Interfaces:**
- Consumes: 无变化（props 不变）
- Produces: 无变化

- [ ] **Step 1: 替换 TelemetryPanel.vue 的模板和样式**

```vue
<!-- components/TelemetryPanel.vue -->
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
  flex-wrap: wrap;
  gap: 4px;
  padding: 6px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.telem-item {
  display: flex;
  align-items: center;
  gap: 4px;
  padding: 2px 6px;
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
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/TelemetryPanel.vue
git commit -m "refactor: restyle TelemetryPanel horizontal wrap for HUD layout"
```

---

### Task 7: 改造 ControlPanel 样式

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/components/ControlPanel.vue`

**Interfaces:**
- Consumes: 无变化（props 不变）
- Produces: 无变化

- [ ] **Step 1: 替换 ControlPanel.vue 的模板和样式**

模板逻辑不变，仅改 `<style scoped>` 和调整模板中 `error` 的显示位置：

```vue
<!-- components/ControlPanel.vue -->
<template>
  <div class="control-panel">
    <p v-if="error" class="error">{{ error }}</p>

    <!-- 深度控制 -->
    <div class="ctrl-group">
      <label>目标深度 (m)</label>
      <div class="input-row">
        <input
          v-model.number="depthTargetInput"
          type="number"
          step="0.1"
          min="0"
          placeholder="深度"
          @keyup.enter="handleSetDepthTarget"
        />
        <button :disabled="sending" @click="handleSetDepthTarget">设定</button>
      </div>
    </div>
    <button
      class="hold-btn"
      :class="depthHoldEnabled ? 'active' : ''"
      :disabled="sending"
      @click="handleDepthHold"
    >
      {{ depthHoldEnabled ? '关闭定深' : '开启定深' }}
    </button>

    <!-- 航向控制 -->
    <div class="ctrl-group">
      <label>目标航向 (°)</label>
      <div class="input-row">
        <input
          v-model.number="headingTargetInput"
          type="number"
          step="1"
          min="0"
          max="360"
          placeholder="航向"
          @keyup.enter="handleSetHeadingTarget"
        />
        <button :disabled="sending" @click="handleSetHeadingTarget">设定</button>
      </div>
    </div>
    <button
      class="hold-btn"
      :class="headingHoldEnabled ? 'active' : ''"
      :disabled="sending"
      @click="handleHeadingHold"
    >
      {{ headingHoldEnabled ? '关闭定航' : '开启定航' }}
    </button>

    <!-- Arm/Disarm -->
    <button
      class="arm-btn"
      :class="armed ? 'armed' : 'disarmed'"
      :disabled="sending"
      @click="handleArmToggle"
    >
      {{ armed ? '🔴 Disarm' : '🟢 Arm' }}
    </button>

    <div class="gamepad-status">
      <template v-if="gamepadConnected">🎮 手柄已连接</template>
      <template v-else>🎮 按手柄键激活</template>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useApi } from '../composables/useApi'
import { useTelemetryStore } from '../stores/telemetry'

const props = defineProps<{ gamepadConnected: boolean }>()
const store = useTelemetryStore()
const { setDepthTarget, toggleDepthHold, setHeadingTarget, toggleHeadingHold, arm, disarm } =
  useApi()
const depthTargetInput = ref(0)
const headingTargetInput = ref(0)
const sending = ref(false)
const error = ref('')
const armed = ref(false)

const depthHoldEnabled = computed(
  () => store.telemetry.depth_hold_enabled
)
const headingHoldEnabled = computed(
  () => store.telemetry.heading_hold_enabled
)

// ----- depth -----

async function handleSetDepthTarget() {
  error.value = ''
  if (depthTargetInput.value < 0) {
    error.value = '深度不能为负数'
    return
  }
  sending.value = true
  try {
    await setDepthTarget(depthTargetInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleDepthHold() {
  error.value = ''
  sending.value = true
  try {
    await toggleDepthHold()
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}

// ----- arm/disarm -----

async function handleArmToggle() {
  error.value = ''
  sending.value = true
  try {
    if (armed.value) {
      await disarm()
      armed.value = false
    } else {
      await arm()
      armed.value = true
    }
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}

// ----- heading -----

async function handleSetHeadingTarget() {
  error.value = ''
  sending.value = true
  try {
    await setHeadingTarget(headingTargetInput.value)
  } catch (e: any) {
    error.value = e.message || '设定失败'
  } finally {
    sending.value = false
  }
}

async function handleHeadingHold() {
  error.value = ''
  sending.value = true
  try {
    await toggleHeadingHold()
  } catch (e: any) {
    error.value = e.message || '操作失败'
  } finally {
    sending.value = false
  }
}
</script>

<style scoped>
.control-panel {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 10px 14px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
}
.ctrl-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.ctrl-group label {
  color: #8899aa;
  font-size: 12px;
}
.input-row {
  display: flex;
  gap: 6px;
}
input {
  width: 90px;
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
  padding: 4px 10px;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 12px;
  background: #00d4ff;
  color: #0a0e17;
  font-weight: 600;
}
button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
.hold-btn {
  background: #2a3040;
  color: #8899aa;
}
.hold-btn.active {
  background: rgba(0, 212, 255, 0.2);
  color: #00d4ff;
}
.error {
  color: #ff6b6b;
  font-size: 11px;
  margin: 0;
}
.arm-btn {
  background: #2a3040;
  color: #8899aa;
  font-weight: 600;
}
.arm-btn.armed {
  background: rgba(255, 107, 107, 0.2);
  color: #ff6b6b;
}
.arm-btn.disarmed {
  background: rgba(76, 175, 80, 0.2);
  color: #4caf50;
}
.gamepad-status {
  font-size: 11px;
  color: #8899aa;
}
</style>
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/components/ControlPanel.vue
git commit -m "refactor: restyle ControlPanel vertical layout for HUD overlay"
```

---

### Task 8: 重构 App.vue（视频层 + HUD 网格叠加）

**Files:**
- Modify: `src/rov_gcs/rov_gcs/frontend/src/App.vue`

**Interfaces:**
- Consumes: CompassRose (Task 2), GridStatus (Task 3), GridTarget (Task 3), GridReached (Task 3), StatusBar (Task 4), DepthGauge (Task 5), TelemetryPanel (Task 6), ControlPanel (Task 7)
- Produces: 完整 HUD 布局

- [ ] **Step 1: 替换 App.vue**

```vue
<!-- App.vue -->
<template>
  <div id="gcs-app">
    <!-- 视频层 -->
    <div class="video-layer">
      <img
        v-if="rosConnected && !streamError"
        :src="streamUrl"
        class="video-stream"
        @error="onStreamError"
      />
      <div v-else class="video-fallback">
        <svg
          width="48" height="48" viewBox="0 0 24 24"
          fill="none" stroke="#4a5568" stroke-width="1.5"
        >
          <rect x="2" y="4" width="20" height="16" rx="2" />
          <path d="M10 9l5 3-5 3V9z" fill="#4a5568" />
        </svg>
        <p>{{ streamError ? '视频信号丢失' : 'ROS 未连接' }}</p>
      </div>
    </div>

    <!-- HUD 叠加层 -->
    <div class="hud-overlay">
      <div class="hud-top-left">
        <StatusBar
          :ros-connected="rosConnected"
          :hold-enabled="store.telemetry.depth_hold_enabled || store.telemetry.heading_hold_enabled"
        />
      </div>
      <div class="hud-top-right">
        <TelemetryPanel
          :lat="store.telemetry.lat"
          :lon="store.telemetry.lon"
          :yaw="store.telemetry.yaw"
          :vertical-pwm="store.telemetry.vertical_pwm"
          :yaw-pwm="store.telemetry.yaw_pwm"
        />
      </div>
      <div class="hud-mid-left">
        <DepthGauge
          :depth="store.telemetry.depth"
          :target-depth="store.telemetry.target_depth"
        />
      </div>
      <div class="hud-center">
        <CompassRose :heading="store.telemetry.yaw" />
      </div>
      <div class="hud-mid-right">
        <ControlPanel :gamepad-connected="gamepadConnected" />
      </div>
      <div class="hud-bot-left">
        <GridStatus />
      </div>
      <div class="hud-bot-center">
        <GridTarget />
      </div>
      <div class="hud-bot-right">
        <GridReached />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import StatusBar from './components/StatusBar.vue'
import DepthGauge from './components/DepthGauge.vue'
import TelemetryPanel from './components/TelemetryPanel.vue'
import ControlPanel from './components/ControlPanel.vue'
import CompassRose from './components/CompassRose.vue'
import GridStatus from './components/GridStatus.vue'
import GridTarget from './components/GridTarget.vue'
import GridReached from './components/GridReached.vue'
import { useWebSocket } from './composables/useWebSocket'
import { useGamepad } from './composables/useGamepad'
import { useTelemetryStore } from './stores/telemetry'

const store = useTelemetryStore()
const gamepadConnected = ref(false)
const streamError = ref(false)
const streamUrl = '/api/video/stream'

const rosConnected = computed(() => store.telemetry.ros_connected)

const wsUrl = `ws://${window.location.host}/ws`
const { connect, close, send } = useWebSocket(wsUrl)

;(window as any).__gcsSend = send
;(window as any).__gcsSetGamepadConnected = (v: boolean) => {
  gamepadConnected.value = v
}

function onStreamError() {
  streamError.value = true
}

onMounted(() => {
  connect()
  try {
    const gamepad = useGamepad({
      onData: (data) => {
        send({ type: 'joystick', data })
      },
      onConnect: (v) => {
        gamepadConnected.value = v
      },
    })
    gamepad.start()
  } catch (e) {
    console.warn('Gamepad API unavailable:', e)
  }
})

onUnmounted(() => close())
</script>

<style>
/* 全局样式重置 */
html, body {
  margin: 0;
  padding: 0;
  overflow: hidden;
  background: #0a0e17;
}

#gcs-app {
  position: relative;
  width: 100vw;
  height: 100vh;
  overflow: hidden;
}

/* ---- 视频层 ---- */
.video-layer {
  position: fixed;
  inset: 0;
  z-index: 0;
}
.video-stream {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.video-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  background: #0a0e17;
  gap: 12px;
}
.video-fallback p {
  color: #4a5568;
  font-size: 14px;
}

/* ---- HUD 叠加层 ---- */
.hud-overlay {
  position: fixed;
  inset: 0;
  z-index: 1;
  pointer-events: none;
  display: grid;
  grid-template-columns: 1fr 2fr 1fr;
  grid-template-rows: auto 1fr auto;
  gap: 8px;
  padding: 8px;
}

.hud-overlay > * {
  pointer-events: auto;
}

.hud-top-left {
  grid-column: 1;
  grid-row: 1;
  justify-self: start;
}

.hud-top-right {
  grid-column: 3;
  grid-row: 1;
  justify-self: end;
}

.hud-mid-left {
  grid-column: 1;
  grid-row: 2;
  align-self: center;
  justify-self: start;
}

.hud-center {
  grid-column: 2;
  grid-row: 2;
  align-self: end;
  justify-self: center;
}

.hud-mid-right {
  grid-column: 3;
  grid-row: 2;
  align-self: center;
  justify-self: end;
}

.hud-bot-left {
  grid-column: 1;
  grid-row: 3;
  justify-self: start;
}

.hud-bot-center {
  grid-column: 2;
  grid-row: 3;
  justify-self: center;
}

.hud-bot-right {
  grid-column: 3;
  grid-row: 3;
  justify-self: end;
}

/* 小屏适配 */
@media (max-width: 320px) {
  .hud-mid-left,
  .hud-center {
    display: none;
  }
  .hud-overlay {
    grid-template-columns: 1fr 1fr;
  }
}
</style>
```

- [ ] **Step 2: 验证 TypeScript 编译通过**

```bash
cd src/rov_gcs/rov_gcs/frontend && npx vue-tsc --noEmit 2>&1 | head -20
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/src/App.vue
git commit -m "refactor: rewrite App.vue with video layer + HUD grid overlay"
```

---

### Task 9: 删除 VideoPlaceholder 组件

**Files:**
- Delete: `src/rov_gcs/rov_gcs/frontend/src/components/VideoPlaceholder.vue`

**Interfaces:**
- Consumes: App.vue 已不再引用该组件（Task 8 已移除 import）
- Produces: 无

- [ ] **Step 1: 删除文件**

```bash
rm src/rov_gcs/rov_gcs/frontend/src/components/VideoPlaceholder.vue
```

- [ ] **Step 2: 确认 App.vue 中无残留引用**

```bash
grep -r "VideoPlaceholder" src/rov_gcs/rov_gcs/frontend/src/ || echo "No references found — safe to proceed"
```

- [ ] **Step 3: Commit**

```bash
cd /home/jetson/whj/rov-ros
git rm src/rov_gcs/rov_gcs/frontend/src/components/VideoPlaceholder.vue
git commit -m "refactor: remove VideoPlaceholder, replaced by full-screen video layer in App.vue"
```

---

### Task 10: 构建并验证

**Files:**
- 无新建/修改（仅验证）

**Interfaces:**
- Consumes: 所有前述 Task 的产物
- Produces: 构建产物 `src/rov_gcs/rov_gcs/frontend/dist/`

- [ ] **Step 1: 构建前端**

```bash
cd /home/jetson/whj/rov-ros/src/rov_gcs/rov_gcs/frontend
npm run build
```

**预期**：`✓ built in X.XXs`，无错误

- [ ] **Step 2: 检查构建产物包含新增组件**

```bash
ls -la dist/
# 应包含 index.html 和 assets/ 目录
```

- [ ] **Step 3: 验证 TypeScript 无错误**

```bash
cd /home/jetson/whj/rov-ros/src/rov_gcs/rov_gcs/frontend
npx vue-tsc --noEmit
```

**预期**：无输出（无错误）

- [ ] **Step 4: Commit**

```bash
cd /home/jetson/whj/rov-ros
git add src/rov_gcs/rov_gcs/frontend/dist/ || true
git commit -m "build: verify HUD redesign frontend build passes"
```
