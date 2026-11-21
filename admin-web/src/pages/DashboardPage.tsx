import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  type CountryRestrictionOut,
  type DeviceOut,
  type DnsDenylistOut,
  type EnrollmentWindowOut,
  type HealthOut,
  type IncidentOut,
  getDnsDenylist,
  getEnrollmentWindow,
  getHealth,
  listDeviceIncidents,
  listDevices,
  listRestrictions,
} from '../api/admin'
import HealthCharts from '../components/HealthCharts'
import KpiStrip from '../components/KpiStrip'
import PolicyCards from '../components/PolicyCards'
import ThreatTable from '../components/ThreatTable'
import { computeDeviceKpis } from '../lib/deviceStats'
import { useI18n } from '../i18n/useI18n'

const INCIDENT_DEVICE_LIMIT = 10
const RECENT_INCIDENTS = 15

export default function DashboardPage() {
  const { t, lang } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [devices, setDevices] = useState<DeviceOut[]>([])
  const [incidents, setIncidents] = useState<IncidentOut[]>([])
  const [restrictions, setRestrictions] = useState<CountryRestrictionOut[]>([])
  const [dns, setDns] = useState<DnsDenylistOut | null>(null)
  const [health, setHealth] = useState<HealthOut | null>(null)
  const [enrollment, setEnrollment] = useState<EnrollmentWindowOut | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [deviceList, restrictionList, denylist, healthRes, enrollRes] = await Promise.all([
        listDevices(),
        listRestrictions(),
        getDnsDenylist(),
        getHealth(),
        getEnrollmentWindow(),
      ])
      setDevices(deviceList)
      setRestrictions(restrictionList)
      setDns(denylist)
      setHealth(healthRes)
      setEnrollment(enrollRes)

      const sample = deviceList.slice(0, INCIDENT_DEVICE_LIMIT)
      const nested = await Promise.all(
        sample.map(async (d) => {
          try {
            return await listDeviceIncidents(d.deviceUuid)
          } catch {
            return [] as IncidentOut[]
          }
        }),
      )
      const merged = nested
        .flat()
        .sort((a, b) => new Date(b.triggeredAt).getTime() - new Date(a.triggeredAt).getTime())
        .slice(0, RECENT_INCIDENTS)
      setIncidents(merged)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const kpis = useMemo(() => computeDeviceKpis(devices), [devices])

  const countryCount = useMemo(() => {
    const set = new Set<string>()
    for (const row of restrictions) {
      for (const c of row.countries ?? []) {
        set.add(c)
      }
    }
    return set.size
  }, [restrictions])

  const policy = useMemo(
    () => ({
      countryCount,
      tldCount: dns?.tlds?.length ?? 0,
      bundleVersion: health?.bundleVersion ?? 0,
      enrollOpen: Boolean(enrollment?.open),
    }),
    [countryCount, dns, health, enrollment],
  )

  const okCount = Math.max(0, kpis.devices - kpis.degraded)

  if (loading) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 px-6 py-12 text-center text-sm text-ink-600">
        {t('state.loading')}
      </div>
    )
  }

  if (error) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-red-200 px-6 py-8 text-center space-y-3">
        <p className="text-sm text-red-800">{t('state.error')}</p>
        <p className="text-xs text-ink-600">{error}</p>
        <button
          type="button"
          onClick={() => void load()}
          className="text-sm font-semibold text-brand-700 hover:text-brand-800"
        >
          {t('state.retry')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-8">
      <KpiStrip
        items={[
          { key: 'devices', label: t('kpi.devices'), value: kpis.devices },
          {
            key: 'degraded',
            label: t('kpi.degraded'),
            value: kpis.degraded,
            accent: kpis.degraded > 0 ? 'warn' : 'default',
          },
          {
            key: 'dns',
            label: t('kpi.dns_off'),
            value: kpis.dnsOff,
            accent: kpis.dnsOff > 0 ? 'warn' : 'default',
          },
          {
            key: 'screening',
            label: t('kpi.screening_off'),
            value: kpis.screeningOff,
            accent: kpis.screeningOff > 0 ? 'risk' : 'default',
          },
        ]}
      />

      <div className="grid lg:grid-cols-3 gap-6">
        <section className="lg:col-span-2 rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
          <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('threats.title')}</h2>
          <ThreatTable rows={incidents} />
        </section>
        <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
          <HealthCharts okCount={okCount} degradedCount={kpis.degraded} />
        </section>
      </div>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
        <h2 className="text-sm font-semibold text-ink-950 mb-4">{t('policy.title')}</h2>
        <PolicyCards policy={policy} />
        {health?.lastSeenAt ? (
          <p className="mt-4 text-xs text-ink-600">
            {lang === 'ko' ? '마지막 기기 동기화' : 'Last device sync'}:{' '}
            {new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
              dateStyle: 'medium',
              timeStyle: 'short',
            }).format(new Date(health.lastSeenAt))}
          </p>
        ) : null}
      </section>
    </div>
  )
}