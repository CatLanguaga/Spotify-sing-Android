import { useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { API_BASE, api, fetcher } from '../api/client'
import { triggerBrowserDownload } from '../api/download'
import { normalizeLang } from '../api/langLabel'
import type { SpotifyTrack, TrackDownloadResponse, YTCandidate } from '../api/types'
import { useToast } from './toast-context'
import { ManualSearchModal } from './ManualSearchModal'

type State = 'idle' | 'downloading' | 'done' | 'error'

interface Props {
  track: SpotifyTrack
  index: number
  fmt: string
  quality: number
  triggerAt?: number
  queued?: boolean
  onStateChange?: (state: State) => void
}

const OVERRIDE_KEY = 'yt_overrides'

function getOverride(spotifyId: string): string | null {
  try {
    const stored = JSON.parse(localStorage.getItem(OVERRIDE_KEY) || '{}')
    return stored[spotifyId] ?? null
  } catch { return null }
}

function saveOverride(spotifyId: string, url: string) {
  try {
    const stored = JSON.parse(localStorage.getItem(OVERRIDE_KEY) || '{}')
    stored[spotifyId] = url
    localStorage.setItem(OVERRIDE_KEY, JSON.stringify(stored))
  } catch { /* ignore storage errors */ }
}

function fmtDur(ms: number): string {
  if (!ms) return '--:--'
  const total = Math.round(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function TrackRow({ track, index, fmt, quality, triggerAt, queued, onStateChange }: Props) {
  const [state, setState] = useState<State>('idle')
  const [progress, setProgress] = useState(0)
  const [indeterminate, setIndeterminate] = useState(false)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const [reviewOpen, setReviewOpen] = useState(false)
  const [reviewCandidates, setReviewCandidates] = useState<YTCandidate[]>([])
  const [pendingItemId, setPendingItemId] = useState<string | null>(null)
  const { toast } = useToast()
  const esRef = useRef<EventSource | null>(null)
  const triggerTimerRef = useRef<number | null>(null)
  const lastTrigger = useRef<number | undefined>(undefined)
  const lastReportedState = useRef<State | null>(null)

  // SWR dedupes this: all TrackRows share one cached config request
  const { data: cfg } = useSWR<Record<string, unknown>>('/config', fetcher)
  const manualReview = (cfg?.manual_review_enabled as boolean) ?? false

  useEffect(() => {
    if (lastReportedState.current === state) return
    lastReportedState.current = state
    onStateChange?.(state)
  }, [state, onStateChange])

  const startSSE = (itemId: string) => {
    esRef.current?.close()
    const es = new EventSource(`${API_BASE}/queue/${itemId}/progress`)
    esRef.current = es
    let resolved = false

    es.onmessage = (e) => {
      try {
        const data = JSON.parse(e.data) as { percent?: number; state?: string; error?: string }
        if (typeof data.percent === 'number') setProgress(data.percent)
        if (data.state === 'done') {
          resolved = true
          es.close()
          setProgress(100)
          setState('done')
          toast('Descarga lista', 'success')
          triggerBrowserDownload(`${API_BASE}/queue/${itemId}/file`)
        } else if (data.state === 'error') {
          resolved = true
          es.close()
          const msg = data.error === 'geo_restricted'
            ? 'Restringido por región — intenta con VPN'
            : (data.error ?? 'Error')
          setProgress(0)
          setErrMsg(msg)
          setState('error')
          toast(msg, 'error')
        }
      } catch { /* ignore parse errors */ }
    }

    es.onerror = () => {
      if (resolved) return
      es.close()
      setIndeterminate(false)
      setProgress(0)
      setErrMsg('Conexión perdida')
      setState('error')
      toast('Conexión perdida', 'error')
    }
  }

  const confirmWithUrl = async (itemId: string, youtubeUrl: string) => {
    setIndeterminate(false)
    setProgress(5)
    try {
      await api.post('/download/track/confirm', { item_id: itemId, youtube_url: youtubeUrl })
      startSSE(itemId)
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Error al confirmar'
      setProgress(0)
      setErrMsg(message)
      setState('error')
      toast(message, 'error')
    }
  }

  const handleReviewSelect = (url: string) => {
    setReviewOpen(false)
    if (!pendingItemId) return
    saveOverride(track.spotify_id, url)
    setState('downloading')
    setErrMsg(null)
    confirmWithUrl(pendingItemId, url)
  }

  const download = async () => {
    if (state === 'downloading' || state === 'done') return
    setState('downloading')
    setErrMsg(null)
    setProgress(0)
    setIndeterminate(true)
    toast('Track agregado a descarga', 'info')

    // Check localStorage for a known-good override
    const override = getOverride(track.spotify_id)
    if (override) {
      // Skip resolve — go straight to confirm
      try {
        const res = await api.post<TrackDownloadResponse>('/download/track', {
          spotify_id: track.spotify_id, fmt, quality,
        })
        setIndeterminate(false)
        // Confirm with the saved override URL instead of the auto-resolved one
        await confirmWithUrl(res.item_id, override)
        return
      } catch { /* fall through to normal flow */ }
    }

    try {
      // Phase 1: Spotify lookup + YouTube search (~3-7s, indeterminate bar)
      const res = await api.post<TrackDownloadResponse>('/download/track', {
        spotify_id: track.spotify_id,
        fmt,
        quality,
      })

      setIndeterminate(false)

      if (res.needs_review) {
        // Backend flagged low confidence — show manual selection modal
        setPendingItemId(res.item_id)
        setReviewCandidates(res.candidates ?? [])
        setReviewOpen(true)
        setState('idle')  // reset to idle while user picks
        return
      }

      // Phase 2: Real download progress via SSE
      startSSE(res.item_id)

    } catch (err) {
      esRef.current?.close()
      setIndeterminate(false)
      const message = err instanceof Error ? err.message : 'Error'
      setProgress(0)
      setErrMsg(message)
      setState('error')
      toast(message, 'error')
    }
  }

  const openManualSearch = (e: React.MouseEvent) => {
    e.stopPropagation()
    setPendingItemId(null)  // will be set after POST resolves
    setReviewCandidates([])
    setReviewOpen(true)
  }

  // Manual search opened without a pending item_id: we need to trigger a resolve first
  const handleManualSelectNoPending = async (url: string) => {
    setReviewOpen(false)
    setState('downloading')
    setErrMsg(null)
    setProgress(0)
    setIndeterminate(true)
    toast('Resolviendo track…', 'info')
    try {
      const res = await api.post<TrackDownloadResponse>('/download/track', {
        spotify_id: track.spotify_id, fmt, quality,
      })
      setIndeterminate(false)
      saveOverride(track.spotify_id, url)
      await confirmWithUrl(res.item_id, url)
    } catch (err) {
      setIndeterminate(false)
      const message = err instanceof Error ? err.message : 'Error'
      setProgress(0)
      setErrMsg(message)
      setState('error')
      toast(message, 'error')
    }
  }

  useEffect(() => {
    if (triggerAt && triggerAt !== lastTrigger.current) {
      lastTrigger.current = triggerAt
      if (triggerTimerRef.current) window.clearTimeout(triggerTimerRef.current)
      const delay = Math.max(0, triggerAt - Date.now())
      triggerTimerRef.current = window.setTimeout(() => {
        if (state === 'idle' || state === 'error') download()
      }, delay)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerAt])

  useEffect(() => () => {
    if (triggerTimerRef.current) window.clearTimeout(triggerTimerRef.current)
    esRef.current?.close()
  }, [])

  // Waiting in the batch pool (backend runs N at a time): show as pending.
  const showQueued = !!queued && state === 'idle'
  const cls = `track ${state === 'downloading' ? 'downloading' : ''} ${state === 'done' ? 'done' : ''} ${state === 'error' ? 'err' : ''} ${showQueued ? 'queued' : ''}`
  const lang = track.language ? normalizeLang(track.language) : ''

  let btnLabel = '⬇ Descargar'
  if (showQueued)              btnLabel = '⏳ En cola…'
  if (state === 'downloading') btnLabel = '⏳ Descargando…'
  if (state === 'done')        btnLabel = '✓ Descargado'
  if (state === 'error')       btnLabel = '↻ Reintentar'

  return (
    <>
      <div className={cls.trim()}>
        <div className="idx">{index + 1}</div>
        <div className="cover">
          {track.album_art_url && (
            <img
              src={track.album_art_url}
              alt=""
              loading="lazy"
              decoding="async"
            />
          )}
        </div>
        <div className="tx">
          <div className="t">{track.name}</div>
          <div className="a">{track.all_artists || track.artist}</div>
        </div>
        {lang ? <div className="lang">{lang}</div> : <div />}
        <div className="dur">{fmtDur(track.duration_ms)}</div>
        <div className="dl-group">
          <button
            className="dl-btn"
            onClick={download}
            title={errMsg ?? ''}
            aria-label={`${btnLabel} ${track.name}`}
            disabled={state === 'downloading' || showQueued}
          >
            {btnLabel}
          </button>
          {manualReview && state !== 'downloading' && (
            <button
              className="dl-btn-search"
              onClick={openManualSearch}
              title="Buscar fuente manualmente"
              aria-label="Buscar fuente de YouTube manualmente"
            >
              🔍
            </button>
          )}
        </div>
        {state === 'downloading' && (
          <div className="progress-mini">
            {indeterminate
              ? <div className="bar indeterminate" />
              : <div className="bar" style={{ width: `${progress}%` }} />}
          </div>
        )}
        {showQueued && (
          <div className="progress-mini">
            <div className="bar pending" />
          </div>
        )}
        <span className="sr-only" aria-live="polite">
          {track.name}: {btnLabel}
        </span>
      </div>

      {reviewOpen && (
        <ManualSearchModal
          trackName={track.name}
          trackArtist={track.all_artists || track.artist}
          candidates={reviewCandidates}
          onSelect={pendingItemId ? handleReviewSelect : handleManualSelectNoPending}
          onClose={() => setReviewOpen(false)}
        />
      )}
    </>
  )
}
