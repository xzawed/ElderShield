import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

export default function DnsTopChart({
  rows,
  title,
}: {
  rows: { domain: string; count: number }[]
  title: string
}) {
  if (rows.length === 0) return null
  return (
    <div className="h-56">
      <p className="text-xs font-semibold text-ink-600 mb-2">{title}</p>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={rows} layout="vertical" margin={{ left: 8, right: 16 }}>
          <XAxis type="number" allowDecimals={false} tick={{ fontSize: 11 }} />
          <YAxis
            type="category"
            dataKey="domain"
            width={120}
            tick={{ fontSize: 10 }}
          />
          <Tooltip />
          <Bar dataKey="count" fill="#0d9488" radius={[0, 4, 4, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
