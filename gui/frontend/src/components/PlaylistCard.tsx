import { useEffect, useMemo, useRef, useState } from 'react'
import useSWR from 'swr'
import { API_BASE, api, fetcher } from '../api/client'
import type { ResolvedPayload } from '../api/types'
import { triggerBrowserDownload } from '../api/download'
import { normalizeLang } from '../api/langLabel'
import { TrackRow } from './TrackRow'
import { TrackPaginator } from './TrackPaginator'
import { useToast } from './toast-context'
import { usePreferences } from '../preferences'

interface Props {
  payload: ResolvedPayload
  sourceUrl: string
}

const MAX_TRACKS_PER_REQUEST = 50
const MAX_RETRIES = 2
const SPOTIFY_RE = /open\.spotify\.com\/(?:intl-[a-z]+\/)?(track|album|playlist)\/([A-Za-z0-9]+)/

function totalDuration(
  payload: ResolvedPayload,
  mins: (m: number) => string,
  hmins: (h: number, m: number) => string,
): string {
  const total = payload.tracks.reduce((acc, t) => acc + (t.duration_ms || 0), 0)
  const min = Math.round(total / 60000)
  if (min < 60) return mins(min)
  const h = Math.floor(min / 60)
  return hmins(h, min % 60)
}

function parseSpotifyId(url: string): string | null {
  return url.match(SPOTIFY_RE)?.[2] ?? null
}

function localStorageKey(url: string): string | null {
  const id = parseSpotifyId(url)
  return id ? `spotify-page:${id}` : null
}

function payloadPage(payload: ResolvedPayload): number {
  return Math.floor(payload.offset / MAX_TRACKS_PER_REQUEST) + 1
}

function initialPage(payload: ResolvedPayload, sourceUrl: string): number {
  if (payload.kind !== 'playlist' || payload.total <= MAX_TRACKS_PER_REQUEST) return 1

  const urlPage = new URLSearchParams(window.location.search).get('page')
  if (urlPage && /^\d+$/.test(urlPage)) {
    const p = Number(urlPage)
    if (p >= 1) return p
  }

  const key = localStorageKey(sourceUrl)
  if (key) {
    const stored = window.localStorage.getItem(key)
    if (stored && /^\d+$/.test(stored)) {
      const p = Number(stored)
      if (p >= 1) return p
    }
  }

  return payloadPage(payload)
}

function calcTotalPages(total: number): number {
  return Math.max(1, Math.ceil(total / MAX_TRACKS_PER_REQUEST))
}

type ZipState = 'idle' | 'working' | 'done' | 'error'

