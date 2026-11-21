type Variant = 'ok' | 'warn' | 'risk' | 'muted'

const styles: Record<Variant, string> = {
  ok: 'bg-emerald-50 text-emerald-800 ring-emerald-200',
  warn: 'bg-amber-50 text-amber-900 ring-amber-200',
  risk: 'bg-red-50 text-red-800 ring-red-200',
  muted: 'bg-slate-100 text-ink-600 ring-slate-200',
}

export default function StatusBadge({
  label,
  variant = 'muted',
}: {
  label: string
  variant?: Variant
}) {
  return (
    <span
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ring-1 ring-inset ${styles[variant]}`}
    >
      {label}
    </span>
  )
}