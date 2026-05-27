import { useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { SpotifyTrack, TrackDownloadResponse } from '../api/types'

type State = 'idle' | 'downloading' | 'done' | 'error'

interface Props {
  track: SpotifyTrack
  index: number
  fmt: string
  quality: number
  triggerAt?: number
  onStateChange?: (state: State) => void
}

const BASE_API = 'http://localhost:8000/api'

function fmtDur(ms: number): string {
  if (!ms) return '--:--'
  const total = Math.round(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

function detectLang(raw: string): string {
  if (!raw) return ''
  const s = raw.toUpperCase()
  if (s.includes('JP') || s.includes('JAPAN')) return 'JP'
  if (s.includes('KR') || s.includes('KOREAN')) return 'KR'
  if (s.includes('ES') || s.includes('SPANISH')) return 'ES'
  if (s.includes('CN') || s.includes('CHINESE')) return 'CN'
  if (s.includes('EN') || s.includes('ENGLISH')) return 'EN'
  return s.slice(0, 2)
}

export function TrackRow({ track, index, fmt, quality, triggerAt, onStateChange }: Props) {
  const [state, setState] = useState<State>('idle')
  const [progress, setProgress] = useState(0)
  const [errMsg, setErrMsg] = useState<string | null>(null)
  const tickRef = useRef<number | null>(null)
  const lastTrigger = useRef<number | undefined>(undefined)

  useEffect(() => {
    onStateChange?.(state)
  }, [state, onStateChange])

  const download = async () => {
    if (state === 'downloading' || state === 'done') return
    setState('downloading')
    setErrMsg(null)
    setProgress(2)

    // simulated progress while server works (no real stream yet)
    if (tickRef.current) window.clearInterval(tickRef.current)
    tickRef.current = window.setInterval(() => {
      setProgress(p => (p < 90 ? p + Math.random() * 8 + 2 : p))
    }, 400)

    try {
      const res = await api.post<TrackDownloadResponse>('/download/track', {
        spotify_id: track.spotify_id,
        fmt,
        quality,
      })
      if (tickRef.current) window.clearInterval(tickRef.current)
      setProgress(100)
      setState('done')
      // browser download
      window.location.href = `${BASE_API}/queue/${res.item_id}/file`
    } catch (err) {
      if (tickRef.current) window.clearInterval(tickRef.current)
      setProgress(0)
      setErrMsg(err instanceof Error ? err.message : 'Error')
      setState('error')
    }
  }

  useEffect(() => {
    if (triggerAt && triggerAt !== lastTrigger.current) {
      lastTrigger.current = triggerAt
      if (state === 'idle' || state === 'error') download()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [triggerAt])

  useEffect(() => () => {
    if (tickRef.current) window.clearInterval(tickRef.current)
  }, [])

  const cls = `track ${state === 'downloading' ? 'downloading' : ''} ${state === 'done' ? 'done' : ''} ${state === 'error' ? 'err' : ''}`
  const lang = detectLang(track.language)
  const coverStyle = track.album_art_url
    ? { backgroundImage: `url(${track.album_art_url})` }
    : { background: 'linear-gradient(135deg,#1DB954,#0F0F11)' }

  let btnLabel = '⬇ Descargar'
  if (state === 'downloading') btnLabel = '⏳ Descargando…'
  if (state === 'done')        btnLabel = '✓ Descargado'
  if (state === 'error')       btnLabel = '↻ Reintentar'

  return (
    <div className={cls.trim()}>
      <div className="idx">{index + 1}</div>
      <div className="cover" style={coverStyle} />
      <div className="tx">
        <div className="t">{track.name}</div>
        <div className="a">{track.all_artists || track.artist}</div>
      </div>
      {lang ? <div className="lang">{lang}</div> : <div />}
      <div className="dur">{fmtDur(track.duration_ms)}</div>
      <button
        className="dl-btn"
        onClick={download}
        title={errMsg ?? ''}
        disabled={state === 'downloading'}
      >
        {btnLabel}
      </button>
      {state === 'downloading' && (
        <div className="progress-mini">
          <div className="bar" style={{ width: `${progress}%` }} />
        </div>
      )}
    </div>
  )
}