export function PlaylistCard({ payload, sourceUrl }: Props) {
  const { toast } = useToast()
  const { t } = usePreferences()
  const { data: publicConfig } = useSWR<Record<string, unknown>>('/config/public', fetcher)
  const [activePayload, setActivePayload] = useState(payload)
  const [fmt, setFmt] = useState('mp3')
  const [quality, setQuality] = useState(320)
  const [filter, setFilter] = useState('')
  const [langFilter, setLangFilter] = useState('ALL')
  // Per-track trigger map: bumping a key's value tells that TrackRow to start.
  const [triggers, setTriggers] = useState<Record<string, number>>({})
  const [doneIds, setDoneIds] = useState<Set<string>>(() => new Set())
  const [errorIds, setErrorIds] = useState<Set<string>>(() => new Set())
  const [batchRunning, setBatchRunning] = useState(false)
  const [zipState, setZipState] = useState<ZipState>('idle')
  const [zipProgress, setZipProgress] = useState<{ done: number; total: number }>({ done: 0, total: 0 })
  const [currentPage, setCurrentPage] = useState<number>(() => initialPage(payload, sourceUrl))
  const [loadedPage, setLoadedPage] = useState<number>(() => payloadPage(payload))
  const [pageLoading, setPageLoading] = useState(false)
  const [pageError, setPageError] = useState<string | null>(null)
  const requestSeq = useRef(0)
  const batchConcurrency = Math.max(1, Math.min(5, Number(publicConfig?.max_concurrent_downloads ?? 3)))

  // Batch pool bookkeeping — refs to avoid stale closures across async callbacks.
  const pendingRef = useRef<string[]>([])
  const inFlightRef = useRef(0)
  const retryRef = useRef<Record<string, number>>({})
  const batchKeysRef = useRef<Set<string>>(new Set())
  const doneCountRef = useRef(0)
  const errCountRef = useRef(0)
  const seqRef = useRef(0)
  const zipEsRef = useRef<EventSource | null>(null)

  useEffect(() => {
    setActivePayload(payload)
    setCurrentPage(initialPage(payload, sourceUrl))
    setLoadedPage(payloadPage(payload))
    setDoneIds(new Set())
    setErrorIds(new Set())
    setBatchRunning(false)
    batchKeysRef.current = new Set()
    pendingRef.current = []
    inFlightRef.current = 0
    setPageError(null)
  }, [payload, sourceUrl])

  useEffect(() => () => { zipEsRef.current?.close() }, [])

  const totalPages = calcTotalPages(activePayload.total)
  const shouldShowPaginator = activePayload.kind !== 'track' && activePayload.total > MAX_TRACKS_PER_REQUEST

  useEffect(() => {
    if (!shouldShowPaginator) {
      const params = new URLSearchParams(window.location.search)
      if (params.has('page')) {
        params.delete('page')
        const query = params.toString()
        window.history.replaceState(null, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
      }
      return
    }

    const clampedPage = Math.min(totalPages, Math.max(1, currentPage))
    if (clampedPage !== currentPage) {
      setCurrentPage(clampedPage)
      return
    }

    const key = localStorageKey(sourceUrl)
    if (key) window.localStorage.setItem(key, String(clampedPage))

    const params = new URLSearchParams(window.location.search)
    if (params.get('page') !== String(clampedPage)) {
      params.set('page', String(clampedPage))
      window.history.replaceState(null, '', `${window.location.pathname}?${params}`)
    }

    if (loadedPage === clampedPage) return

    const seq = ++requestSeq.current
    const timeout = window.setTimeout(async () => {
      setPageLoading(true)
      setPageError(null)
      try {
        const offset = (clampedPage - 1) * MAX_TRACKS_PER_REQUEST
        const nextPayload = await api.get<ResolvedPayload>(
          `/spotify/resolve?url=${encodeURIComponent(sourceUrl)}&offset=${offset}&limit=${MAX_TRACKS_PER_REQUEST}`,
        )
        if (seq !== requestSeq.current) return
        setActivePayload(nextPayload)
        setLoadedPage(clampedPage)
        setDoneIds(new Set())
        setErrorIds(new Set())
      } catch (err) {
        if (seq !== requestSeq.current) return
        setPageError(err instanceof Error ? err.message : t('plPageError'))
      } finally {
        if (seq === requestSeq.current) setPageLoading(false)
      }
    }, 200)

    return () => window.clearTimeout(timeout)
  }, [activePayload.total, currentPage, loadedPage, shouldShowPaginator, sourceUrl, totalPages])

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

  const trackKey = (track: { spotify_id?: string; name: string }, absIndex: number): string =>
    track.spotify_id || `${absIndex}-${track.name}`

  const kindLabel = activePayload.kind === 'playlist' ? t('plKindPlaylist')
                  : activePayload.kind === 'album'    ? t('plKindAlbum')
                  : t('plKindTrack')

  const coverUrl = activePayload.info.image_url || activePayload.tracks[0]?.album_art_url

  // ─── batch pool ────────────────────────────────────────────────────────────

  const dispatchNext = () => {
    while (inFlightRef.current < batchConcurrency && pendingRef.current.length > 0) {
      const key = pendingRef.current.shift()!
      inFlightRef.current++
      const value = ++seqRef.current
      setTriggers(prev => ({ ...prev, [key]: value }))
    }
    if (inFlightRef.current === 0 && pendingRef.current.length === 0 && batchKeysRef.current.size > 0) {
      // Batch finished.
      const done = doneCountRef.current
      const errs = errCountRef.current
      setBatchRunning(false)
      batchKeysRef.current = new Set()
      toast(
        errs > 0 ? t('plToastDownloadedWithErrors')(done, errs) : t('plToastDownloaded')(done),
        errs > 0 ? 'info' : 'success',
      )
    }
  }

  const startKeys = (keys: string[]) => {
    if (!keys.length) return
    pendingRef.current = [...keys]
    inFlightRef.current = 0
    retryRef.current = {}
    batchKeysRef.current = new Set(keys)
    doneCountRef.current = 0
    errCountRef.current = 0
    setDoneIds(new Set())
    setErrorIds(new Set())
    setBatchRunning(true)
    dispatchNext()
  }

  const downloadAll = () => {
    const keys = tracks.map((t, i) => trackKey(t, activePayload.offset + i))
    startKeys(keys)
  }

  useEffect(() => {
    const onDownloadAll = () => {
      if (!batchRunning && tracks.length) downloadAll()
    }
    window.addEventListener('mp3vine-download-all', onDownloadAll)
    return () => window.removeEventListener('mp3vine-download-all', onDownloadAll)
    // downloadAll intentionally reads current visible tracks.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [batchRunning, tracks])

  const retryFailed = () => {
    const keys = [...errorIds]
    if (!keys.length) return
    errCountRef.current = Math.max(0, errCountRef.current - keys.length)
    setErrorIds(new Set())
    startKeys(keys)
  }

  const handleRowState = (key: string, state: 'done' | 'error') => {
    const inBatch = batchKeysRef.current.has(key)

    if (state === 'done') {
      setDoneIds(prev => {
        if (prev.has(key)) return prev
        const next = new Set(prev)
        next.add(key)
        return next
      })
      if (inBatch) {
        doneCountRef.current++
        inFlightRef.current = Math.max(0, inFlightRef.current - 1)
        dispatchNext()
      }
      return
    }

    // state === 'error'
    if (!inBatch) return
    inFlightRef.current = Math.max(0, inFlightRef.current - 1)
    const attempts = retryRef.current[key] ?? 0
    if (attempts < MAX_RETRIES) {
      retryRef.current[key] = attempts + 1
      pendingRef.current.push(key)
    } else {
      errCountRef.current++
      setErrorIds(prev => {
        const next = new Set(prev)
        next.add(key)
        return next
      })
    }
    dispatchNext()
  }

  // ─── ZIP batch ───────────────────────────────────────────────────────────────

  const downloadZip = async () => {
    if (zipState === 'working') return
    const ids = tracks.map(t => t.spotify_id).filter(Boolean) as string[]
    if (!ids.length) {
      toast(t('plToastZipNoIds'), 'error')
      return
    }
    setZipState('working')
    setZipProgress({ done: 0, total: ids.length })
    try {
      const { job_id } = await api.post<{ job_id: string; total: number }>(
        '/download/batch', { spotify_ids: ids, fmt, quality },
      )
      zipEsRef.current?.close()
      const es = new EventSource(`${API_BASE}/download/batch/${job_id}/progress`)
      zipEsRef.current = es
      es.onmessage = (e) => {
        try {
          const d = JSON.parse(e.data) as { state: string; done: number; total: number; error?: string }
          setZipProgress({ done: d.done, total: d.total })
          if (d.state === 'done') {
            es.close()
            setZipState('done')
            toast(t('plToastZipReady'), 'success')
            triggerBrowserDownload(`${API_BASE}/download/batch/${job_id}/zip`)
            setTimeout(() => setZipState('idle'), 1500)
          } else if (d.state === 'error') {
            es.close()
            setZipState('error')
            toast(d.error || t('plToastZipFailed'), 'error')
          }
        } catch { /* ignore parse errors */ }
      }
      es.onerror = () => {
        es.close()
        setZipState('error')
        toast(t('plToastZipConnLost'), 'error')
      }
    } catch (err) {
      setZipState('error')
      toast(err instanceof Error ? err.message : t('plToastZipFailed'), 'error')
    }
  }

  const doneCount = doneIds.size
  const errorCount = errorIds.size
  const zipLabel = zipState === 'working'
    ? t('plZipGenerating')(zipProgress.done, zipProgress.total)
    : zipState === 'done' ? t('plZipReady')
    : t('plZipDownload')

  return (
    <section className="results" id="results">
      <div className="pl-card">
        <div className="pl-head">
          <div className="pl-cover">
            {coverUrl && (
              <img
                src={coverUrl}
                alt=""
                loading="lazy"
                decoding="async"
              />
            )}
          </div>
          <div className="pl-info">
            <div className="kicker">{kindLabel}{activePayload.info.owner ? ` · ${activePayload.info.owner}` : ''}</div>
            <h2>{activePayload.info.name || t('plUntitled')}</h2>
            <div className="stats">
              <strong>{t('plTracksCount')(activePayload.total)}</strong> · <strong>{totalDuration(activePayload, t('plMinutes'), t('plHourMinutes'))}</strong>
              {activePayload.returned < activePayload.total && (
                <> · {t('plShowing')(activePayload.offset + 1, activePayload.offset + activePayload.returned)}</>
              )}
            </div>
          </div>
          <div className="pl-actions">
            <div className="options">
              <select value={fmt} onChange={e => setFmt(e.target.value)} aria-label={t('plFormat')}>
                <option value="mp3">mp3</option>
                <option value="m4a">m4a</option>
                <option value="opus">opus</option>
              </select>
              <select value={quality} onChange={e => setQuality(Number(e.target.value))} aria-label={t('plQuality')}>
                <option value={320}>320 kbps</option>
                <option value={192}>192 kbps</option>
                <option value={128}>128 kbps</option>
              </select>
            </div>
            <button className="btn btn-accent" onClick={downloadAll} disabled={pageLoading || batchRunning}>
              {batchRunning ? t('plDownloading')(doneCount, tracks.length) : t('plDownloadAll')(tracks.length)}
            </button>
            <button
              className="btn btn-ghost"
              onClick={downloadZip}
              disabled={pageLoading || zipState === 'working'}
            >
              {zipLabel}
            </button>
          </div>
        </div>

        {shouldShowPaginator && (
          <TrackPaginator
            currentPage={currentPage}
            totalPages={totalPages}
            total={activePayload.total}
            loading={pageLoading}
            onPageChange={setCurrentPage}
          />
        )}

        {pageError && <div className="page-error">{pageError}</div>}

        <div className="pl-toolbar">
          <div className="search">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="7" />
              <path d="m20 20-3-3" />
            </svg>
            <input
              placeholder={t('plFilterInput')}
              value={filter}
              onChange={e => setFilter(e.target.value)}
            />
          </div>
          <div className="lang-filter" aria-label={t('plLangFilter')}>
            <button
              className={langFilter === 'ALL' ? 'active' : ''}
              onClick={() => setLangFilter('ALL')}
              type="button"
            >
              {t('plLangAll')}
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
          <div className="count">{t('plTracksShort')(tracks.length)}</div>
        </div>

        <div className="tracks">
          {pageLoading && (
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
          {tracks.map((t, i) => {
            const key = trackKey(t, activePayload.offset + i)
            return (
              <TrackRow
                key={t.spotify_id || `${i}-${t.name}`}
                track={t}
                index={activePayload.offset + i}
                fmt={fmt}
                quality={quality}
                triggerAt={triggers[key]}
                queued={batchRunning && batchKeysRef.current.has(key) && triggers[key] === undefined}
                onStateChange={s => {
                  if (s === 'done' || s === 'error') handleRowState(key, s)
                }}
              />
            )
          })}
        </div>

        <div className="pl-foot">
          <div className="msg">
            <strong>{doneCount}</strong> {t('plOfDownloaded')(doneCount, tracks.length)}
            {errorCount > 0 && <> · <strong className="foot-err">{t('plFailed')(errorCount)}</strong></>}
            {' '}· {t('plParallel')}
          </div>
          {errorCount > 0 && !batchRunning && (
            <button className="btn btn-ghost sm" onClick={retryFailed}>{t('plRetryFailed')(errorCount)}</button>
          )}
        </div>
      </div>
    </section>
  )
}
