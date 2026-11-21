export type KpiItem = {
  key: string
  label: string
  value: number | string
  accent?: 'default' | 'warn' | 'risk'
}

const accentRing: Record<NonNullable<KpiItem['accent']>, string> = {
  default: 'ring-slate-200',
  warn: 'ring-amber-200',
  risk: 'ring-red-200',
}

const accentValue: Record<NonNullable<KpiItem['accent']>, string> = {
  default: 'text-ink-950',
  warn: 'text-amber-900',
  risk: 'text-red-800',
}

export default function KpiStrip({ items }: { items: KpiItem[] }) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3 animate-kpi-fade-in">
      {items.map((item) => (
        <div
          key={item.key}
          className={`rounded-xl bg-white px-4 py-3 shadow-panel ring-1 ${accentRing[item.accent ?? 'default']}`}
        >
          <p className="text-xs font-medium text-ink-600">{item.label}</p>
          <p className={`mt-1 text-2xl font-semibold tabular-nums ${accentValue[item.accent ?? 'default']}`}>
            {item.value}
          </p>
        </div>
      ))}
    </div>
  )
}