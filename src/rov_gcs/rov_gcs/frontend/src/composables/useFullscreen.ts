import { onMounted, onUnmounted, ref } from 'vue'

export function useFullscreen(targetSelector = '#gcs-app') {
  const isFullscreen = ref(false)

  function onChange() {
    isFullscreen.value = !!document.fullscreenElement
  }

  async function toggle() {
    try {
      if (isFullscreen.value) {
        await document.exitFullscreen()
      } else {
        const el = document.querySelector(targetSelector)
        if (el) {
          await el.requestFullscreen()
        }
      }
    } catch {
      // silently ignore — browser may deny fullscreen
    }
  }

  onMounted(() => {
    document.addEventListener('fullscreenchange', onChange)
  })
  onUnmounted(() => {
    document.removeEventListener('fullscreenchange', onChange)
  })

  return { isFullscreen, toggle }
}
