import { useCallback, useEffect, useState } from 'react'
import { listAllowlist } from '../api/admin'
import { useI18n } from '../i18n/useI18n'

type AllowRow = { packageName: string; note?: string | null; createdAt?: string | null }

export default function AllowlistPage() {
  const { t, lang } = useI18n()
  const [rows, setRows] = useState<AllowRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows(await listAllowlist())
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
  if (error) {
    return (
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-red-200 px-6 py-8 text-center space-y-3">
        <p className="text-sm text-red-800">{error}</p>
        <button type="button" onClick={() => void load()} className="text-sm font-semibold text-brand-700">
          {t('state.retry')}
        </button>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <p className="text-sm text-ink-600">{t('policy.legacy_hint')}</p>
      <div className="rounded-xl bg-white shadow-panel ring-1 ring-slate-200 overflow-x-auto">
        <table className="min-w-full text-sm">
          <thead className="bg-slate-50 border-b text-left text-xs font-semibold uppercase tracking-wide text-ink-600">
            <tr>
              <th className="px-4 py-3">{t('allowlist.col_package')}</th>
              <th className="px-4 py-3">{t('allowlist.col_note')}</th>
              <th className="px-4 py-3">{t('allowlist.col_created')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.packageName} className="hover:bg-slate-50">
                <td className="px-4 py-2.5 font-mono text-xs">{r.packageName}</td>
                <td className="px-4 py-2.5 text-ink-700">{r.note || '—'}</td>
                <td className="px-4 py-2.5 text-xs text-ink-600">
                  {r.createdAt
                    ? new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
                        dateStyle: 'short',
                        timeStyle: 'short',
                      }).format(new Date(r.createdAt))
                    : '—'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-600">{t('allowlist.empty')}</p>
        ) : null}
      </div>
    </div>
  )
}
