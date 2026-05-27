import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { useToast } from '../components/Toast'

export function SettingsView() {
  const { data: cfg, isLoading, error, mutate } = useSWR<Record<string, unknown>>('/config', fetcher)
  const { toast } = useToast()
  const [form, setForm] = useState({
    client_id: '', client_secret: '', playlist_id: '',
    default_fmt: 'mp3', default_quality: 320,
  })
  const [saving, setSaving] = useState(false)
  const [testing, setTesting] = useState(false)

  useEffect(() => {
    if (cfg) setForm(f => ({
      ...f,
      client_id:       (cfg.spotify_client_id     as string) ?? '',
      client_secret:   (cfg.spotify_client_secret as string) ?? '',
      playlist_id:     (cfg.playlist_id           as string) ?? '',
      default_fmt:     (cfg.default_fmt           as string) ?? 'mp3',
      default_quality: (cfg.default_quality       as number) ?? 320,
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
          <label>Spotify Client ID</label>
          <input
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
          <label>Spotify Client Secret</label>
          <input
            type="password"
            value={form.client_secret}
            onChange={e => set('client_secret', e.target.value)}
            placeholder="••••••••••••••••"
            disabled={isLoading}
          />
        </div>

        <div className="field" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
          <div>
            <label>Formato por defecto</label>
            <select value={form.default_fmt} onChange={e => set('default_fmt', e.target.value)}>
              <option value="mp3">mp3</option>
              <option value="m4a">m4a</option>
              <option value="opus">opus</option>
            </select>
          </div>
          <div>
            <label>Calidad por defecto</label>
            <select value={form.default_quality} onChange={e => set('default_quality', Number(e.target.value))}>
              <option value={320}>320 kbps</option>
              <option value={192}>192 kbps</option>
              <option value={128}>128 kbps</option>
            </select>
          </div>
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

      <p style={{ fontSize: 12, color: 'var(--ink-faint)', marginTop: 24, textAlign: 'center' }}>
        Backend: <code style={{ fontFamily: 'var(--font-mono)' }}>localhost:8000</code> ·{' '}
        <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer">Swagger Docs</a>
      </p>
    </div>
  )
}
