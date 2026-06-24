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

  async function setTarget(target: number) {
    if (target < 0) throw new Error('target depth must be >= 0')
    const result = await request('POST', '/depth/set_target', { target })
    store.updateTelemetry({ target_depth: target, hold_enabled: true })
    return result
  }

  async function toggleHold() {
    const result = await request('POST', '/depth/hold')
    if (result.message) {
      const enabled = result.message.toLowerCase().includes('enabled')
      store.updateTelemetry({ hold_enabled: enabled })
    }
    return result
  }

  return { setTarget, toggleHold }
}
