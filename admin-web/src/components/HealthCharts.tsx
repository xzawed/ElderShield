import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from 'recharts'
import { useI18n } from '../i18n/useI18n'

const COLORS = ['#0d9488', '#f59e0b']

export default function HealthCharts({ okCount, degradedCount }: { okCount: number; degradedCount: number }) {
  const { t } = useI18n()
  const data = [
    { name: t('chart.ok'), value: okCount },
    { name: t('chart.degraded'), value: degradedCount },
  ].filter((d) => d.value > 0)

  const total = okCount + degradedCount

  if (total === 0) {
    return <p className="text-sm text-ink-600 text-center py-8">—</p>
  }

  return (
    <div className="h-52 w-full">
      <p className="text-sm font-semibold text-ink-950 mb-2">{t('chart.health_title')}</p>
      <ResponsiveContainer width="100%" height="100%">
        <PieChart>
          <Pie
            data={data}
            dataKey="value"
            nameKey="name"
            cx="50%"
            cy="50%"
            innerRadius={48}
            outerRadius={72}
            paddingAngle={2}
          >
            {data.map((entry, index) => (
              <Cell key={entry.name} fill={COLORS[index % COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            contentStyle={{
              borderRadius: 8,
              border: '1px solid #e2e8f0',
              fontFamily: '"Source Sans 3", sans-serif',
            }}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}