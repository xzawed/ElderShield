/**
 * Lightweight KPI unit checks (node --test). Run: node --test src/lib/deviceStats.test.mjs
 * Mirrors computeDeviceKpis in deviceStats.ts (keep in sync).
 */
import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

function computeDeviceKpis(devices) {
  return {
    devices: devices.length,
    degraded: devices.filter((d) => d.protectionDegraded).length,
    dnsOff: devices.filter((d) => !d.dnsConfigured).length,
    screeningOff: devices.filter((d) => !d.callScreeningEnabled).length,
  }
}

describe('computeDeviceKpis', () => {
  it('counts empty as zeros', () => {
    assert.deepEqual(computeDeviceKpis([]), {
      devices: 0,
      degraded: 0,
      dnsOff: 0,
      screeningOff: 0,
    })
  })

  it('aggregates degraded dns and screening flags', () => {
    const k = computeDeviceKpis([
      {
        protectionDegraded: true,
        dnsConfigured: false,
        callScreeningEnabled: true,
      },
      {
        protectionDegraded: false,
        dnsConfigured: true,
        callScreeningEnabled: false,
      },
    ])
    assert.deepEqual(k, {
      devices: 2,
      degraded: 1,
      dnsOff: 1,
      screeningOff: 1,
    })
  })
})
