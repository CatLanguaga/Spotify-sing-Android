import { useMemo, useState } from 'react'
import type { ResolvedPayload } from '../api/types'
import { TrackRow } from './TrackRow'

interface Props {
  payload: ResolvedPayload
}

function totalDuration(payload: ResolvedPayload): string {
  const total = payload.tracks.reduce((acc, t) => acc + (t.duration_ms || 0), 0)
  const min = Math.round(total / 60000)
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  return `${h} h ${min % 60} min`
}

export function PlaylistCard({ payload }: Props) {
  const [fmt, setFmt] = useState('mp3')
  const [quality, setQuality] = useState(320)
  const [filter, setFilter] = useState('')
  const [trigger, setTrigger] = useState<number>(0)
  const [doneCount, setDoneCount] = useState(0)

  const tracks = useMemo(() => {
    if (!filter.trim()) return payload.tracks
    const f = filter.toLowerCase()
    return payload.tracks.filter(t =>
      t.name.toLowerCase().includes(f) ||
      (t.all_artists || t.artist).toLowerCase().includes(f)
    )
  }, [payload.tracks, filter])

  const kindLabel = payload.kind === 'playlist' ? 'Spotify · Playlist'
                  : payload.kind === 'album'    ? 'Spotify · Álbum'
                  : 'Spotify · Track'

  const coverUrl = payload.info.image_url || payload.tracks[0]?.album_art_url
  const coverStyle = coverUrl
    ? { backgroundImage: `url(${coverUrl})` }
    : undefined

  const downloadAll = () => {
    setDoneCount(0)
    setTrigger(Date.now())
  }

  return (
    <section className="results" id="results">
      <div className="pl-card">
        <div className="pl-head">
          <div className="pl-cover" style={coverStyle} />
          <div className="pl-info">
            <div className="kicker">{kindLabel}{payload.info.owner ? ` · ${payload.info.owner}` : ''}</div>
            <h2>{payload.info.name || 'Sin nombre'}</h2>
            <div className="stats">
              <strong>{payload.total} tracks</strong> · <strong>{totalDuration(payload)}</strong>
              {payload.returned < payload.total && (
                <> · mostrando {payload.returned}</>
              )}
            </div>
          </div>
          <div className="pl-actions">
            <div className="options">
              <select value={fmt} onChange={e => setFmt(e.target.value)} aria-label="Formato">
                <option value="mp3">mp3</option>
                <option value="m4a">m4a</option>
                <option value="opus">opus</option>
              </select>
              <select value={quality} onChange={e => setQuality(Number(e.target.value))} aria-label="Calidad">
                <option value={320}>320 kbps</option>
                <option value={192}>192 kbps</option>
                <option value={128}>128 kbps</option>
              </select>
            </div>
            <button className="btn btn-accent" onClick={downloadAll}>
              ⬇ Descargar todo ({tracks.length})
            </button>
          </div>
        </div>

        <div className="pl-toolbar">
          <div className="search">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3-3" />
            </svg>
            <input
              placeholder="Filtrar título o artista"
              value={filter}
              onChange={e => setFilter(e.target.value)}
            />
          </div>
          <div className="count">{tracks.length} canciones</div>
        </div>

        <div className="tracks">
          {tracks.map((t, i) => (
            <TrackRow
              key={t.spotify_id || `${i}-${t.name}`}
              track={t}
              index={i}
              fmt={fmt}
              quality={quality}
              triggerAt={trigger ? trigger + i * 180 : undefined}
              onStateChange={s => {
                if (s === 'done') setDoneCount(c => c + 1)
              }}
            />
          ))}
        </div>

        <div className="pl-foot">
          <div className="msg">
            <strong>{doneCount}</strong> de {tracks.length} descargados · Las descargas se procesan en paralelo.
          </div>
          <button className="btn btn-ghost sm" disabled title="Próximamente">Descargar como .ZIP</button>
        </div>
      </div>
    </section>
  )
}
