import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { useToast } from '../components/toast-context'

export function SettingsView() {
  const { data: cfg, isLoading, error, mutate } = useSWR<Record<string, unknown>>('/config', fetcher)
  const { toast } = useToast()
  const [form, setForm] = useState({
    client_id: '', client_secret: '', playlist_id: '',
    default_fmt: 'mp3', default_quality: 320,
    manual_review_enabled: false,
  })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    if (cfg) setForm(f => ({
      ...f,
      client_id:              (cfg.spotify_client_id      as string)  ?? '',
      client_secret:          (cfg.spotify_client_secret  as string)  ?? '',
      playlist_id:            (cfg.playlist_id            as string)  ?? '',
      default_fmt:            (cfg.default_fmt            as string)  ?? 'mp3',
      default_quality:        (cfg.default_quality        as number)  ?? 320,
      manual_review_enabled:  (cfg.manual_review_enabled  as boolean) ?? false,
    }))
  }, [cfg])

  const save = async () => {
    setSaving(true)
    try {
      await api.post('/config', {
        ...form,
        download_path: '',
        auto_approve_threshold: 85,
        min_score_to_show: 40,
        manual_review_enabled: form.manual_review_enabled,
      })
      mutate()
      toast('Credenciales guardadas', 'success')
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Error al guardar', 'error')
    } finally {
      setSaving(false)
    }
  }

  const test = async () => {
    setTesting(true)
    try {
      const r = await api.get<{ connected: boolean; reason?: string }>('/spotify/status')
      if (r.connected) toast('Conexión Spotify OK', 'success')
      else toast(`Sin conexión: ${r.reason ?? 'desconocido'}`, 'error')
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Verificación falló', 'error')
    } finally {
      setTesting(false)
    }
  }

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div className="settings-wrap">
      <h1>Configuración</h1>

      {error && (
        <div className="settings-card" style={{ borderColor: 'var(--err)', marginBottom: 16 }}>
          <strong style={{ color: 'var(--err)' }}>⚠ No se pudo cargar la configuración:</strong> {error.message}
        </div>
      )}

      <div className="settings-card">
        <div className="field">
          <label htmlFor="spotify-client-id">Spotify Client ID</label>
          <input
            id="spotify-client-id"
            value={form.client_id}
            onChange={e => set('client_id', e.target.value)}
            placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
            disabled={isLoading}
          />
          <div className="hint">
            Créalo gratis en{' '}
            <a href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
              developer.spotify.com/dashboard
            </a>.
          </div>
        </div>

        <div className="field">
          <label htmlFor="spotify-client-secret">Spotify Client Secret</label>
          <input
            id="spotify-client-secret"
            type="password"
            value={form.client_secret}
            onChange={e => set('client_secret', e.target.value)}
            placeholder="••••••••••••••••"
            disabled={isLoading}
          />
        </div>

        <div className="field" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label htmlFor="default-format">Formato por defecto</label>
            <select id="default-format" value={form.default_fmt} onChange={e => set('default_fmt', e.target.value)}>
              <option value="mp3">mp3</option>
              <option value="m4a">m4a</option>
              <option value="opus">opus</option>
            </select>
          </div>
          <div>
            <label htmlFor="default-quality">Calidad por defecto</label>
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
              <strong>Revisión manual de fuente YouTube</strong>
              <span className="hint">Cuando está activo, tracks con baja confianza de match (&lt;65%) muestran un modal para elegir la fuente manualmente. Si está desactivado, siempre se descarga el mejor resultado encontrado.</span>
            </span>
            <input
              type="checkbox"
              checked={form.manual_review_enabled}
              onChange={e => set('manual_review_enabled', e.target.checked)}
              disabled={isLoading}
            />
          </label>
        </div>

        <div className="settings-actions">
          <button className="btn btn-accent" onClick={save} disabled={saving || isLoading}>
            {saving ? <><span className="spinner" /> Guardando…</> : 'Guardar cambios'}
          </button>
          <button className="btn btn-ghost" onClick={test} disabled={testing || isLoading}>
            {testing ? 'Verificando…' : 'Verificar credenciales'}
          </button>
        </div>
      </div>

      <section className="settings-help" aria-label="Guia para crear una Spotify App">
        <div className="help-head">
          <div>
            <span className="kicker">Spotify App</span>
            <h2>Configura tus credenciales</h2>
          </div>
          <a className="btn btn-ghost sm" href="https://developer.spotify.com/dashboard" target="_blank" rel="noreferrer">
            Abrir dashboard
          </a>
        </div>

        <div className="help-steps">
          <div className="help-step">
            <span>1</span>
            <div>
              <h3>Crea la app</h3>
              <p>En el dashboard de Spotify, usa Create app y ponle cualquier nombre interno.</p>
            </div>
          </div>
          <div className="help-step">
            <span>2</span>
            <div>
              <h3>Copia las llaves</h3>
              <p>Abre Settings y pega Client ID y Client Secret en los campos de arriba.</p>
            </div>
          </div>
          <div className="help-step">
            <span>3</span>
            <div>
              <h3>Verifica acceso</h3>
              <p>Guarda cambios y usa Verificar credenciales antes de buscar playlists.</p>
            </div>
          </div>
        </div>

        <div className="redirect-box">
          <div>
            <strong>Redirect URI</strong>
            <p>Si Spotify te pide una URL de redireccionamiento, agrega esta para desarrollo local.</p>
          </div>
          <code>http://localhost:8000</code>
        </div>
      </section>

      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 24, textAlign: 'center' }}>
        Backend: <code style={{ fontFamily: 'var(--font-mono)' }}>localhost:8000</code> ·{' '}
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">Swagger Docs</a>
      </p>
    </div>
  )
}
