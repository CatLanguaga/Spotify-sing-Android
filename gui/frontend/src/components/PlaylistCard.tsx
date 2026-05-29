import { useEffect, useMemo, useRef, useState } from 'react'
import { api } from '../api/client'
import type { ResolvedPayload } from '../api/types'
import { TrackRow } from './TrackRow'
import { TrackRangeSlider, type TrackRange } from './TrackRangeSlider'

interface Props {
  payload: ResolvedPayload
  sourceUrl: string
}

const MAX_TRACKS_PER_REQUEST = 50
const SPOTIFY_RE = /open\.spotify\.com\/(?:intl-[a-z]+\/)?(track|album|playlist)\/([A-Za-z0-9]+)/

function totalDuration(payload: ResolvedPayload): string {
  const total = payload.tracks.reduce((acc, t) => acc + (t.duration_ms || 0), 0)
  const min = Math.round(total / 60000)
  if (min < 60) return `${min} min`
  const h = Math.floor(min / 60)
  return `${h} h ${min % 60} min`
}

function normalizeLang(raw: string): string {
  if (!raw) return 'OTHER'
  const s = raw.toUpperCase()
  if (s.includes('JP') || s.includes('JAPAN')) return 'JP'
  if (s.includes('KR') || s.includes('KOREAN')) return 'KR'
  if (s.includes('ES') || s.includes('SPANISH')) return 'ES'
  if (s.includes('CN') || s.includes('CHINESE')) return 'CN'
  if (s.includes('RU') || s.includes('RUSSIAN')) return 'RU'
  if (s.includes('EN') || s.includes('ENGLISH')) return 'EN'
  return 'OTHER'
}

function payloadRange(payload: ResolvedPayload): TrackRange {
  const from = Math.max(1, payload.offset + 1)
  const count = payload.returned || payload.tracks.length
  return { from, to: Math.max(from, payload.offset + count) }
}

function requestedRange(payload: ResolvedPayload): TrackRange {
  const from = Math.max(1, payload.offset + 1)
  const width = payload.total > MAX_TRACKS_PER_REQUEST
    ? MAX_TRACKS_PER_REQUEST
    : Math.max(1, payload.returned || payload.tracks.length)
  return { from, to: Math.min(payload.total || from, from + width - 1) }
}

function sameRange(a: TrackRange, b: TrackRange): boolean {
  return a.from === b.from && a.to === b.to
}

function clampRange(range: TrackRange, total: number): TrackRange {
  const from = Math.min(total, Math.max(1, Math.round(range.from)))
  const maxTo = Math.min(total, from + MAX_TRACKS_PER_REQUEST - 1)
  const to = Math.min(maxTo, Math.max(from, Math.round(range.to)))
  return { from, to }
}

function parseRange(raw: string | null, total: number): TrackRange | null {
  const match = raw?.match(/^(\d+)-(\d+)$/)
  if (!match) return null
  return clampRange({ from: Number(match[1]), to: Number(match[2]) }, total)
}

function parseSpotifyId(url: string): string | null {
  return url.match(SPOTIFY_RE)?.[2] ?? null
}

function localStorageKey(url: string): string | null {
  const id = parseSpotifyId(url)
  return id ? `spotify-range:${id}` : null
}

function initialRange(payload: ResolvedPayload, sourceUrl: string): TrackRange {
  if (payload.kind !== 'playlist' || payload.total <= MAX_TRACKS_PER_REQUEST) {
    return payloadRange(payload)
  }

  const urlRange = parseRange(new URLSearchParams(window.location.search).get('range'), payload.total)
  if (urlRange) return urlRange

  const key = localStorageKey(sourceUrl)
  if (key) {
    const storedRange = parseRange(window.localStorage.getItem(key), payload.total)
    if (storedRange) return storedRange
  }

  return payloadRange(payload)
}

