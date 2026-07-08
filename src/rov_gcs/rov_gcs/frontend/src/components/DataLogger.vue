<template>
  <div class="data-logger">
    <!-- 文件夹选择 -->
    <div class="logger-row">
      <button
        class="logger-btn folder-btn"
        @click="selectFolder"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 19a2 2 0 01-2 2H4a2 2 0 01-2-2V5a2 2 0 012-2h5l2 3h9a2 2 0 012 2z" />
        </svg>
        <span>{{ folderName }}</span>
      </button>
    </div>

    <!-- 记录按钮 -->
    <div class="logger-row save-row">
      <button
        class="logger-btn save-btn"
        @click="saveRecord"
      >
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="9" />
          <path d="M12 7v10M7 12h10" />
        </svg>
        <span>记录</span>
      </button>
      <Transition name="status-fade">
        <span
          v-if="lastStatus"
          :class="lastStatusOk ? 'status-ok' : 'status-err'"
          class="status-text"
        >{{ lastStatus }}</span>
      </Transition>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useTelemetryStore } from '../stores/telemetry'

const store = useTelemetryStore()

const dirHandle = ref<FileSystemDirectoryHandle | null>(null)
const folderName = ref('选择目录')
const lastStatus = ref('')
const lastStatusOk = ref(true)
let statusTimer: ReturnType<typeof setTimeout> | null = null

/** 显示状态，3 秒后自动消失 */
function showStatus(msg: string, ok: boolean) {
  if (statusTimer) clearTimeout(statusTimer)
  lastStatus.value = msg
  lastStatusOk.value = ok
  statusTimer = setTimeout(() => {
    lastStatus.value = ''
  }, 3000)
}

/** 检查 File System Access API 是否可用 (需要安全上下文: HTTPS 或 localhost) */
const apiSupported = computed(() => {
  try {
    return 'showDirectoryPicker' in window
  } catch {
    return false
  }
})

/** 选择文件夹 */
async function selectFolder() {
  if (!apiSupported.value) {
    // 安全上下文不可用时的提示
    alert(
      '文件夹选择需要安全上下文（HTTPS 或 localhost）。\n' +
      '当前通过非安全连接访问，将使用浏览器下载方式保存文件。'
    )
    return
  }

  // 记录当前是否全屏（showDirectoryPicker 系统弹窗会导致退出全屏）
  const wasFullscreen = !!document.fullscreenElement

  try {
    const handle = await window.showDirectoryPicker({ mode: 'readwrite' })
    dirHandle.value = handle
    folderName.value = handle.name
    lastStatus.value = ''
  } catch (err: any) {
    if (err.name !== 'AbortError') {
      console.error('文件夹选择失败:', err)
    }
  }

  // 文件选择器关闭后恢复全屏
  if (wasFullscreen && !document.fullscreenElement) {
    try {
      await document.documentElement.requestFullscreen()
    } catch {
      // 全屏请求可能被拒绝，忽略
    }
  }
}

/** 生成时间戳文件名 (不含冒号，兼容 Windows) */
function makeTimestampName(): string {
  const now = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `rov_${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}.csv`
}

/** 生成 CSV 内容 */
function makeCsvContent(): string {
  const tel = store.telemetry
  const ts = new Date().toISOString()
  return `timestamp,latitude,longitude,depth\n${ts},${tel.lat.toFixed(7)},${tel.lon.toFixed(7)},${tel.depth.toFixed(2)}\n`
}

/** 通过 <a download> 下载文件 (非安全上下文的回退方案) */
function downloadFallback(fileName: string, content: string) {
  const blob = new Blob([content], { type: 'text/csv;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = fileName
  a.style.display = 'none'
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  URL.revokeObjectURL(url)
}

/** 保存一条记录 */
async function saveRecord() {
  const fileName = makeTimestampName()
  const content = makeCsvContent()

  // 如果已选择了目录（File System Access API 模式），写入该目录
  if (dirHandle.value) {
    try {
      const fileHandle = await dirHandle.value.getFileHandle(fileName, { create: true })
      const writable = await fileHandle.createWritable({ keepExistingData: false })
      await writable.write(content)
      await writable.close()

      showStatus(`已保存 → ${fileName}`, true)
      return
    } catch (err) {
      console.error('写入目录失败，回退到下载:', err)
      // 目录写入失败，回退到下载方式
    }
  }

  // 安全上下文不可用或未选择目录时，通过浏览器下载
  try {
    downloadFallback(fileName, content)
    showStatus(`已下载 → ${fileName}`, true)
  } catch (err) {
    console.error('下载失败:', err)
    showStatus('保存失败', false)
  }
}
</script>

<style scoped>
.data-logger {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  padding: 6px;
  background: rgba(20, 25, 36, 0.65);
  border-radius: 8px;
  user-select: none;
  align-items: center;
}

.logger-row {
  display: flex;
  align-items: center;
}

.logger-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 5px;
  background: rgba(255, 255, 255, 0.06);
  color: #c8d2dc;
  font-size: 12px;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.2s, border-color 0.2s;
  font-family: inherit;
  line-height: 1.4;
}

.logger-btn:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.12);
  border-color: rgba(255, 255, 255, 0.25);
}

.logger-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.folder-btn {
  max-width: 180px;
  overflow: hidden;
  text-overflow: ellipsis;
}

.save-btn:hover:not(:disabled) {
  background: rgba(52, 211, 153, 0.15);
  border-color: rgba(52, 211, 153, 0.35);
  color: #6ee7b7;
}

.save-row {
  position: relative;
}

.status-text {
  position: absolute;
  left: calc(100% + 6px);
  top: 50%;
  transform: translateY(-50%);
  font-size: 11px;
  white-space: nowrap;
  pointer-events: none;
}

.status-ok {
  color: #6ee7b7;
}

.status-err {
  color: #fca5a5;
}

.status-fade-enter-active,
.status-fade-leave-active {
  transition: opacity 0.3s ease;
}

.status-fade-enter-from,
.status-fade-leave-to {
  opacity: 0;
}
</style>
