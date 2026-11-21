import type { DeviceOut } from '../api/admin'

export function computeDeviceKpis(devices: DeviceOut[]) {
  return {
    devices: devices.length,
    degraded: devices.filter((d) => d.protectionDegraded).length,
    dnsOff: devices.filter((d) => !d.dnsConfigured).length,
    screeningOff: devices.filter((d) => !d.callScreeningEnabled).length,
  }
}

export function shortUuid(uuid: string): string {
  if (uuid.length <= 12) return uuid
  return `${uuid.slice(0, 8)}…`
}