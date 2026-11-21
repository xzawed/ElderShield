export type TimelineKind = 'call' | 'app' | 'dns'

export interface TimelineItem {
  at: string
  kind: TimelineKind
  label: string
  detail?: string
}

function asList(v: unknown): Record<string, unknown>[] {
  if (!Array.isArray(v)) return []
  return v.filter((x): x is Record<string, unknown> => !!x && typeof x === 'object')
}

export function mergeIncidentTimeline(payload: Record<string, unknown> | undefined): TimelineItem[] {
  if (!payload) return []
  const items: TimelineItem[] = []

  for (const c of asList(payload.calls)) {
    const at = String(c.at || '')
    const iso = String(c.countryIso || c.country_iso || '—')
    const decision = String(c.decision || '—')
    const last4 = c.last4 != null ? String(c.last4) : ''
    items.push({
      at,
      kind: 'call',
      label: `${iso} · ${decision}`,
      detail: last4 ? `…${last4}` : undefined,
    })
  }

  for (const a of asList(payload.apps)) {
    const at = String(a.firstSeenAt || a.first_seen_at || a.at || '')
    const pkg = String(a.packageName || a.package_name || 'app')
    const score = a.riskScore ?? a.risk_score
    items.push({
      at,
      kind: 'app',
      label: pkg,
      detail: score != null ? `score ${score}` : undefined,
    })
  }

  const dns = payload.dns && typeof payload.dns === 'object' ? (payload.dns as Record<string, unknown>) : {}
  for (const e of asList(dns.events)) {
    items.push({
      at: String(e.at || ''),
      kind: 'dns',
      label: String(e.domain || '—'),
      detail: String(e.action || e.status || 'block'),
    })
  }

  return items.sort((x, y) => {
    const tx = Date.parse(x.at) || 0
    const ty = Date.parse(y.at) || 0
    return tx - ty
  })
}

export function topDnsDomains(
  payload: Record<string, unknown> | undefined,
  limit = 8,
): { domain: string; count: number }[] {
  if (!payload) return []
  const dns = payload.dns && typeof payload.dns === 'object' ? (payload.dns as Record<string, unknown>) : {}
  const counts = new Map<string, number>()
  for (const e of asList(dns.events)) {
    const d = String(e.domain || '').trim()
    if (!d) continue
    counts.set(d, (counts.get(d) || 0) + 1)
  }
  return [...counts.entries()]
    .map(([domain, count]) => ({ domain, count }))
    .sort((a, b) => b.count - a.count)
    .slice(0, limit)
}
