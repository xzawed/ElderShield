import { useCallback, useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { type DeviceOut, listDevices } from '../api/admin'
import KpiStrip from '../components/KpiStrip'
import StatusBadge from '../components/StatusBadge'
import { computeDeviceKpis, shortUuid } from '../lib/deviceStats'
import { useI18n } from '../i18n/useI18n'

function formatSync(iso: string | null, lang: string): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export default function DevicesPage() {
  const { t, lang } = useI18n()
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [devices, setDevices] = useState<DeviceOut[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setDevices(await listDevices())
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
        <button type="button" onClick={() => void load()} className="text-sm font-semibold text-brand-700">
          {t('state.retry')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <KpiStrip
        items={[
          { key: 'devices', label: t('kpi.devices'), value: kpis.devices },
          { key: 'degraded', label: t('kpi.degraded'), value: kpis.degraded, accent: kpis.degraded ? 'warn' : 'default' },
          { key: 'dns', label: t('kpi.dns_off'), value: kpis.dnsOff, accent: kpis.dnsOff ? 'warn' : 'default' },
          {
            key: 'screening',
            label: t('kpi.screening_off'),
            value: kpis.screeningOff,
            accent: kpis.screeningOff ? 'risk' : 'default',
          },
        ]}
      />

      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 overflow-hidden">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ink-600">
                <th className="px-4 py-3">{t('devices.col_uuid')}</th>
                <th className="px-4 py-3">{t('devices.col_app')}</th>
                <th className="px-4 py-3">{t('devices.col_dns')}</th>
                <th className="px-4 py-3">{t('devices.col_screening')}</th>
                <th className="px-4 py-3">{t('devices.col_degraded')}</th>
                <th className="px-4 py-3">{t('devices.col_sync')}</th>
                <th className="px-4 py-3">{t('devices.col_rules')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {devices.map((d) => (
                <tr
                  key={d.deviceUuid}
                  className="hover:bg-slate-50 cursor-pointer"
                  onClick={() => navigate(`/devices/${d.deviceUuid}`)}
                >
                  <td className="px-4 py-2.5 font-mono text-xs text-ink-800" title={d.deviceUuid}>
                    {shortUuid(d.deviceUuid)}
                  </td>
                  <td className="px-4 py-2.5 text-ink-800">{d.appVersion}</td>
                  <td className="px-4 py-2.5">
                    <StatusBadge
                      label={d.dnsConfigured ? t('yes') : t('no')}
                      variant={d.dnsConfigured ? 'ok' : 'warn'}
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge
                      label={d.callScreeningEnabled ? t('yes') : t('no')}
                      variant={d.callScreeningEnabled ? 'ok' : 'risk'}
                    />
                  </td>
                  <td className="px-4 py-2.5">
                    <StatusBadge
                      label={d.protectionDegraded ? t('yes') : t('no')}
                      variant={d.protectionDegraded ? 'warn' : 'ok'}
                    />
                  </td>
                  <td className="px-4 py-2.5 whitespace-nowrap text-ink-600">
                    {formatSync(d.lastSyncAt, lang)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums text-ink-800">{d.lastRuleVersion}</td>
                </tr>
              ))}
            </tbody>
          </table>
      </div>
    </div>
  )
}