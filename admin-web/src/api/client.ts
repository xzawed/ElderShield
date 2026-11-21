/** Must match backend app.web.auth.ADMIN_UI_REQUEST_HEADER* (cookie-auth CSRF). */
const ADMIN_UI_HEADERS: Record<string, string> = {
  'X-ElderShield-Admin': '1',
}

export async function apiGet<T>(path: string): Promise<T> {
  const r = await fetch(path, {
    credentials: 'include',
    headers: ADMIN_UI_HEADERS,
  })
  if (r.status === 401) {
    window.location.assign('/admin/ui/login')
    throw new Error('unauthorized')
  }
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  return r.json() as Promise<T>
}

export async function apiPost<T>(path: string, body: unknown): Promise<T> {
  const r = await fetch(path, {
    method: 'POST',
    credentials: 'include',
    headers: { ...ADMIN_UI_HEADERS, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  if (r.status === 401) {
    window.location.assign('/admin/ui/login')
    throw new Error('unauthorized')
  }
  if (!r.ok) throw new Error(`HTTP ${r.status}`)
  if (r.status === 204) return undefined as T
  return r.json() as Promise<T>
}