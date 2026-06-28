# GCS HUD 重设计 — 设计文档

**日期**：2026-06-28
**范围**：前端 only，不修改后端或数据逻辑

## 动机

参考 OpenROV Cockpit 的设计理念（视频全屏背景 + 半透明 HUD 叠加），将当前 3 列网格布局的 Web 上位机改造为沉浸式 HUD 风格界面。同时预留后续池壁网格巡检功能的位置和接口。

## 设计约束

- 只改前端（Vue 3 + TypeScript + CSS），后端和 `rosbridge` 通信层不动
- 视频流保持现有 MJPEG `<img>` 方案（`/api/video/stream`）
- HUD 始终可见，不实现自动淡入淡出
- 环绕式布局，罗盘居中偏下作为视觉锚点

---

## 架构

### 层级

```
┌─ z-index: 0 ──────────────────────────────────┐
│           <img> 视频流                          │
│       position: fixed; object-fit: cover        │
├─ z-index: 1 ───────────────────────────────────┤
│  CSS Grid 叠加层 (3 列 × 3 行)                  │
│  pointer-events: none（子元素各自 auto）         │
│                                                  │
│ ┌───────────┬────────────┬──────────────┐       │
│ │ StatusBar │    (空)    │ TelemetryPanel│      │
│ ├───────────┼────────────┼──────────────┤       │
│ │ DepthGauge│ CompassRose│ ControlPanel │       │
│ │ (竖排)    │ (居中偏下) │ (竖排)        │       │
│ ├───────────┼────────────┼──────────────┤       │
│ │ GridStatus│ GridTarget │ GridReached  │       │
│ └───────────┴────────────┴──────────────┘       │
└──────────────────────────────────────────────────┘
```

### Grid 定义

- 列：`1fr 2fr 1fr`（两侧窄、中间宽给罗盘和视频主要区域）
- 行：`auto 1fr auto`（中行撑满，上下行内容自适应）
- 视频层：`position: fixed; inset: 0; object-fit: cover; z-index: 0`
- 叠加层：`position: fixed; inset: 0; z-index: 1; pointer-events: none`

### 半透明视觉规范

- 组件背景：`rgba(20, 25, 36, 0.65)`
- 文字主色：`#e0e6ed`
- 文字次色：`#8899aa`
- 强调色保持现有：青 `#00d4ff` / 红 `#ff6b6b` / 黄 `#ffd93d` / 绿 `#4caf50`
- 圆角：`8px`

---

## 组件

### 新增组件

#### CompassRose.vue

圆形 SVG 航向罗盘，直径约 160px。

- **Props**：`heading: number`（0-360°，来自 `store.telemetry.yaw`）
- **视觉**：外圈 360° 刻度环（每 5° 短线，每 30° 标注方向），中心三角形指针旋转指向当前航向，底部文字显示数值
- **防御**：`isNaN(heading) ? 0 : heading`
- **位置**：grid-row 2, grid-col 2，`justify-self: center; align-self: end`
- **无外部依赖**

#### 网格预留组件（3 个占位）

均为功能占位，本次只渲染静态 UI 框架：

- **GridStatus.vue**：显示 `store.telemetry.current_grid`（空字符串时显示 "---"）
- **GridTarget.vue**：输入框 + 设定按钮（点击无实际 API 调用，留 `@click` 空函数）
- **GridReached.vue**：状态指示灯（绿/黄/灰三色圆点）

### 改造组件

#### App.vue

- 移除 `max-width: 960px`、overflow 控制、滚动
- 模板顶部添加 `<img>` 视频层
- 原有 `dashboard` 改为 HUD Grid 叠加层
- 视频加载失败 / ROS 未连接时显示备用暗色背景

#### StatusBar.vue

- 改为横向紧凑排列（`gap: 12px`），移除 `spacer`
- 半透明圆角背景

#### DepthGauge.vue

- 外层容器宽度缩小至 140px
- 半透明圆角背景
- `maxDepth` 改为 prop（默认 10）

#### TelemetryPanel.vue

- 从竖排改为横向 `flex-wrap`，节省垂直空间
- 每个遥测项缩小字体和 padding
- 半透明圆角背景

#### ControlPanel.vue

- 从横向 `flex-wrap` 改为竖排
- 半透明圆角背景

### 删除组件

- **VideoPlaceholder.vue**：视频渲染逻辑移入 App.vue

---

## 数据流

### 现有数据流（不变）

```
浏览器 (Vue 3) ←→ FastAPI (:8000) ←→ rosbridge (:9090) ←→ ROS2
   ↑                  ↑
Gamepad API      托管前端静态文件
```

- `composables/useWebSocket.ts` — 不变
- `composables/useApi.ts` — 不变
- `composables/useGamepad.ts` — 不变
- `backend/*` — 不变

### Telemetry 接口扩展

在 `stores/telemetry.ts` 中新增 3 个字段（仅前端接口，后端暂不对接）：

```typescript
interface Telemetry {
  // ... 现有字段保留 ...
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
  // 新增（网格巡检预留）
  current_grid: string       // 当前网格 ID，空字符串 = 不在任何网格
  target_grid: string        // 目标网格 ID
  grid_reached: boolean      // 是否到达目标网格
}
```

初始值：`current_grid: ''`, `target_grid: ''`, `grid_reached: false`

---

## 边界情况

| 场景 | 处理 |
|------|------|
| 视频流加载失败 | 视频层显示暗色背景 + "视频信号丢失"（复用 `streamError` 逻辑） |
| ROS 未连接 | 视频层显示暗色背景 + "ROS 未连接"，HUD 数值保持 0 |
| 窗口宽度 < 320px | 罗盘和深度表 `display: none`，保留控制和视频 |
| `heading` 为 NaN/undefined | `CompassRose` 默认指向 0°（北） |
| `depth` < 0 | `DepthGauge` 比率 clamp 到 0 |
| 网格字段空字符串 | 显示 "---"，指示灯灰色 |

---

## 测试

- **手动验证**：`npm run build` → `ros2 launch rov_gcs gcs.launch.py` → 浏览器确认布局和视频叠加
- **开发调试**：`npm run dev` 可直接查看 CompassRose 和其他组件渲染效果
- **无自动化测试**（项目当前无测试基础设施）

---

## 文件变更清单

| 文件 | 操作 |
|------|------|
| `src/App.vue` | 重构 |
| `src/components/StatusBar.vue` | 改样式 |
| `src/components/DepthGauge.vue` | 改样式 |
| `src/components/TelemetryPanel.vue` | 改样式 |
| `src/components/ControlPanel.vue` | 改样式 |
| `src/components/CompassRose.vue` | **新增** |
| `src/components/GridStatus.vue` | **新增** |
| `src/components/GridTarget.vue` | **新增** |
| `src/components/GridReached.vue` | **新增** |
| `src/components/VideoPlaceholder.vue` | 删除 |
| `src/stores/telemetry.ts` | 新增 3 个字段 |
| `src/composables/*` | 不动 |
| `backend/*` | 不动 |

---

## 后续扩展

网格巡检功能的完整实现在本次范围之外。后续需要：

1. 后端 ROS node 实现网格判定逻辑（球心 + 半径 + 深度约束）
2. 后端 FastAPI 添加 `POST /api/grid/set_target` 和 telemetry 中的 `current_grid`/`target_grid`/`grid_reached` 字段
3. 前端 `GridTarget.vue` 接通 API，`GridStatus`/`GridReached` 对接 WebSocket telemetry
