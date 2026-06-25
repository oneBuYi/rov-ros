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

  // ----- arm/disarm -----

  async function arm() {
    return request('POST', '/arm')
  }

  async function disarm() {
    return request('POST', '/disarm')
  }

  return { setDepthTarget, toggleDepthHold, setHeadingTarget, toggleHeadingHold, arm, disarm }
}
