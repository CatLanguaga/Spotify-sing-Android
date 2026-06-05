// In Vite dev (port 5173) the backend runs separately on 8000; everywhere else
// (prod single-container, Coolify behind SSL/proxy) the SPA is served same-origin
// by FastAPI, so a relative /api keeps working regardless of host/port/scheme.
export const API_BASE =
  window.location.port === '5173'
    ? `${window.location.protocol}//${window.location.hostname}:8001/api`
    : '/api'

// Double-submit CSRF cookie set by the backend on /admin/session and /admin/login.
// We read it here and echo it on every mutating request so authenticated admin
// endpoints accept us. Falls back to '' if the cookie is missing — the backend
// will respond 403, which the caller surfaces normally.
const CSRF_COOKIE_NAMES = ['__Host-spotify_sing_csrf', 'spotify_sing_csrf']

function readCsrfCookie(): string {
  if (typeof document === 'undefined' || !document.cookie) return ''
  for (const raw of document.cookie.split(';')) {
    const [name, ...rest] = raw.trim().split('=')
    if (CSRF_COOKIE_NAMES.includes(name)) {
      return decodeURIComponent(rest.join('='))
    }
  }
  return ''
}

const MUTATING_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const method = (init?.method || 'GET').toUpperCase()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(init?.headers as Record<string, string> | undefined),
  }
  if (MUTATING_METHODS.has(method)) {
    const token = readCsrfCookie()
    if (token) headers['X-CSRF-Token'] = token
  }
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...init,
    headers,
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
