import { useCallback, useEffect, useMemo, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { type DnsLogEvent, getDnsLogs } from '../api/admin'
import DnsTopChart from '../components/DnsTopChart'
import { useI18n } from '../i18n/useI18n'

function formatTime(iso: string, lang: string): string {
  try {
    return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
      dateStyle: 'short',
      timeStyle: 'medium',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

function toLocalInput(d: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

export default function DnsLogsPage() {
  const { t, lang } = useI18n()
  const [searchParams] = useSearchParams()
  const now = useMemo(() => new Date(), [])
  const startDefault = useMemo(() => {
    const d = new Date(now)
    d.setHours(0, 0, 0, 0)
    return d
  }, [now])

  const [fromLocal, setFromLocal] = useState(
    () => searchParams.get('from')?.slice(0, 16) || toLocalInput(startDefault),
  )
  const [toLocal, setToLocal] = useState(
    () => searchParams.get('to')?.slice(0, 16) || toLocalInput(now),
  )
  const [status, setStatus] = useState(searchParams.get('status') || 'blocked')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [unset, setUnset] = useState(false)
  const [events, setEvents] = useState<DnsLogEvent[]>([])

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    setUnset(false)
    try {
      const fromIso = new Date(fromLocal).toISOString()
      const toIso = new Date(toLocal).toISOString()
      if (Number.isNaN(Date.parse(fromIso)) || Number.isNaN(Date.parse(toIso))) {
        throw new Error(t('dns_logs.invalid_range'))
      }
      const res = await getDnsLogs({ from: fromIso, to: toIso, status, limit: 300 })
      if (res.error === 'nextdns_unset') {
        setUnset(true)
        setEvents([])
        return
      }
      setEvents(res.events || [])
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [fromLocal, toLocal, status, t])

  // Initial fetch only — filter edits require explicit Refresh (avoids spam / mid-edit errors).
  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps -- mount once
  }, [])

  const top = useMemo(() => {
    const counts = new Map<string, number>()
    for (const e of events) {
      counts.set(e.domain, (counts.get(e.domain) || 0) + 1)
    }
    return [...counts.entries()]
      .map(([domain, count]) => ({ domain, count }))
      .sort((a, b) => b.count - a.count)
      .slice(0, 10)
  }, [events])

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 items-end rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-4">
        <label className="text-sm text-ink-700">
          {t('dns_logs.from')}
          <input
            type="datetime-local"
            value={fromLocal}
            onChange={(e) => setFromLocal(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-sm text-ink-700">
          {t('dns_logs.to')}
          <input
            type="datetime-local"
            value={toLocal}
            onChange={(e) => setToLocal(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-sm text-ink-700">
          {t('dns_logs.status')}
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="mt-1 block rounded-md border border-slate-300 px-2 py-1 text-sm"
          >
            <option value="blocked">blocked</option>
            <option value="all">all</option>
          </select>
        </label>
        <button
          type="button"
          onClick={() => void load()}
          className="rounded-lg bg-brand-600 px-3 py-1.5 text-sm font-semibold text-white hover:bg-brand-700"
        >
          {t('dns_logs.refresh')}
        </button>
        <Link to="/dns-denylist" className="text-sm font-semibold text-ink-600 hover:text-ink-900 ml-auto">
          {t('dns_logs.denylist_link')}
        </Link>
      </div>

      {unset ? (
        <div className="rounded-xl bg-amber-50 ring-1 ring-amber-200 px-5 py-6 text-sm text-amber-950">
          {t('dns_logs.unset')}
        </div>
      ) : null}

      {loading ? (
        <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 px-6 py-12 text-center text-sm text-ink-600">
          {t('state.loading')}
        </div>
      ) : null}

      {error ? (
        <div className="rounded-xl bg-white shadow-panel ring-1 ring-red-200 px-6 py-8 text-center text-sm text-red-800">
          {error}
        </div>
      ) : null}

      {!loading && !unset && !error ? (
        <div className="grid lg:grid-cols-2 gap-6">
          <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
            <DnsTopChart rows={top} title={t('dns_logs.top')} />
          </section>
          <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 overflow-x-auto max-h-[28rem] overflow-y-auto">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="text-left text-xs text-ink-600 border-b">
                  <th className="py-2 pr-2">{t('incident.col_time')}</th>
                  <th className="py-2 pr-2">{t('incident.col_domain')}</th>
                  <th className="py-2">{t('dns_logs.status')}</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {events.map((e, i) => (
                  <tr key={`${e.at}-${e.domain}-${i}`}>
                    <td className="py-2 pr-2 text-xs whitespace-nowrap">{formatTime(e.at, lang)}</td>
                    <td className="py-2 pr-2 font-mono text-xs">{e.domain}</td>
                    <td className="py-2 text-xs">{e.status}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {events.length === 0 ? (
              <p className="py-8 text-center text-sm text-ink-600">{t('dns_logs.empty')}</p>
            ) : null}
          </section>
        </div>
      ) : null}
    </div>
  )
}
