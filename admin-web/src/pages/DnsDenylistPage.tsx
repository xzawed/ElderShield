import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { type DnsDenylistOut, getDnsDenylist } from '../api/admin'
import { useI18n } from '../i18n/useI18n'

export default function DnsDenylistPage() {
  const { t } = useI18n()
  const [data, setData] = useState<DnsDenylistOut | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setData(await getDnsDenylist())
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

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
        <p className="text-sm text-red-800">{error || t('state.error')}</p>
        <button type="button" onClick={() => void load()} className="text-sm font-semibold text-brand-700">
          {t('state.retry')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3 text-sm">
        <Link to="/dns-logs" className="font-semibold text-brand-700">
          {t('nav.dns_logs')} →
        </Link>
        <span className="text-ink-600">
          {t('dns_denylist.count')}: {data.count}
        </span>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
          <h2 className="text-sm font-semibold text-ink-950 mb-2">{t('dns_denylist.tlds')}</h2>
          <p className="font-mono text-xs text-ink-700 break-all">{(data.tlds || []).join(', ') || '—'}</p>
        </section>
        <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5">
          <h2 className="text-sm font-semibold text-ink-950 mb-2">{t('dns_denylist.countries')}</h2>
          <p className="font-mono text-xs text-ink-700 break-all">
            {(data.countries || []).join(', ') || '—'}
          </p>
        </section>
      </div>
      <section className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 p-5 max-h-80 overflow-y-auto">
        <h2 className="text-sm font-semibold text-ink-950 mb-2">{t('dns_denylist.domains')}</h2>
        <ul className="text-xs font-mono text-ink-700 space-y-1">
          {(data.domains || []).slice(0, 200).map((d) => (
            <li key={d}>{d}</li>
          ))}
        </ul>
      </section>
    </div>
  )
}
