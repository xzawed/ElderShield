import { Link } from 'react-router-dom'
import type { IncidentOut } from '../api/admin'
import { useI18n } from '../i18n/useI18n'

export type IncidentRow = IncidentOut & { deviceUuid: string }

function shortUuid(uuid: string): string {
  if (uuid.length <= 12) return uuid
  return `${uuid.slice(0, 8)}…`
}

function formatTime(iso: string, lang: string): string {
  try {
    return new Intl.DateTimeFormat(lang === 'ko' ? 'ko-KR' : 'en-US', {
      dateStyle: 'short',
      timeStyle: 'short',
    }).format(new Date(iso))
  } catch {
    return iso
  }
}

export default function ThreatTable({ rows }: { rows: IncidentRow[] }) {
  const { t, lang } = useI18n()

  if (rows.length === 0) {
    return (
      <p className="text-sm text-ink-600 py-6 text-center">{t('threats.empty')}</p>
    )
  }

  return (
    <div className="overflow-x-auto -mx-2">
      <table className="min-w-full text-sm">
        <thead>
          <tr className="text-left text-xs font-semibold uppercase tracking-wide text-ink-600 border-b border-slate-200">
            <th className="px-2 py-2">{t('threats.col_time')}</th>
            <th className="px-2 py-2">{t('threats.col_device')}</th>
            <th className="px-2 py-2">{t('threats.col_triggers')}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={row.incidentId} className="hover:bg-slate-50">
              <td className="px-2 py-2.5 whitespace-nowrap text-ink-800">
                <Link
                  to={`/incidents/${row.incidentId}`}
                  className="font-medium text-brand-700 hover:text-brand-800"
                >
                  {formatTime(row.triggeredAt, lang)}
                </Link>
              </td>
              <td className="px-2 py-2.5 font-mono text-xs text-ink-600">
                <Link to={`/devices/${row.deviceUuid}`} className="hover:underline">
                  {shortUuid(row.deviceUuid)}
                </Link>
              </td>
              <td className="px-2 py-2.5 text-ink-800">
                <span className="line-clamp-2">{row.triggers.join(', ') || '—'}</span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}