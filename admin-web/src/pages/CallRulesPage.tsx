import { useCallback, useEffect, useState } from 'react'
import { listCallRules } from '../api/admin'
import { useI18n } from '../i18n/useI18n'

type CallRuleRow = {
  id: string
  countryCodes?: string[]
  whitelist?: string[]
  enabled?: boolean
  version?: number
}

export default function CallRulesPage() {
  const { t } = useI18n()
  const [rows, setRows] = useState<CallRuleRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      setRows((await listCallRules()) as CallRuleRow[])
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
              <th className="px-4 py-3">{t('call_rules.col_countries')}</th>
              <th className="px-4 py-3">{t('call_rules.col_whitelist')}</th>
              <th className="px-4 py-3">{t('call_rules.col_enabled')}</th>
              <th className="px-4 py-3">{t('call_rules.col_version')}</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {rows.map((r) => (
              <tr key={r.id} className="hover:bg-slate-50">
                <td className="px-4 py-2.5 font-mono text-xs">{(r.countryCodes || []).join(', ') || '—'}</td>
                <td className="px-4 py-2.5 font-mono text-xs">{(r.whitelist || []).join(', ') || '—'}</td>
                <td className="px-4 py-2.5">{r.enabled ? t('yes') : t('no')}</td>
                <td className="px-4 py-2.5 tabular-nums">{r.version ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 ? (
          <p className="px-4 py-8 text-center text-sm text-ink-600">{t('call_rules.empty')}</p>
        ) : null}
      </div>
    </div>
  )
}
