import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { type IncidentOut, getIncidentExport } from '../api/admin'
import DnsTopChart from '../components/DnsTopChart'
import { mergeIncidentTimeline, topDnsDomains } from '../lib/incidentTimeline'
import { shortUuid } from '../lib/deviceStats'
import { useI18n } from '../i18n/useI18n'

function formatTime(iso: string, lang: string): string {
  try {
    return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
      dateStyle: 'medium',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function asList(v: unknown): Record<string, unknown>[] {
  if (!Array.isArray(v)) return []
  return v.filter((x): x is Record<string, unknown> => !!x && typeof x === 'object')
}

export default function IncidentPage() {
  const { incidentId = '' } = useParams()
  const { t, lang } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [data, setData] = useState<IncidentOut | null>(null)
  const [showHashes, setShowHashes] = useState(false)

  const load = useCallback(async () => {
    if (!incidentId) return
    setLoading(true)
    setError(null)
    try {
      setData(await getIncidentExport(incidentId))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [incidentId, t])

  useEffect(() => {
    void load()
  }, [load])

  const payload = (data?.payload || {}) as Record<string, unknown>
  const timeline = useMemo(() => mergeIncidentTimeline(payload), [payload])
  const dnsTop = useMemo(() => topDnsDomains(payload), [payload])
  const apps = asList(payload.apps)
  const calls = asList(payload.calls)
  const dns = payload.dns && typeof payload.dns === 'object' ? (payload.dns as Record<string, unknown>) : {}
  const dnsEvents = asList(dns.events)
  const hints =
    payload.countryHints && typeof payload.countryHints === 'object'
      ? (payload.countryHints as Record<string, unknown>)
      : {}
  const snap =
    payload.protectionSnapshot && typeof payload.protectionSnapshot === 'object'
      ? (payload.protectionSnapshot as Record<string, unknown>)
      : {}
  const windowObj =
    payload.window && typeof payload.window === 'object'
      ? (payload.window as Record<string, unknown>)
      : {}

  if (loading) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 px-6 py-12 text-center text-sm text-ink-600">
        {t('state.loading')}
      </div>
    )
  }

  if (error || !data) {
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
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex flex-wrap gap-2">
          {data.triggers.map((tr) => (
            <span
              key={tr}
              className="inline-flex rounded-md bg-brand-50 text-brand-800 ring-1 ring-brand-200 px-2.5 py-1 text-xs font-semibold"
            >
              {tr}
            </span>
          ))}
        </div>
        <div className="flex flex-wrap gap-3 text-sm">
          <Link to={`/devices/${data.deviceUuid}`} className="font-semibold text-brand-700 hover:text-brand-800">
            {t('incident.device_link')} ({shortUuid(data.deviceUuid)})
          </Link>
          <a
            href={`/api/v1/admin/incidents/${data.incidentId}/export`}
            className="font-semibold text-ink-700 hover:text-ink-950"
            onClick={(e) => {
              e.preventDefault()
              void (async () => {
                const r = await fetch(`/api/v1/admin/incidents/${data.incidentId}/export`, {
                  credentials: 'include',
                  headers: { 'X-ElderShield-Admin': '1' },
                })
                const blob = await r.blob()
                const url = URL.createObjectURL(blob)
                const a = document.createElement('a')
                a.href = url
                a.download = `incident-${data.incidentId}.json`
                a.click()
                URL.revokeObjectURL(url)
              })()
            }}
          >
            {t('incident.download_json')}
          </a>
        </div>
      </div>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 grid sm:grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-600">{t('incident.triggered')}</p>
          <p className="mt-1 text-ink-950">{formatTime(data.triggeredAt, lang)}</p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-600">{t('incident.window')}</p>
          <p className="mt-1 text-ink-800 text-xs">
            {String(windowObj.from || '—')} → {String(windowObj.to || '—')}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-600">{t('incident.hints')}</p>
          <p className="mt-1 text-ink-800 text-xs">
            {String(hints.callIsoMode || hints.call_iso_mode || '—')} /{' '}
            {String(hints.dnsCctldMode || hints.dns_cctld_mode || '—')}
          </p>
        </div>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-ink-600">{t('incident.protection')}</p>
          <p className="mt-1 text-ink-800 text-xs">
            DNS {String(snap.dnsConfigured ?? snap.dns_configured ?? '—')} · screening{' '}
            {String(snap.callScreeningEnabled ?? snap.call_screening_enabled ?? '—')}
          </p>
        </div>
      </section>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
        <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('incident.timeline')}</h2>
        {timeline.length === 0 ? (
          <p className="text-sm text-ink-600">{t('incident.timeline_empty')}</p>
        ) : (
          <ol className="space-y-2 border-l border-slate-200 ml-2 pl-4">
            {timeline.map((item, i) => (
              <li key={`${item.at}-${item.kind}-${i}`} className="relative text-sm">
                <span
                  className={
                    item.kind === 'call'
                      ? 'absolute -left-[1.35rem] mt-1.5 h-2 w-2 rounded-full bg-rose-500'
                      : item.kind === 'app'
                        ? 'absolute -left-[1.35rem] mt-1.5 h-2 w-2 rounded-full bg-amber-500'
                        : 'absolute -left-[1.35rem] mt-1.5 h-2 w-2 rounded-full bg-teal-600'
                  }
                />
                <span className="text-xs text-ink-500">{formatTime(item.at, lang)}</span>
                <span className="ml-2 font-medium text-ink-900 uppercase text-[10px] tracking-wide">
                  {item.kind}
                </span>
                <p className="text-ink-800">
                  {item.label}
                  {item.detail ? <span className="text-ink-500"> · {item.detail}</span> : null}
                </p>
              </li>
            ))}
          </ol>
        )}
      </section>

      <div className="grid lg:grid-cols-2 gap-6">
        <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 overflow-x-auto">
          <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('incident.apps')}</h2>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-600 border-b">
                <th className="py-2 pr-2">{t('incident.col_package')}</th>
                <th className="py-2 pr-2">{t('incident.col_score')}</th>
                <th className="py-2">{t('incident.col_reasons')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {apps.map((a, i) => (
                <tr key={i}>
                  <td className="py-2 pr-2 font-mono text-xs">{String(a.packageName || a.package_name)}</td>
                  <td className="py-2 pr-2 tabular-nums">{String(a.riskScore ?? a.risk_score ?? '—')}</td>
                  <td className="py-2 text-xs text-ink-600">
                    {Array.isArray(a.reasons) ? a.reasons.join(', ') : '—'}
                    {showHashes ? (
                      <div className="mt-1 text-[10px] break-all text-ink-400">
                        apk={String(a.apkSha256 || a.apk_sha256 || '—')}
                      </div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <button
            type="button"
            className="mt-3 text-xs font-semibold text-brand-700"
            onClick={() => setShowHashes((v) => !v)}
          >
            {showHashes ? t('incident.hide_hashes') : t('incident.show_hashes')}
          </button>
        </section>

        <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 overflow-x-auto">
          <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('incident.calls')}</h2>
          <table className="min-w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-ink-600 border-b">
                <th className="py-2 pr-2">{t('incident.col_time')}</th>
                <th className="py-2 pr-2">{t('incident.col_country')}</th>
                <th className="py-2 pr-2">{t('incident.col_decision')}</th>
                <th className="py-2">{t('incident.col_last4')}</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {calls.map((c, i) => (
                <tr key={i}>
                  <td className="py-2 pr-2 whitespace-nowrap text-xs">
                    {formatTime(String(c.at || ''), lang)}
                  </td>
                  <td className="py-2 pr-2">{String(c.countryIso || c.country_iso || '—')}</td>
                  <td className="py-2 pr-2">{String(c.decision || '—')}</td>
                  <td className="py-2 font-mono text-xs">
                    {c.last4 != null ? `…${c.last4}` : '—'}
                    {showHashes && c.phoneHash ? (
                      <div className="text-[10px] break-all text-ink-400">{String(c.phoneHash)}</div>
                    ) : null}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>
      </div>

      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
        <h2 className="text-sm font-semibold text-ink-950 mb-3">{t('incident.dns')}</h2>
        {!dns.available && dnsEvents.length === 0 ? (
          <p className="text-sm text-ink-600">
            {t('incident.dns_unavailable')}: {String(dns.unavailableReason || '—')}
          </p>
        ) : (
          <div className="grid lg:grid-cols-2 gap-6">
            <DnsTopChart rows={dnsTop} title={t('incident.dns_top')} />
            <div className="overflow-x-auto max-h-64 overflow-y-auto">
              <table className="min-w-full text-sm">
                <thead>
                  <tr className="text-left text-xs text-ink-600 border-b">
                    <th className="py-2 pr-2">{t('incident.col_time')}</th>
                    <th className="py-2 pr-2">{t('incident.col_domain')}</th>
                    <th className="py-2">{t('incident.col_action')}</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {dnsEvents.map((e, i) => (
                    <tr key={i}>
                      <td className="py-2 pr-2 text-xs whitespace-nowrap">
                        {formatTime(String(e.at || ''), lang)}
                      </td>
                      <td className="py-2 pr-2 font-mono text-xs">{String(e.domain)}</td>
                      <td className="py-2 text-xs">{String(e.action || e.status || 'block')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </section>
    </div>
  )
}
