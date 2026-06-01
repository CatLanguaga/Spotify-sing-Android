import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ResolvedPayload } from '../api/types'

const SPOTIFY_RE = /open\.spotify\.com\/(?:intl-[a-z]+\/)?(track|album|playlist)\/([A-Za-z0-9]+)/

interface Props {
  onResolved: (payload: ResolvedPayload, url: string) => void
  onError: (msg: string) => void
  onLoadingChange?: (loading: boolean) => void
}

const EXAMPLES: Array<{ label: string; url: string }> = [
  { label: 'track',    url: 'https://open.spotify.com/track/4PTG3Z6ehGkBFwjybzWkR8' },
  { label: 'álbum',    url: 'https://open.spotify.com/album/4aawyAB9vmqN3uQ7FjRGTy' },
  { label: 'playlist', url: 'https://open.spotify.com/playlist/37i9dQZF1DXcBWIGoYBM5M' },
]

function extractSpotifyUrl(raw: string): string {
  const trimmed = raw.trim()
  const match = trimmed.match(/https?:\/\/open\.spotify\.com\/(?:intl-[a-z]+\/)?(?:track|album|playlist)\/[A-Za-z0-9][^\s]*/)
  return (match?.[0] ?? trimmed).replace(/[),.;]+$/, '')
}

export function HeroSearch({ onResolved, onError, onLoadingChange }: Props) {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const lastSubmittedRef = useRef('')

  const parsed = useMemo(() => {
    const m = extractSpotifyUrl(url).match(SPOTIFY_RE)
    if (!m) return null
    return { kind: m[1] as 'track' | 'album' | 'playlist' }
  }, [url])

  useEffect(() => {
    onLoadingChange?.(loading)
  }, [loading, onLoadingChange])

  const submit = async (source: 'manual' | 'auto' = 'manual') => {
    if (!parsed || loading) return
    const cleanUrl = extractSpotifyUrl(url)
    if (source === 'auto' && cleanUrl === lastSubmittedRef.current) return
    lastSubmittedRef.current = cleanUrl
    setLoading(true)
    try {
      const res = await api.get<ResolvedPayload>(`/spotify/resolve?url=${encodeURIComponent(cleanUrl)}`)
      onResolved(res, cleanUrl)
      setTimeout(() => {
        document.getElementById('results')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
      }, 50)
    } catch (err) {
      lastSubmittedRef.current = ''
      onError(err instanceof Error ? err.message : 'Error al resolver URL')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!parsed || loading) return
    const timeout = window.setTimeout(() => {
      void submit('auto')
    }, 450)
    return () => window.clearTimeout(timeout)
    // submit intentionally reads the latest url/loading state.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [parsed, url])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    void submit('manual')
  }

  const kindLabel = parsed
    ? parsed.kind === 'playlist' ? 'Playlist detectada'
    : parsed.kind === 'album'    ? 'Álbum detectado'
    : 'Track detectado'
    : null

  return (
    <section className="hero">
      <div className="kicker">Descarga directa · sin cuenta · sin cola</div>
      <h1>Pega el link.<br /><span className="em">Descarga la música.</span></h1>
      <p className="sub">Pasa una URL de Spotify y guarda los archivos en tu dispositivo. Track, álbum o playlist completa — sin esperar, sin teléfono, sin instalar nada.</p>

      <form className="input-wrap" onSubmit={handleSubmit}>
        <label className="sr-only" htmlFor="spotify-url">URL de Spotify</label>
        <span className="icon">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M10 14a3.5 3.5 0 0 0 5 0l4-4a3.5 3.5 0 0 0-5-5l-1 1" />
            <path d="M14 10a3.5 3.5 0 0 0-5 0l-4 4a3.5 3.5 0 0 0 5 5l1-1" />
          </svg>
        </span>
        <input
          id="spotify-url"
          value={url}
          onChange={e => setUrl(e.target.value)}
          placeholder="https://open.spotify.com/playlist/..."
          aria-label="URL de Spotify"
          inputMode="url"
          autoCapitalize="none"
          autoCorrect="off"
        />
        {url && (
          <button type="button" className="clear" onClick={() => setUrl('')} aria-label="Limpiar">×</button>
        )}
        <button type="submit" className="btn btn-accent" disabled={!parsed || loading}>
          {loading ? <><span className="spinner" /> Buscando…</> : 'Buscar →'}
        </button>
      </form>

      {kindLabel && <div className="detected">{kindLabel}</div>}

      <div className="examples">
        <span>Pruébalo:</span>
        {EXAMPLES.map(ex => (
          <button key={ex.label} onClick={() => setUrl(ex.url)}>{ex.label}</button>
        ))}
      </div>
    </section>
  )
}
