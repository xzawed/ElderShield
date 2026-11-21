import { describe, it } from 'node:test'
import assert from 'node:assert/strict'

function asList(v) {
  if (!Array.isArray(v)) return []
  return v.filter((x) => x && typeof x === 'object')
}

function mergeIncidentTimeline(payload) {
  if (!payload) return []
  const items = []
  for (const c of asList(payload.calls)) {
    items.push({ at: String(c.at || ''), kind: 'call', label: `${c.countryIso} · ${c.decision}` })
  }
  for (const a of asList(payload.apps)) {
    items.push({
      at: String(a.firstSeenAt || a.at || ''),
      kind: 'app',
      label: String(a.packageName || 'app'),
    })
  }
  const dns = payload.dns && typeof payload.dns === 'object' ? payload.dns : {}
  for (const e of asList(dns.events)) {
    items.push({ at: String(e.at || ''), kind: 'dns', label: String(e.domain || '—') })
  }
  return items.sort((x, y) => (Date.parse(x.at) || 0) - (Date.parse(y.at) || 0))
}

describe('mergeIncidentTimeline', () => {
  it('sorts mixed axes by time', () => {
    const out = mergeIncidentTimeline({
      calls: [{ at: '2026-11-21T12:00:00Z', countryIso: 'CN', decision: 'Reject' }],
      apps: [{ firstSeenAt: '2026-11-21T11:00:00Z', packageName: 'com.risk' }],
      dns: { events: [{ at: '2026-11-21T13:00:00Z', domain: 'baidu.com' }] },
    })
    assert.equal(out.map((x) => x.kind).join(','), 'app,call,dns')
  })

  it('handles empty payload', () => {
    assert.deepEqual(mergeIncidentTimeline(undefined), [])
  })
})
