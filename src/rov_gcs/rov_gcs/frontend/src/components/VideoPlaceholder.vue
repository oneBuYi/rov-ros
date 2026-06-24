<template>
  <div class="video-placeholder">
    <div class="placeholder-content">
      <svg
        width="48" height="48" viewBox="0 0 24 24"
        fill="none" stroke="#4a5568" stroke-width="1.5"
      >
        <rect x="2" y="4" width="20" height="16" rx="2" />
        <path d="M10 9l5 3-5 3V9z" fill="#4a5568" />
      </svg>
      <p>视频功能开发中</p>
    </div>
  </div>
</template>

<style scoped>
.video-placeholder {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 200px;
  background: #141924;
  border: 1px dashed #2a3040;
  border-radius: 8px;
  margin: 8px 0;
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
