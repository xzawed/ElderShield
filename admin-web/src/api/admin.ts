import { apiGet, apiPost } from './client'

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