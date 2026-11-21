import { apiDelete, apiGet, apiPost } from './client'

export interface DeviceOut {
  deviceUuid: string
  name: string | null
  model: string | null
  appVersion: string
  dnsConfigured: boolean
  callScreeningEnabled: boolean
  callScreeningHeldBy?: string | null
  callScreeningPeers?: string[]
  lastRuleVersion: number
  lastSyncAt: string | null
  dnsHostClass?: string | null
  lastSyncOk?: boolean
  lastSyncErrorCode?: string | null
  cachedBundleVersion?: number
  protectionDegraded: boolean
}

export interface CountryRestrictionOut {
  id: string
  name: string
  countries: string[]
  applyTo: string[]
  enabled: boolean
  version: number
  description?: string | null
}

export interface DnsDenylistOut {
  source: string
  countries: string[]
  tlds: string[]
  domains: string[]
  threatHosts: string[]
  threatHostsLab: string[]
  count: number
}

export interface HealthOut {
  status: string
  devices: number
  degradedDevices: number
  bundleVersion: number
  lastSeenAt: string | null
  syncLagSeconds: number | null
}

export interface EnrollmentWindowOut {
  enabled: boolean
  open: boolean
  expiresAt: string | null
}

export interface IncidentOut {
  incidentId: string
  deviceUuid: string
  triggeredAt: string
  triggers: string[]
  payload?: Record<string, unknown>
  createdAt?: string
}

export interface DeviceDetailOut {
  device: DeviceOut
  /** active | revoked | none — bound enroll token state (no raw hash). */
  tokenStatus?: 'active' | 'revoked' | 'none'
  healthEvents: {
    id: string
    type: string
    detail: string | null
    createdAt: string | null
  }[]
  scans: {
    packageName: string
    installer: string | null
    dangerousPermissions: string[]
    riskScore: number
    reasons: string[]
    createdAt: string | null
  }[]
}

export interface AuditRow {
  id: string
  actor: string
  action: string
  resourceType: string
  resourceId: string | null
  detail: string | null
  createdAt: string | null
}

export interface DnsLogEvent {
  at: string
  domain: string
  status: string
}

export interface DnsLogsOut {
  events: DnsLogEvent[]
  nextCursor?: string
  error?: string
}

export function listDevices(): Promise<DeviceOut[]> {
  return apiGet<DeviceOut[]>('/api/v1/admin/devices')
}

export function listRestrictions(): Promise<CountryRestrictionOut[]> {
  return apiGet<CountryRestrictionOut[]>('/api/v1/admin/country-restrictions')
}

/** @deprecated use listRestrictions */
export function listCountryRestrictions(): Promise<CountryRestrictionOut[]> {
  return listRestrictions()
}

export function getDnsDenylist(): Promise<DnsDenylistOut> {
  return apiGet<DnsDenylistOut>('/api/v1/admin/dns-denylist')
}

export function getHealth(): Promise<HealthOut> {
  return apiGet<HealthOut>('/health')
}

export function getEnrollmentWindow(): Promise<EnrollmentWindowOut> {
  return apiGet<EnrollmentWindowOut>('/api/v1/admin/enrollment-window')
}

export function listDeviceIncidents(deviceUuid: string): Promise<IncidentOut[]> {
  return apiGet<IncidentOut[]>(`/api/v1/admin/devices/${deviceUuid}/incidents`)
}

export function getIncidentExport(incidentId: string): Promise<IncidentOut> {
  return apiGet<IncidentOut>(`/api/v1/admin/incidents/${incidentId}/export`)
}

export function getDeviceDetail(deviceUuid: string): Promise<DeviceDetailOut> {
  return apiGet<DeviceDetailOut>(`/api/v1/admin/devices/${deviceUuid}`)
}

export function revokeDeviceToken(deviceUuid: string): Promise<void> {
  return apiDelete(`/api/v1/admin/devices/${deviceUuid}/token`)
}

export function listAudit(limit = 200): Promise<AuditRow[]> {
  return apiGet<AuditRow[]>(`/api/v1/admin/audit?limit=${limit}`)
}

export async function getDnsLogs(params: {
  from?: string
  to?: string
  status?: string
  limit?: number
}): Promise<DnsLogsOut> {
  const q = new URLSearchParams()
  if (params.from) q.set('from', params.from)
  if (params.to) q.set('to', params.to)
  if (params.status) q.set('status', params.status)
  if (params.limit) q.set('limit', String(params.limit))
  const path = `/api/v1/admin/dns-logs?${q.toString()}`
  const r = await fetch(path, {
    credentials: 'include',
    headers: { 'X-ElderShield-Admin': '1' },
  })
  if (r.status === 401) {
    window.location.assign('/admin/ui/login')
    throw new Error('unauthorized')
  }
  const body = (await r.json()) as DnsLogsOut
  if (r.status === 503) {
    return { events: [], error: body.error || 'nextdns_unset' }
  }
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return body
}

export function listCountries(): Promise<unknown[]> {
  return apiGet<unknown[]>('/api/v1/admin/countries')
}

export function listCallRules(): Promise<unknown[]> {
  return apiGet<unknown[]>('/api/v1/admin/call-rules')
}

export function openEnrollmentWindow(body: {
  enabled: boolean
  ttlMinutes?: number
}): Promise<EnrollmentWindowOut> {
  return apiPost<EnrollmentWindowOut>('/api/v1/admin/enrollment-window', body)
}