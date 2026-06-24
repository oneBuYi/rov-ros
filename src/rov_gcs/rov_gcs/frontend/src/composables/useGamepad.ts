interface JoystickData {
  x: number // -100 ~ 100
  y: number
  z: number
  r: number
}

export function useGamepad(options: {
  onData: (data: JoystickData) => void
  onConnect?: (connected: boolean) => void
}) {
  let animFrameId: number | null = null
  let wasConnected = false

  function poll() {
    const gamepads = navigator.getGamepads()
    const gamepad = gamepads[0]

    const connected = gamepad !== null
    if (connected !== wasConnected) {
      wasConnected = connected
      options.onConnect?.(connected)
    }

    if (gamepad) {
      const leftX = gamepad.axes[0] ?? 0
      const leftY = gamepad.axes[1] ?? 0
      const rightX = gamepad.axes[2] ?? 0
      const rightY = gamepad.axes[3] ?? 0

      const data: JoystickData = {
        x: Math.round(-leftY * 100),  // forward = positive
        y: Math.round(leftX * 100),   // right = positive
        z: Math.round(-rightY * 100), // up = positive
        r: Math.round(rightX * 100),  // right turn = positive
      }
      options.onData(data)
    }

    animFrameId = requestAnimationFrame(poll)
  }

  function start() {
    if (animFrameId === null) {
      animFrameId = requestAnimationFrame(poll)
    }
  }

  function stop() {
    if (animFrameId !== null) {
      cancelAnimationFrame(animFrameId)
      animFrameId = null
    }
  }

  return { start, stop }
}
