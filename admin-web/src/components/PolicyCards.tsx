import { useI18n } from '../i18n/useI18n'

export type PolicySummary = {
  countryCount: number
  tldCount: number
  bundleVersion: number
  enrollOpen: boolean
}

export default function PolicyCards({ policy }: { policy: PolicySummary }) {
  const { t } = useI18n()

  const cards = [
    { label: t('policy.countries'), value: String(policy.countryCount) },
    { label: t('policy.tlds'), value: String(policy.tldCount) },
    { label: t('policy.bundle'), value: `v${policy.bundleVersion}` },
    {
      label: t('policy.enroll'),
      value: policy.enrollOpen ? t('policy.enroll_on') : t('policy.enroll_off'),
    },
  ]

  return (
    <div className="grid grid-cols-2 gap-3">
      {cards.map((card) => (
        <div
          key={card.label}
          className="rounded-xl bg-white px-4 py-3 shadow-panel ring-1 ring-slate-200"
        >
          <p className="text-xs font-medium text-ink-600">{card.label}</p>
          <p className="mt-1 text-lg font-semibold text-ink-950">{card.value}</p>
        </div>
      ))}
    </div>
  )
}