// In Vite dev (port 5173) the backend runs separately on 8000; everywhere else
// (prod single-container, Coolify behind SSL/proxy) the SPA is served same-origin
// by FastAPI, so a relative /api keeps working regardless of host/port/scheme.
export const API_BASE =
  window.location.port === '5173'
    ? `${window.location.protocol}//${window.location.hostname}:8000/api`
    : '/api'

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    ...init,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail ?? res.statusText)
  }
  return res.json()
}

export function fetcher<T>(url: string): Promise<T> {
  return apiFetch<T>(url)
}

export const api = {
  get: <T>(path: string) => apiFetch<T>(path),
  post: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'POST', body: JSON.stringify(body) }),
  patch: <T>(path: string, body: unknown) =>
    apiFetch<T>(path, { method: 'PATCH', body: JSON.stringify(body) }),
  delete: <T>(path: string) => apiFetch<T>(path, { method: 'DELETE' }),
}
