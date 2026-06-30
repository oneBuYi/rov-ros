interface JoystickData {
  x: number // -100 ~ 100
  y: number
  z: number
  r: number
  buttons: number[] // 0 or 1 for each button (remapped to SDL2/ArduSub layout)
}

/**
 * W3C Standard Gamepad → SDL2 GameController button index mapping.
 *
 * Browser Gamepad API button layout (Standard Gamepad):
 *   0=A  1=B  2=X  3=Y  4=LB  5=RB  6=LT  7=RT
 *   8=Back  9=Start  10=L3  11=R3
 *   12=D-padUp  13=D-padDown  14=D-padLeft  15=D-padRight  16=Home
 *
 * SDL2 / ArduSub expects:
 *   0=A  1=B  2=X  3=Y
 *   4=Back  5=Guide  6=Start  7=L3  8=R3  9=LB  10=RB
 *   11=D-padUp  12=D-padDown  13=D-padLeft  14=D-padRight
 *
 * LT/RT (browser 6,7) are analog axes in SDL2 → unmapped as digital buttons.
 */
const BROWSER_TO_SDL2: Record<number, number> = {
  0: 0,   // A
  1: 1,   // B
  2: 2,   // X
  3: 3,   // Y
  4: 9,   // LB → SDL2 LB
  5: 10,  // RB → SDL2 RB
  // 6,7: LT/RT → analog axes in SDL2, skipped
  8: 4,   // Back → SDL2 Back
  9: 6,   // Start → SDL2 Start
  10: 7,  // L3 → SDL2 LeftStick
  11: 8,  // R3 → SDL2 RightStick
  12: 11, // D-pad Up
  13: 12, // D-pad Down
  14: 13, // D-pad Left
  15: 14, // D-pad Right
  16: 5,  // Home → SDL2 Guide
}

const SDL2_BUTTON_COUNT = 15

function remapButtons(browserButtons: number[]): number[] {
  const sdlButtons = new Array(SDL2_BUTTON_COUNT).fill(0)
  for (const [browserIdx, sdlIdx] of Object.entries(BROWSER_TO_SDL2)) {
    const bi = Number(browserIdx)
    if (bi < browserButtons.length && browserButtons[bi]) {
      sdlButtons[sdlIdx] = 1
    }
  }
  return sdlButtons
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

      // Read raw browser button states, then remap to SDL2/ArduSub layout
      const rawButtons: number[] = []
      for (let i = 0; i < gamepad.buttons.length; i++) {
        rawButtons.push(gamepad.buttons[i].pressed ? 1 : 0)
      }
      const buttons = remapButtons(rawButtons)

      prevButtons = buttons

      const data: JoystickData = {
        x: Math.round(-leftY * 100),   // 左摇杆Y: 前进/后退
        y: Math.round(rightX * 100),   // 右摇杆X: 左移/右移
        z: Math.round(-rightY * 100),  // 右摇杆Y: 上升/下降
        r: Math.round(leftX * 100),    // 左摇杆X: 左转/右转
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