export function PlaylistCard({ payload, sourceUrl }: Props) {
  const [activePayload, setActivePayload] = useState(payload)
  const [fmt, setFmt] = useState('mp3')
  const [quality, setQuality] = useState(320)
  const [filter, setFilter] = useState('')
  const [langFilter, setLangFilter] = useState('ALL')
  const [trigger, setTrigger] = useState<number>(0)
  const [doneIds, setDoneIds] = useState<Set<string>>(() => new Set())
  const [range, setRange] = useState<TrackRange>(() => initialRange(payload, sourceUrl))
  const [loadedRange, setLoadedRange] = useState<TrackRange>(() => requestedRange(payload))
  const [rangeLoading, setRangeLoading] = useState(false)
  const [rangeError, setRangeError] = useState<string | null>(null)
  const requestSeq = useRef(0)

  useEffect(() => {
    setActivePayload(payload)
    setRange(initialRange(payload, sourceUrl))
    setLoadedRange(requestedRange(payload))
    setDoneIds(new Set())
    setRangeError(null)
  }, [payload, sourceUrl])

  const shouldShowRange = activePayload.kind !== 'track' && activePayload.total > MAX_TRACKS_PER_REQUEST

  useEffect(() => {
    if (!shouldShowRange) {
      const params = new URLSearchParams(window.location.search)
      if (params.has('range')) {
        params.delete('range')
        const query = params.toString()
        window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
      }
      return
    }

    const nextRange = clampRange(range, activePayload.total)
    const rangeValue = `${nextRange.from}-${nextRange.to}`
    const key = localStorageKey(sourceUrl)

    if (!sameRange(range, nextRange)) {
      setRange(nextRange)
      return
    }

    if (key) window.localStorage.setItem(key, rangeValue)

    const params = new URLSearchParams(window.location.search)
    if (params.get('range') !== rangeValue) {
      params.set('range', rangeValue)
      window.history.replaceState(null, '', `${window.location.pathname}?${params}`)
    }

    if (sameRange(loadedRange, nextRange)) return

    const seq = ++requestSeq.current
    const timeout = window.setTimeout(async () => {
      setRangeLoading(true)
      setRangeError(null)
      try {
        const limit = nextRange.to - nextRange.from + 1
        const nextPayload = await api.get<ResolvedPayload>(
          `/spotify/resolve?url=${encodeURIComponent(sourceUrl)}&offset=${nextRange.from - 1}&limit=${limit}`,
        )
        if (seq !== requestSeq.current) return
        setActivePayload(nextPayload)
        setLoadedRange(nextRange)
        setDoneIds(new Set())
      } catch (err) {
        if (seq !== requestSeq.current) return
        setRangeError(err instanceof Error ? err.message : 'No se pudo cargar el rango')
      } finally {
        if (seq === requestSeq.current) setRangeLoading(false)
      }
    }, 300)

    return () => window.clearTimeout(timeout)
  }, [activePayload, loadedRange, range, shouldShowRange, sourceUrl])

  const langOptions = useMemo(() => {
    const counts = activePayload.tracks.reduce<Record<string, number>>((acc, track) => {
      const lang = normalizeLang(track.language)
      acc[lang] = (acc[lang] ?? 0) + 1
      return acc
    }, {})

    return Object.entries(counts)
      .sort(([a], [b]) => a.localeCompare(b))
      .map(([lang, count]) => ({ lang, count }))
  }, [activePayload.tracks])

  const tracks = useMemo(() => {
    const f = filter.toLowerCase()
    return activePayload.tracks.filter(t =>
      (langFilter === 'ALL' || normalizeLang(t.language) === langFilter) &&
      (
        !f.trim() ||
        t.name.toLowerCase().includes(f) ||
        (t.all_artists || t.artist).toLowerCase().includes(f)
      )
    )
  }, [activePayload.tracks, filter, langFilter])

  const kindLabel = activePayload.kind === 'playlist' ? 'Spotify · Playlist'
                  : activePayload.kind === 'album'    ? 'Spotify · Álbum'
                  : 'Spotify · Track'

  const coverUrl = activePayload.info.image_url || activePayload.tracks[0]?.album_art_url
  const coverStyle = coverUrl
    ? { backgroundImage: `url(${coverUrl})` }
    : undefined

  const downloadAll = () => {
    setDoneIds(new Set())
    setTrigger(Date.now())
  }

  const doneCount = doneIds.size

  return (
    <section className="results" id="results">
      <div className="pl-card">
        <div className="pl-head">
          <div className="pl-cover" style={coverStyle} />
          <div className="pl-info">
            <div className="kicker">{kindLabel}{activePayload.info.owner ? ` · ${activePayload.info.owner}` : ''}</div>
            <h2>{activePayload.info.name || 'Sin nombre'}</h2>
            <div className="stats">
              <strong>{activePayload.total} tracks</strong> · <strong>{totalDuration(activePayload)}</strong>
              {activePayload.returned < activePayload.total && (
                <> · mostrando {activePayload.offset + 1}-{activePayload.offset + activePayload.returned}</>
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
            <button className="btn btn-accent" onClick={downloadAll} disabled={rangeLoading}>
              ⬇ Descargar todo ({tracks.length})
            </button>
          </div>
        </div>

        {shouldShowRange && (
          <TrackRangeSlider
            total={activePayload.total}
            range={range}
            loading={rangeLoading}
            onChange={setRange}
          />
        )}

        {rangeError && <div className="range-error">{rangeError}</div>}

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
          <div className="lang-filter" aria-label="Filtrar por idioma">
            <button
              className={langFilter === 'ALL' ? 'active' : ''}
              onClick={() => setLangFilter('ALL')}
              type="button"
            >
              Todos
            </button>
            {langOptions.map(({ lang, count }) => (
              <button
                key={lang}
                className={langFilter === lang ? 'active' : ''}
                onClick={() => setLangFilter(lang)}
                type="button"
              >
                {lang} <span>{count}</span>
              </button>
            ))}
          </div>
          <div className="count">{tracks.length} canciones</div>
        </div>

        <div className="tracks">
          {rangeLoading && (
            <div className="track-skeletons" aria-hidden="true">
              {Array.from({ length: Math.min(6, tracks.length || 6) }).map((_, i) => (
                <div className="track-skeleton" key={i}>
                  <span className="sk idx-sk" />
                  <span className="sk cover-sk" />
                  <span className="sk title-sk" />
                  <span className="sk badge-sk" />
                  <span className="sk dur-sk" />
                  <span className="sk btn-sk" />
                </div>
              ))}
            </div>
          )}
          {tracks.map((t, i) => (
            <TrackRow
              key={t.spotify_id || `${i}-${t.name}`}
              track={t}
              index={activePayload.offset + i}
              fmt={fmt}
              quality={quality}
              triggerAt={trigger ? trigger + i * 180 : undefined}
              onStateChange={s => {
                if (s === 'done') {
                  const id = t.spotify_id || `${activePayload.offset + i}-${t.name}`
                  setDoneIds(prev => {
                    if (prev.has(id)) return prev
                    const next = new Set(prev)
                    next.add(id)
                    return next
                  })
                }
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
