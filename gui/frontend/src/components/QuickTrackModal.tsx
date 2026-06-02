import { useEffect, useRef, useState } from 'react'
import { API_BASE, api } from '../api/client'
import { triggerBrowserDownload } from '../api/download'
import type { SpotifyTrack, TrackDownloadResponse } from '../api/types'
import { useToast } from './toast-context'
import { usePreferences } from '../preferences'

interface Props {
  track: SpotifyTrack
  onClose: () => void
}

function fmtDur(ms: number): string {
  if (!ms) return '--:--'
  const total = Math.round(ms / 1000)
  const m = Math.floor(total / 60)
  const s = total % 60
  return `${m}:${String(s).padStart(2, '0')}`
}

export function QuickTrackModal({ track, onClose }: Props) {
  const [fmt, setFmt] = useState('mp3')
  const [quality, setQuality] = useState(320)
  const [loading, setLoading] = useState(false)
  const { toast } = useToast()
  const { t } = usePreferences()
  const esRef = useRef<EventSource | null>(null)

  // Close any open SSE stream when the modal unmounts.
  useEffect(() => () => { esRef.current?.close() }, [])

  const downloadNow = async () => {
    if (loading) return
    setLoading(true)
    toast(t('trToastAdded'), 'info')
    try {
      // /download/track is non-blocking: returns item_id immediately and runs
      // the actual download in a background thread. We must wait for the SSE
      // 'done' event before hitting /file, otherwise local_path isn't set yet
      // and the server returns 404 "File not found — download it first.".
      const res = await api.post<TrackDownloadResponse>('/download/track', {
        spotify_id: track.spotify_id,
        fmt,
        quality,
      })

      if (res.needs_review) {
        // Low-confidence match needs manual selection — not available in this
        // modal. Send the user to the track table flow.
        toast(t('qmToastLowConf'), 'error')
        setLoading(false)
        return
      }

      const es = new EventSource(`${API_BASE}/queue/${res.item_id}/progress`)
      esRef.current = es

      es.onmessage = (e) => {
        try {
          const data = JSON.parse(e.data) as { state?: string; error?: string }
          if (data.state === 'done') {
            es.close()
            toast(t('trToastReady'), 'success')
            triggerBrowserDownload(`${API_BASE}/queue/${res.item_id}/file`)
            onClose()
          } else if (data.state === 'error') {
            es.close()
            const msg = data.error === 'geo_restricted'
              ? t('trGeoRestricted')
              : (data.error ?? t('qmToastFailed'))
            toast(msg, 'error')
            setLoading(false)
          }
        } catch { /* ignore parse errors */ }
      }

      es.onerror = () => {
        es.close()
        toast(t('trToastConnLost'), 'error')
        setLoading(false)
      }
    } catch (err) {
      toast(err instanceof Error ? err.message : t('qmToastFailed'), 'error')
      setLoading(false)
    }
  }

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="quick-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="quick-track-title"
        onMouseDown={e => e.stopPropagation()}
      >
        <div className="quick-cover">
          {track.album_art_url && (
            <img
              src={track.album_art_url}
              alt=""
              loading="lazy"
              decoding="async"
            />
          )}
        </div>
        <div className="quick-body">
          <div className="kicker">{t('qmTrackDetected')}</div>
          <h2 id="quick-track-title">{track.name}</h2>
          <p>{track.all_artists || track.artist}</p>
          <div className="quick-meta">
            <span>{track.album || t('qmSingle')}</span>
            <span>{fmtDur(track.duration_ms)}</span>
          </div>
          <div className="quick-options">
            <label>
              {t('qmFormat')}
              <select value={fmt} onChange={e => setFmt(e.target.value)} disabled={loading}>
                <option value="mp3">mp3</option>
                <option value="m4a">m4a</option>
                <option value="opus">opus</option>
              </select>
            </label>
            <label>
              {t('qmQuality')}
              <select value={quality} onChange={e => setQuality(Number(e.target.value))} disabled={loading}>
                <option value={320}>320 kbps</option>
                <option value={192}>192 kbps</option>
                <option value={128}>128 kbps</option>
              </select>
            </label>
          </div>
          <div className="quick-actions">
            <button className="btn btn-ghost" type="button" onClick={onClose} disabled={loading}>
              {t('qmCancel')}
            </button>
            <button className="btn btn-accent" type="button" onClick={downloadNow} disabled={loading}>
              {loading ? <><span className="spinner" /> {t('qmDownloading')}</> : t('qmDownloadNow')}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
