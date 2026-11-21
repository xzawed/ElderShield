import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import {
  type DeviceDetailOut,
  type IncidentOut,
  getDeviceDetail,
  listDeviceIncidents,
  revokeDeviceToken,
} from '../api/admin'
import KpiStrip from '../components/KpiStrip'
import StatusBadge from '../components/StatusBadge'
import { shortUuid } from '../lib/deviceStats'
import { useI18n } from '../i18n/useI18n'

function formatTime(iso: string | null, lang: string): string {
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

export default function DeviceDetailPage() {
  const { deviceUuid = '' } = useParams()
  const { t, lang } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [detail, setDetail] = useState<DeviceDetailOut | null>(null)
  const [incidents, setIncidents] = useState<IncidentOut[]>([])
  const [revoking, setRevoking] = useState(false)
  const [revokeMsg, setRevokeMsg] = useState<string | null>(null)

  const load = useCallback(async () => {
    if (!deviceUuid) return
    setLoading(true)
    setError(null)
    try {
      const [d, inc] = await Promise.all([
        getDeviceDetail(deviceUuid),
        listDeviceIncidents(deviceUuid),
      ])
      setDetail(d)
      setIncidents(inc)
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [deviceUuid, t])

  useEffect(() => {
    void load()
  }, [load])

  const scans = useMemo(
    () => [...(detail?.scans || [])].sort((a, b) => b.riskScore - a.riskScore),
    [detail],
  )

  const onRevoke = async () => {
    if (!deviceUuid) return
    if (!window.confirm(t('device.revoke_confirm'))) return
    setRevoking(true)
    setRevokeMsg(null)
    try {
      await revokeDeviceToken(deviceUuid)
      setRevokeMsg(t('device.revoke_done'))
      await load()
    } catch (e) {
      setRevokeMsg(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setRevoking(false)
    }
  }

  if (loading) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 px-6 py-12 text-center text-sm text-ink-600">
        {t('state.loading')}
      </div>
    )
  }

  if (error || !detail) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-red-200 px-6 py-8 text-center space-y-3">
        <p className="text-sm text-red-800">{t('state.error')}</p>
        <button type="button" onClick={() => void load()} className="text-sm font-semibold text-brand-700">
          {t('state.retry')}
        </button>
      </div>
    )
  }

  const d = detail.device
  const tokenStatus = detail.tokenStatus || 'none'

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-mono text-sm text-ink-800" title={d.deviceUuid}>
          {shortUuid(d.deviceUuid)}
        </p>
        <Link to="/devices" className="text-sm font-semibold text-brand-700">
          {t('device.back')}
        </Link>
      </div>

      <KpiStrip
        items={[
          {
            key: 'dns',
            label: t('devices.col_dns'),
            value: d.dnsConfigured ? t('yes') : t('no'),
            accent: d.dnsConfigured ? 'default' : 'warn',
          },
          {
            key: 'screen',
            label: t('devices.col_screening'),
            value: d.callScreeningEnabled ? t('yes') : t('no'),
            accent: d.callScreeningEnabled ? 'default' : 'risk',
          },
          {
            key: 'deg',
            label: t('devices.col_degraded'),
            value: d.protectionDegraded ? t('yes') : t('no'),
            accent: d.protectionDegraded ? 'warn' : 'default',
          },
          {
            key: 'rules',
            label: t('devices.col_rules'),
            value: d.lastRuleVersion,
          },
        ]}
      />

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 space-y-3">
        <div className="flex flex-wrap items-center gap-3">
          <StatusBadge
            label={
              tokenStatus === 'active'
                ? t('device.token_active')
                : tokenStatus === 'revoked'
                  ? t('device.token_revoked')
                  : t('device.token_none')
            }
            variant={tokenStatus === 'active' ? 'ok' : tokenStatus === 'revoked' ? 'warn' : 'muted'}
          />
          <StatusBadge
            label={d.dnsConfigured ? `DNS ${d.dnsHostClass || 'on'}` : 'DNS off'}
            variant={d.dnsConfigured ? 'ok' : 'warn'}
          />
        </div>
        {tokenStatus === 'active' ? (
          <button
            type="button"
            disabled={revoking}
            onClick={() => void onRevoke()}
            className="rounded-lg bg-amber-700 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-600 disabled:opacity-60"
          >
            {revoking ? t('state.loading') : t('device.revoke')}
          </button>
        ) : null}
        {revokeMsg ? <p className="text-sm text-ink-700">{revokeMsg}</p> : null}
        <p className="text-xs text-ink-500">
          app {d.appVersion}
          {d.lastSyncErrorCode ? ` · sync ${d.lastSyncErrorCode}` : ''}
        </p>
      </section>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
        <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('device.health')}</h2>
        {detail.healthEvents.length === 0 ? (
          <p className="text-sm text-ink-600">{t('device.health_empty')}</p>
        ) : (
          <ol className="space-y-2 border-l border-slate-200 ml-2 pl-4">
            {detail.healthEvents.map((e) => (
              <li key={e.id} className="text-sm">
                <span className="text-xs text-ink-500">{formatTime(e.createdAt, lang)}</span>
                <p className="font-medium text-ink-900">{e.type}</p>
                {e.detail ? <p className="text-xs text-ink-600">{e.detail}</p> : null}
              </li>
            ))}
          </ol>
        )}
      </section>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 overflow-x-auto">
        <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('device.scans')}</h2>
        <table className="min-w-full text-sm">
          <thead>
            <tr className="text-left text-xs text-ink-600 border-b">
              <th className="py-2 pr-2">{t('incident.col_package')}</th>
              <th className="py-2 pr-2">{t('incident.col_score')}</th>
              <th className="py-2">{t('incident.col_reasons')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {scans.map((s, i) => (
              <tr key={`${s.packageName}-${i}`}>
                <td className="py-2 pr-2 font-mono text-xs">{s.packageName}</td>
                <td className="py-2 pr-2 tabular-nums">{s.riskScore}</td>
                <td className="py-2 text-xs text-ink-600">{(s.reasons || []).join(', ') || '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
        <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('device.incidents')}</h2>
        {incidents.length === 0 ? (
          <p className="text-sm text-ink-600">{t('threats.empty')}</p>
        ) : (
          <ul className="divide-y divide-slate-100">
            {incidents.map((inc) => (
              <li key={inc.incidentId} className="py-2.5 flex flex-wrap justify-between gap-2 text-sm">
                <div>
                  <p className="text-ink-800">{formatTime(inc.triggeredAt, lang)}</p>
                  <p className="text-xs text-ink-600">{inc.triggers.join(', ')}</p>
                </div>
                <Link
                  to={`/incidents/${inc.incidentId}`}
                  className="font-semibold text-brand-700 hover:text-brand-800"
                >
                  {t('device.open_incident')}
                </Link>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
