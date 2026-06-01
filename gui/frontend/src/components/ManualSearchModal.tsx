import { useRef, useState } from 'react'
import { api } from '../api/client'
import type { YTCandidate } from '../api/types'

interface Props {
  trackName: string
  trackArtist: string
  candidates: YTCandidate[]
  onSelect: (url: string) => void
  onClose: () => void
}

const YT_URL_RE = /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=|youtu\.be\/)[\w-]+/

function fmtSec(s: number | null): string {
  if (!s) return '--:--'
  const m = Math.floor(s / 60)
  const sec = s % 60
  return `${m}:${String(sec).padStart(2, '0')}`
}

export function ManualSearchModal({ trackName, trackArtist, candidates, onSelect, onClose }: Props) {
  const [query, setQuery] = useState(`${trackArtist} ${trackName}`.trim())
  const [pasteUrl, setPasteUrl] = useState('')
  const [results, setResults] = useState<YTCandidate[]>(candidates)
  const [searching, setSearching] = useState(false)
  const [searchErr, setSearchErr] = useState<string | null>(null)
  const inputRef = useRef<HTMLInputElement>(null)

  const search = async () => {
    if (!query.trim() || searching) return
    setSearching(true)
    setSearchErr(null)
    try {
      const data = await api.get<YTCandidate[]>(`/youtube/search?q=${encodeURIComponent(query)}&limit=5`)
      setResults(data)
    } catch (e) {
      setSearchErr(e instanceof Error ? e.message : 'Error en búsqueda')
    } finally {
      setSearching(false)
    }
  }

  const pasteValid = YT_URL_RE.test(pasteUrl.trim())

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="manual-search-modal"
        role="dialog"
        aria-modal="true"
        aria-label="Seleccionar fuente de YouTube"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="msm-header">
          <div>
            <div className="kicker">Seleccionar fuente de YouTube</div>
            <h2>{trackName}</h2>
            <p>{trackArtist}</p>
          </div>
          <button className="msm-close" onClick={onClose} aria-label="Cerrar">✕</button>
        </div>

        {/* Search bar */}
        <div className="msm-search-bar">
          <label className="sr-only" htmlFor="youtube-search-query">Buscar en YouTube</label>
          <input
            id="youtube-search-query"
            ref={inputRef}
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search()}
            placeholder="Buscar en YouTube…"
            disabled={searching}
          />
          <button className="btn btn-accent sm" onClick={search} disabled={searching || !query.trim()}>
            {searching ? <span className="spinner" /> : 'Buscar'}
          </button>
        </div>

        {searchErr && <p className="msm-err">{searchErr}</p>}

        {/* Results list */}
        <div className="msm-results">
          {results.length === 0 && !searching && (
            <p className="msm-empty">Sin resultados. Intenta otra búsqueda.</p>
          )}
          {results.map((r, i) => (
            <div key={r.url + i} className="msm-result-row">
              {r.thumbnail
                ? <img className="msm-thumb" src={r.thumbnail} alt="" loading="lazy" />
                : <div className="msm-thumb msm-thumb-placeholder" />}
              <div className="msm-result-info">
                <div className="msm-result-title">{r.title}</div>
                <div className="msm-result-meta">
                  <span>{r.channel ?? '—'}</span>
                  <span>{fmtSec(r.duration)}</span>
                  {r.score != null && (
                    <span className={`msm-score ${r.score >= 65 ? 'ok' : 'warn'}`}>
                      {r.score.toFixed(0)}%
                    </span>
                  )}
                </div>
              </div>
              <button
                className="btn btn-accent sm"
                onClick={() => onSelect(r.url)}
              >
                Usar este
              </button>
            </div>
          ))}
        </div>

        {/* Paste URL */}
        <div className="msm-paste-section">
          <div className="msm-paste-label">O pega una URL de YouTube directamente:</div>
          <div className="msm-paste-row">
            <label className="sr-only" htmlFor="youtube-url-override">URL de YouTube</label>
            <input
              id="youtube-url-override"
              value={pasteUrl}
              onChange={e => setPasteUrl(e.target.value)}
              placeholder="https://www.youtube.com/watch?v=…"
            />
            <button
              className="btn btn-ghost sm"
              disabled={!pasteValid}
              onClick={() => onSelect(pasteUrl.trim())}
            >
              Confirmar
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
