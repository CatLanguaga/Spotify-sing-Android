import { useState } from 'react'
import { API_BASE, api } from '../api/client'
import type { SpotifyTrack, TrackDownloadResponse } from '../api/types'
import { useToast } from './toast-context'

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

  const coverStyle = track.album_art_url
    ? { backgroundImage: `url(${track.album_art_url})` }
    : { background: 'linear-gradient(135deg,#1DB954,#0F0F11)' }

  const downloadNow = async () => {
    if (loading) return
    setLoading(true)
    toast('Track agregado a descarga', 'info')
    try {
      const res = await api.post<TrackDownloadResponse>('/download/track', {
        spotify_id: track.spotify_id,
        fmt,
        quality,
      })
      toast('Descarga lista', 'success')
      window.location.href = `${API_BASE}/queue/${res.item_id}/file`
      onClose()
    } catch (err) {
      toast(err instanceof Error ? err.message : 'Error al descargar', 'error')
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
        <div className="quick-cover" style={coverStyle} />
        <div className="quick-body">
          <div className="kicker">Track detectado</div>
          <h2 id="quick-track-title">{track.name}</h2>
          <p>{track.all_artists || track.artist}</p>
          <div className="quick-meta">
            <span>{track.album || 'Single'}</span>
            <span>{fmtDur(track.duration_ms)}</span>
          </div>
          <div className="quick-options">
            <label>
              Formato
              <select value={fmt} onChange={e => setFmt(e.target.value)} disabled={loading}>
                <option value="mp3">mp3</option>
                <option value="m4a">m4a</option>
                <option value="opus">opus</option>
              </select>
            </label>
            <label>
              Calidad
              <select value={quality} onChange={e => setQuality(Number(e.target.value))} disabled={loading}>
                <option value={320}>320 kbps</option>
                <option value={192}>192 kbps</option>
                <option value={128}>128 kbps</option>
              </select>
            </label>
          </div>
          <div className="quick-actions">
            <button className="btn btn-ghost" type="button" onClick={onClose} disabled={loading}>
              Cancelar
            </button>
            <button className="btn btn-accent" type="button" onClick={downloadNow} disabled={loading}>
              {loading ? <><span className="spinner" /> Descargando...</> : 'Descargar ahora'}
            </button>
          </div>
        </div>
      </section>
    </div>
  )
}
