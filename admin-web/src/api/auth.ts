import { apiPost } from './client'

export type LoginResult =
  | { ok: true }
  | { ok: false; error: 'invalid' | 'rate' | string }

export async function login(apiKey: string): Promise<LoginResult> {
  const r = await fetch('/admin/ui/api/login', {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ apiKey }),
  })
  const data = (await r.json()) as LoginResult
  if (!r.ok) return data
  return data
}

export async function loginOrThrow(apiKey: string): Promise<void> {
  const data = await login(apiKey)
  if (!data.ok) {
    throw new Error(data.error)
  }
}

// Re-export for callers that need generic POST with session cookies.
export { apiPost }