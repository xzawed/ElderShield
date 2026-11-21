import { useCallback, useEffect, useMemo, useState } from 'react'
import { type AuditRow, listAudit } from '../api/admin'
import { useI18n } from '../i18n/useI18n'

function formatTime(iso: string | null, lang: string): string {
  if (!iso) return '—'
  try {
    return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
      dateStyle: 'short',
      timeStyle: 'medium',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export default function AuditPage() {
  const { t, lang } = useI18n()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [rows, setRows] = useState<AuditRow[]>([])
  const [actionFilter, setActionFilter] = useState('')
  const [resourceFilter, setResourceFilter] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows(await listAudit(300))
    } catch (e) {
      setError(e instanceof Error ? e.message : t('state.error'))
    } finally {
      setLoading(false)
    }
  }, [t])

  useEffect(() => {
    void load()
  }, [load])

  const filtered = useMemo(() => {
    return rows.filter((r) => {
      if (actionFilter && !r.action.toLowerCase().includes(actionFilter.toLowerCase())) return false
      if (
        resourceFilter &&
        !(r.resourceType || '').toLowerCase().includes(resourceFilter.toLowerCase())
      ) {
        return false
      }
      return true
    })
  }, [rows, actionFilter, resourceFilter])

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
    <div className="space-y-4">
      <div className="flex flex-wrap gap-3">
        <label className="text-sm text-ink-700">
          {t('audit.filter_action')}
          <input
            value={actionFilter}
            onChange={(e) => setActionFilter(e.target.value)}
            className="ml-2 rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
        <label className="text-sm text-ink-700">
          {t('audit.filter_resource')}
          <input
            value={resourceFilter}
            onChange={(e) => setResourceFilter(e.target.value)}
            className="ml-2 rounded-md border border-slate-300 px-2 py-1 text-sm"
          />
        </label>
      </div>

      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ink-600">
              <th className="px-4 py-3">{t('audit.col_time')}</th>
              <th className="px-4 py-3">{t('audit.col_actor')}</th>
              <th className="px-4 py-3">{t('audit.col_action')}</th>
              <th className="px-4 py-3">{t('audit.col_resource')}</th>
              <th className="px-4 py-3">{t('audit.col_detail')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filtered.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50">
                <td className="px-4 py-2 whitespace-nowrap text-xs text-ink-600">
                  {formatTime(r.createdAt, lang)}
                </td>
                <td className="px-4 py-2 text-ink-800">{r.actor}</td>
                <td className="px-4 py-2 font-medium text-ink-900">{r.action}</td>
                <td className="px-4 py-2 text-xs text-ink-700">
                  {r.resourceType}
                  {r.resourceId ? (
                    <span className="text-ink-500"> · {r.resourceId}</span>
                  ) : null}
                </td>
                <td className="px-4 py-2 text-xs text-ink-600 max-w-xs truncate" title={r.detail || ''}>
                  {r.detail || '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-600">{t('audit.empty')}</p>
        ) : null}
      </div>
    </div>
  )
}
