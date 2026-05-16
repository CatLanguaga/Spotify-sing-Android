import { useEffect, useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'

const input = {
  background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 5,
  color: '#fff', fontSize: 12, padding: '7px 10px', width: '100%',
  outline: 'none', boxSizing: 'border-box' as const,
}

const label = { fontSize: 11, color: '#B3B3B3', display: 'block', marginBottom: 4 }

const shimmer = {
  background: 'linear-gradient(90deg, #1A1A1A 0%, #2A2A2A 50%, #1A1A1A 100%)',
  backgroundSize: '200% 100%',
  animation: 'skeletonPulse 1.6s linear infinite',
  borderRadius: 5,
}

function FieldSkeleton() {
  return (
    <div>
      <div style={{ ...shimmer, height: 11, width: 100, marginBottom: 6 }} />
      <div style={{ ...shimmer, height: 32, width: '100%' }} />
    </div>
  )
}

export function SettingsView() {
  const { data: cfg, isLoading: cfgLoading, error: cfgError, mutate } = useSWR<Record<string, unknown>>('/config', fetcher)
  const [form, setForm] = useState({
    client_id: '', client_secret: '', download_path: '', playlist_id: '',
    auto_approve_threshold: 85, min_score_to_show: 40,
  })
  const [saving,  setSaving]  = useState(false)
  const [saved,   setSaved]   = useState(false)
  const [saveErr, setSaveErr] = useState<string | null>(null)

  useEffect(() => {
    if (cfg) setForm(f => ({
      ...f,
      client_id:     (cfg.spotify_client_id     as string) ?? '',
      client_secret: (cfg.spotify_client_secret as string) ?? '',
      download_path: (cfg.download_folder       as string) ?? '',
      playlist_id:   (cfg.playlist_id           as string) ?? '',
    }))
  }, [cfg])

  const save = async () => {
    setSaving(true)
    setSaveErr(null)
    try {
      await api.post('/config', form)
      mutate()
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch (e: unknown) {
      setSaveErr(e instanceof Error ? e.message : 'Save failed')
    } finally {
      setSaving(false)
    }
  }

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' }}>Settings</h1>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {saveErr && <span style={{ fontSize: 11, color: '#E22D44' }}>{saveErr}</span>}
          <button
            onClick={save}
            disabled={saving || cfgLoading}
            style={{
              background: saved ? '#15803d' : '#1DB954',
              color: '#000', border: 'none', borderRadius: 5,
              padding: '6px 16px', fontSize: 12, fontWeight: 700,
              cursor: saving ? 'not-allowed' : 'pointer',
              opacity: saving ? 0.7 : 1,
              display: 'flex', alignItems: 'center', gap: 6,
              transition: 'background 0.2s',
            }}
          >
            {saving && (
              <span style={{
                width: 10, height: 10, borderRadius: '50%',
                border: '2px solid rgba(0,0,0,0.3)', borderTopColor: '#000',
                display: 'inline-block', animation: 'spin 0.7s linear infinite',
              }} />
            )}
            {saved ? '✓ Saved' : saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: 20 }}>
        {/* Config load error */}
        {cfgError && (
          <div style={{
            marginBottom: 20, padding: '12px 16px',
            background: 'rgba(226,45,68,0.06)', border: '1px solid rgba(226,45,68,0.25)',
            borderRadius: 8, fontSize: 12, color: '#E22D44',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <span>⚠</span> Failed to load config: {cfgError.message}
            <button onClick={() => mutate()} style={{ marginLeft: 'auto', fontSize: 11, color: '#888', background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 4, padding: '3px 8px', cursor: 'pointer' }}>
              Retry
            </button>
          </div>
        )}

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 32, maxWidth: 960 }}>
          {/* Left — Config */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: '#666', marginBottom: 16, textTransform: 'uppercase' }}>
              Configuration
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
              {cfgLoading ? (
                Array.from({ length: 4 }).map((_, i) => <FieldSkeleton key={i} />)
              ) : (
                <>
                  <div>
                    <span style={label}>Spotify Client ID</span>
                    <input style={input} value={form.client_id} onChange={e => set('client_id', e.target.value)} placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx" />
                  </div>
                  <div>
                    <span style={label}>Spotify Client Secret</span>
                    <input style={input} type="password" value={form.client_secret} onChange={e => set('client_secret', e.target.value)} placeholder="••••••••••••••••" />
                  </div>
                  <div>
                    <span style={label}>Download Path</span>
                    <input style={input} value={form.download_path} onChange={e => set('download_path', e.target.value)} placeholder="C:/Users/.../Music" />
                  </div>
                  <div>
                    <span style={label}>Spotify Playlist ID</span>
                    <input style={input} value={form.playlist_id} onChange={e => set('playlist_id', e.target.value)} placeholder="37i9dQZF1DX4SBhb3fqCJd" />
                    <span style={{ fontSize: 10, color: '#555', marginTop: 4, display: 'block' }}>
                      ID que aparece en la URL de la playlist: spotify.com/playlist/<b style={{ color: '#888' }}>{'<ID>'}</b>
                    </span>
                  </div>
                </>
              )}

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={label}>Auto-approve threshold</span>
                  <span style={{ fontSize: 11, color: '#1DB954', fontFamily: 'monospace' }}>{form.auto_approve_threshold}%</span>
                </div>
                <input type="range" min={50} max={100} value={form.auto_approve_threshold}
                  onChange={e => set('auto_approve_threshold', +e.target.value)}
                  style={{ width: '100%', accentColor: '#1DB954' }}
                />
              </div>

              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 6 }}>
                  <span style={label}>Min score to show</span>
                  <span style={{ fontSize: 11, color: '#F59B23', fontFamily: 'monospace' }}>{form.min_score_to_show}%</span>
                </div>
                <input type="range" min={0} max={85} value={form.min_score_to_show}
                  onChange={e => set('min_score_to_show', +e.target.value)}
                  style={{ width: '100%', accentColor: '#1DB954' }}
                />
              </div>
            </div>
          </div>

          {/* Right — Info */}
          <div>
            <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: '#666', marginBottom: 16, textTransform: 'uppercase' }}>
              About
            </div>
            <div style={{ color: '#666', fontSize: 12, lineHeight: 1.8 }}>
              <p style={{ margin: 0 }}>Spotify Sync Manager GUI</p>
              <p style={{ margin: '8px 0 0' }}>Backend running at <span style={{ color: '#1DB954', fontFamily: 'monospace' }}>localhost:8000</span></p>
              <p style={{ margin: '8px 0 0' }}>
                <a href="http://localhost:8000/docs" target="_blank" rel="noreferrer"
                  style={{ color: '#74B9FF', fontSize: 11 }}>
                  → API Docs (Swagger)
                </a>
              </p>
            </div>
          </div>
        </div>
      </div>

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </div>
  )
}
