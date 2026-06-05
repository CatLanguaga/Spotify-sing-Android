import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { useToast } from '../components/toast-context'
import { usePreferences } from '../preferences'

type YtCookiesStatus = {
  present: boolean
  uploaded_at?: number | null
  last_validated_at?: number | null
  last_status?: string | null
}

function fmtTimestamp(ts?: number | null) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString()
}

function YouTubeCookiesCard() {
  const { data: status, mutate } = useSWR<YtCookiesStatus>('/admin/youtube-cookies/status', fetcher)
  const { toast } = useToast()
  const [content, setContent] = useState('')
  const [validateLive, setValidateLive] = useState(true)
  const [busy, setBusy] = useState(false)

  const upload = async () => {
    if (!content.trim()) return
    setBusy(true)
    try {
      await api.post('/admin/youtube-cookies', { content, validate_live: validateLive })
      setContent('')
      await mutate()
      toast('YouTube cookies saved.', 'success')
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Upload failed', 'error')
    } finally {
      setBusy(false)
    }
  }

  const purge = async () => {
    if (!confirm('Delete the stored YouTube cookies?')) return
    setBusy(true)
    try {
      await api.delete('/admin/youtube-cookies')
      await mutate()
      toast('YouTube cookies removed.', 'info')
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Delete failed', 'error')
    } finally {
      setBusy(false)
    }
  }

  const statusLabel = status?.last_status || (status?.present ? 'uploaded' : 'none')
  const badStatus = (status?.last_status || '').startsWith('invalid')

  return (
    <div className="settings-card" style={{ marginTop: 16 }}>
      <h2 style={{ marginTop: 0 }}>YouTube cookies (bot-detection bypass)</h2>
      <p className="hint" style={{ marginTop: 0 }}>
        Datacenter IPs often hit YouTube's "Sign in to confirm you're not a bot" wall.
        Upload <code>cookies.txt</code> (Netscape format) from a <strong>dedicated, throwaway</strong>{' '}
        YouTube account so pytubefix requests look like an authenticated session.
        Cookies are encrypted at rest with <code>ADMIN_DATA_KEY</code>.
      </p>

      <div className="field" style={{ display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <span>Status:&nbsp;
          <strong style={{ color: badStatus ? 'var(--err)' : (status?.present ? 'var(--ok)' : 'var(--ink-faint)') }}>
            {statusLabel}
          </strong>
        </span>
        <span className="hint">Uploaded: {fmtTimestamp(status?.uploaded_at)}</span>
        <span className="hint">Last check: {fmtTimestamp(status?.last_validated_at)}</span>
      </div>

      <details style={{ marginTop: 12 }}>
        <summary style={{ cursor: 'pointer' }}>How to export cookies.txt</summary>
        <ol style={{ fontSize: 13, lineHeight: 1.6, marginTop: 8 }}>
          <li>Install a browser extension like <em>Get cookies.txt LOCALLY</em> (Chrome/Firefox).</li>
          <li>Log into <code>youtube.com</code> with a dedicated Google account (NOT your personal one).</li>
          <li>Open the extension on a YouTube page and export → cookies.txt.</li>
          <li>Open the file in a text editor, copy the entire contents, paste below, click Upload.</li>
          <li>YouTube may sanction the account if it detects automation — burn it, don't reuse it.</li>
        </ol>
      </details>

      <div className="field" style={{ marginTop: 12 }}>
        <label htmlFor="yt-cookies-content">Paste cookies.txt contents</label>
        <textarea
          id="yt-cookies-content"
          value={content}
          onChange={e => setContent(e.target.value)}
          rows={6}
          placeholder="# Netscape HTTP Cookie File&#10;.youtube.com&#9;TRUE&#9;/&#9;TRUE&#9;1234567890&#9;SID&#9;…"
          style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}
        />
      </div>

      <div className="field">
        <label className="toggle-row">
          <span>
            <strong>Validate against YouTube on upload</strong>
            <span className="hint">Makes one test request to confirm cookies aren't already rejected.</span>
          </span>
          <input
            type="checkbox"
            checked={validateLive}
            onChange={e => setValidateLive(e.target.checked)}
          />
        </label>
      </div>

      <div className="settings-actions">
        <button className="btn btn-accent" onClick={upload} disabled={busy || !content.trim()}>
          {busy ? <><span className="spinner" /> Uploading…</> : 'Upload cookies'}
        </button>
        <button className="btn btn-ghost" onClick={purge} disabled={busy || !status?.present}>
          Delete stored cookies
        </button>
      </div>
    </div>
  )
}

type AdminSession = {
  authenticated: boolean
  default_password: boolean
}

type ConfigPayload = Record<string, unknown>

function AdminLogin({ onLoggedIn }: { onLoggedIn: () => void }) {
  const { toast } = useToast()
  const { t } = usePreferences()
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/admin/login', { password })
      setPassword('')
      onLoggedIn()
      toast(t('setLoginOk'), 'success')
    } catch (err) {
      toast(err instanceof Error ? err.message : t('setLoginFailed'), 'error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="settings-wrap">
      <h1>{t('setAdminLogin')}</h1>
      <div className="settings-card">
        <form onSubmit={submit}>
          <div className="field">
            <label htmlFor="admin-password">{t('setAdminPassword')}</label>
            <input
              id="admin-password"
              type="password"
              value={password}
              onChange={e => setPassword(e.target.value)}
              placeholder={t('setAdminPasswordPlaceholder')}
              autoComplete="current-password"
            />
            <div className="hint">{t('setAdminPasswordHint')}</div>
          </div>
          <div className="settings-actions">
            <button className="btn btn-accent" type="submit" disabled={loading || !password}>
              {loading ? <><span className="spinner" /> {t('setSigningIn')}</> : t('setSignIn')}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export function SettingsView() {
  const { data: session, isLoading: sessionLoading, mutate: mutateSession } = useSWR<AdminSession>('/admin/session', fetcher)
  const isAdmin = !!session?.authenticated
  const { data: cfg, isLoading, error, mutate } = useSWR<ConfigPayload>(isAdmin ? '/config' : null, fetcher)
  const { toast } = useToast()
  const { t } = usePreferences()
  const [form, setForm] = useState({
    client_id: '', client_secret: '', playlist_id: '',
    default_fmt: 'mp3', default_quality: 320,
    manual_review_enabled: false,
    max_concurrent_downloads: 3,
  })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    if (cfg) setForm(f => ({
      ...f,
      client_id:             (cfg.spotify_client_id      as string)  ?? '',
      client_secret:         (cfg.spotify_client_secret  as string)  ?? '',
      playlist_id:           (cfg.playlist_id            as string)  ?? '',
      default_fmt:           (cfg.default_fmt            as string)  ?? 'mp3',
      default_quality:       (cfg.default_quality        as number)  ?? 320,
      manual_review_enabled: (cfg.manual_review_enabled  as boolean) ?? false,
      max_concurrent_downloads: (cfg.max_concurrent_downloads as number) ?? 3,
    }))
  }, [cfg])

  if (sessionLoading) {
    return <div className="settings-wrap"><h1>{t('setTitle')}</h1></div>
  }

  if (!isAdmin) {
    return <AdminLogin onLoggedIn={() => { void mutateSession() }} />
  }

  const save = async () => {
    setSaving(true)
    try {
      await api.post('/config', {
        ...form,
        download_path: '',
        auto_approve_threshold: 85,
        min_score_to_show: 40,
        manual_review_enabled: form.manual_review_enabled,
        max_concurrent_downloads: form.max_concurrent_downloads,
      })
      mutate()
      toast(t('setSaved'), 'success')
    } catch (e) {
      toast(e instanceof Error ? e.message : t('setSaveFailed'), 'error')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    try {
      const r = await api.get<{ connected: boolean; reason?: string }>('/spotify/status')
      if (r.connected) toast(t('setSpotifyOk'), 'success')
      else toast(t('setSpotifyFail')(r.reason ?? t('setUnknown')), 'error')
    } catch (e) {
      toast(e instanceof Error ? e.message : t('setVerifyFailed'), 'error')
    } finally {
      setTesting(false)
    }
  }

  const logout = async () => {
    try {
      await api.post('/admin/logout', {})
      await mutateSession()
      toast(t('setSignedOut'), 'info')
    } catch (e) {
      toast(e instanceof Error ? e.message : t('setSignOutFailed'), 'error')
    }
  }

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="settings-wrap">
      <div className="settings-title-row">
        <h1>{t('setTitle')}</h1>
        <button className="btn btn-ghost sm" onClick={logout}>{t('setSignOut')}</button>
      </div>

      {session?.default_password && (
        <div className="settings-card" style={{ borderColor: 'var(--warn)', marginBottom: 16 }}>
          <strong>{t('setDefaultPwWarn')}</strong>{t('setDefaultPwHint')}
        </div>
      )}

      {error && (
        <div className="settings-card" style={{ borderColor: 'var(--err)', marginBottom: 16 }}>
          <strong style={{ color: 'var(--err)' }}>{t('setLoadError')}</strong> {error.message}
        </div>
      )}

      <div className="settings-card">
        <div className="field">
          <label htmlFor="spotify-client-id">{t('setClientId')}</label>
          <input
            id="spotify-client-id"
            value={form.client_id}
            onChange={e => set('client_id', e.target.value)}
            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            disabled={isLoading}
          />
          <div className="hint">
            {t('setCreateAtFree')}{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
              developer.spotify.com/dashboard
            </a>.
          </div>
        </div>

        <div className="field">
          <label htmlFor="spotify-client-secret">{t('setClientSecret')}</label>
          <input
            id="spotify-client-secret"
            type="password"
            value={form.client_secret}
            onChange={e => set('client_secret', e.target.value)}
            placeholder="••••••••••••••••"
            disabled={isLoading}
            autoComplete="off"
          />
        </div>

        <div className="field" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label htmlFor="default-format">{t('setDefaultFormat')}</label>
            <select id="default-format" value={form.default_fmt} onChange={e => set('default_fmt', e.target.value)}>
              <option value="mp3">mp3</option>
              <option value="m4a">m4a</option>
              <option value="opus">opus</option>
            </select>
          </div>
          <div>
            <label htmlFor="default-quality">{t('setDefaultQuality')}</label>
            <select id="default-quality" value={form.default_quality} onChange={e => set('default_quality', Number(e.target.value))}>
              <option value={320}>320 kbps</option>
              <option value={192}>192 kbps</option>
              <option value={128}>128 kbps</option>
            </select>
          </div>
        </div>

        <div className="field">
          <label className="toggle-row">
            <span>
              <strong>{t('setManualReviewTitle')}</strong>
              <span className="hint">{t('setManualReviewHint')}</span>
            </span>
            <input
              type="checkbox"
              checked={form.manual_review_enabled}
              onChange={e => set('manual_review_enabled', e.target.checked)}
              disabled={isLoading}
            />
          </label>
        </div>

        <div className="field">
          <label htmlFor="max-concurrent-downloads">{t('setParallelDownloads')}</label>
          <input
            id="max-concurrent-downloads"
            type="number"
            min={1}
            max={5}
            value={form.max_concurrent_downloads}
            onChange={e => set('max_concurrent_downloads', Math.max(1, Math.min(5, Number(e.target.value) || 3)))}
            disabled={isLoading}
          />
          <div className="hint">{t('setParallelHint')}</div>
        </div>

        <div className="settings-actions">
          <button className="btn btn-accent" onClick={save} disabled={saving || isLoading}>
            {saving ? <><span className="spinner" /> {t('setSaving')}</> : t('setSave')}
          </button>
          <button className="btn btn-ghost" onClick={test} disabled={testing || isLoading}>
            {testing ? t('setChecking') : t('setVerify')}
          </button>
        </div>
      </div>

      <YouTubeCookiesCard />

      <section className="settings-help" aria-label={t('setSpotifyAppGuide')}>
        <div className="help-head">
          <div>
            <span className="kicker">{t('setSpotifyAppKicker')}</span>
            <h2>{t('setConfigCreds')}</h2>
          </div>
          <a className="btn btn-ghost sm" href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
            {t('setOpenDashboard')}
          </a>
        </div>

        <div className="help-steps">
          <div className="help-step">
            <span>1</span>
            <div>
              <h3>{t('setHelp1Title')}</h3>
              <p>{t('setHelp1Body')}</p>
            </div>
          </div>
          <div className="help-step">
            <span>2</span>
            <div>
              <h3>{t('setHelp2Title')}</h3>
              <p>{t('setHelp2Body')}</p>
            </div>
          </div>
          <div className="help-step">
            <span>3</span>
            <div>
              <h3>{t('setHelp3Title')}</h3>
              <p>{t('setHelp3Body')}</p>
            </div>
          </div>
        </div>

        <div className="redirect-box">
          <div>
            <strong>{t('setRedirectTitle')}</strong>
            <p>{t('setRedirectBody')}</p>
          </div>
          <code>http://localhost:8000</code>
        </div>
      </section>

      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 24, textAlign: 'center' }}>
        {t('setBackend')} <code style={{ fontFamily: 'var(--font-mono)' }}>localhost:8000</code> ·{' '}
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">{t('setSwaggerDocs')}</a>
      </p>
    </div>
  )
}
