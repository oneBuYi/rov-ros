import { useTelemetryStore } from '../stores/telemetry'

const BASE = '/api'

async function request(method: string, path: string, body?: unknown) {
  const resp = await fetch(`${BASE}${path}`, {
    method,
    headers: body ? { 'Content-Type': 'application/json' } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  })
  if (!resp.ok) {
    const text = await resp.text()
    throw new Error(text)
  }
  return resp.json()
}

export function useApi() {
  const store = useTelemetryStore()

  // ----- depth control -----

  async function setDepthTarget(target: number) {
    if (target < 0) throw new Error('target depth must be >= 0')
    const result = await request('POST', '/depth/set_target', { target })
    store.updateTelemetry({ target_depth: target, depth_hold_enabled: true })
    return result
  }

  async function toggleDepthHold() {
    const result = await request('POST', '/depth/hold')
    if (result.message) {
      const enabled = result.message.toLowerCase().includes('enabled')
      store.updateTelemetry({ depth_hold_enabled: enabled })
    }
    return result
  }

  // ----- heading control -----

  async function setHeadingTarget(target: number) {
    const result = await request('POST', '/heading/set_target', { target })
    store.updateTelemetry({
      target_heading: target % 360,
      heading_hold_enabled: true,
    })
    return result
  }

  async function toggleHeadingHold() {
    const result = await request('POST', '/heading/hold')
    if (result.message) {
      const enabled = result.message.toLowerCase().includes('enabled')
      store.updateTelemetry({ heading_hold_enabled: enabled })
    }
    return result
  }

  // ----- grid control -----

  async function setGridTarget(row: number, col: number) {
    const result = await request('POST', '/grid/set_target', { row, col })
    if (result.success) {
      store.updateTelemetry({
        grid_target_row: row,
        grid_target_col: col,
        target_grid: `R${row}C${col}`,
      })
    }
    return result
  }

  // ----- arm/disarm -----

  async function arm() {
    return request('POST', '/arm')
  }

  async function disarm() {
    return request('POST', '/disarm')
  }

  // ----- PID gains -----

  async function setDepthPIDGains(kp: number, ki: number, kd: number) {
    const result = await request('POST', '/depth/pid_gains', { kp, ki, kd })
    if (result.success) {
      store.updateTelemetry({ depth_kp: kp, depth_ki: ki, depth_kd: kd })
    }
    return result
  }

  async function resetDepthPIDGains() {
    return request('POST', '/depth/pid_reset')
  }

  async function setHeadingPIDGains(kp: number, ki: number, kd: number) {
    const result = await request('POST', '/heading/pid_gains', { kp, ki, kd })
    if (result.success) {
      store.updateTelemetry({ heading_kp: kp, heading_ki: ki, heading_kd: kd })
    }
    return result
  }

  async function resetHeadingPIDGains() {
    return request('POST', '/heading/pid_reset')
  }

  return {
    setDepthTarget,
    toggleDepthHold,
    setHeadingTarget,
    toggleHeadingHold,
    setGridTarget,
    arm,
    disarm,
    setDepthPIDGains,
    resetDepthPIDGains,
    setHeadingPIDGains,
    resetHeadingPIDGains,
  }
}
