interface JoystickData {
  x: number // -100 ~ 100
  y: number
  z: number
  r: number
  buttons: number[] // 0 or 1 for each button
}

export function useGamepad(options: {
  onData: (data: JoystickData) => void
  onConnect?: (connected: boolean) => void
}) {
  let animFrameId: number | null = null
  let wasConnected = false
  // Track previous button states to detect edge changes
  let prevButtons: number[] = []

  function onGamepadConnected(_e: GamepadEvent) {
    wasConnected = true
    options.onConnect?.(true)
    if (animFrameId === null) {
      animFrameId = requestAnimationFrame(poll)
    }
  }

  function onGamepadDisconnected(_e: GamepadEvent) {
    wasConnected = false
    options.onConnect?.(false)
  }

  function poll() {
    const gamepads = navigator.getGamepads()
    const gamepad = gamepads[0]

    // Check connection status from polling as fallback
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

      // Read button states (pressed = 1, released = 0)
      const buttons: number[] = []
      for (let i = 0; i < gamepad.buttons.length; i++) {
        buttons.push(gamepad.buttons[i].pressed ? 1 : 0)
      }

      // Only send if axes OR buttons changed (reduce noise)
      const buttonsChanged =
        buttons.length !== prevButtons.length ||
        buttons.some((v, i) => v !== prevButtons[i])
      prevButtons = buttons

      const data: JoystickData = {
        x: Math.round(-leftY * 100),  // forward = positive
        y: Math.round(leftX * 100),   // right = positive
        z: Math.round(-rightY * 100), // up = positive
        r: Math.round(rightX * 100),  // right turn = positive
        buttons,
      }
      options.onData(data)
    }

    animFrameId = requestAnimationFrame(poll)
  }

  // Chrome requires a user gesture before exposing gamepads.
  // Page interaction (click, keypress) counts — this triggers
  // the gamepadconnected event for pre-connected gamepads.
  function onPageInteraction() {
    const gamepads = navigator.getGamepads()
    const existing = gamepads[0]
    if (existing && !wasConnected) {
      wasConnected = true
      options.onConnect?.(true)
    }
  }

  function start() {
    window.addEventListener('gamepadconnected', onGamepadConnected)
    window.addEventListener('gamepaddisconnected', onGamepadDisconnected)
    document.addEventListener('click', onPageInteraction, { once: true })
    document.addEventListener('keydown', onPageInteraction, { once: true })

    // Also try to detect already-connected gamepads
    const gamepads = navigator.getGamepads()
    const existing = gamepads[0]
    if (existing) {
      wasConnected = true
      options.onConnect?.(true)
    }

    if (animFrameId === null) {
      animFrameId = requestAnimationFrame(poll)
    }
  }

  function stop() {
    window.removeEventListener('gamepadconnected', onGamepadConnected)
    window.removeEventListener('gamepaddisconnected', onGamepadDisconnected)

    if (animFrameId !== null) {
      cancelAnimationFrame(animFrameId)
      animFrameId = null
    }
  }

  return { start, stop }
}
