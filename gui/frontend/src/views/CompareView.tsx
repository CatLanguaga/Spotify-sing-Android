import { useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { fetcher } from '../api/client'
import { LangBadge } from '../components/LangBadge'
import type { SpotifyTrack } from '../api/types'

interface PlaylistResponse {
  info: { name: string; total_tracks: number }
  tracks: SpotifyTrack[]
  count: number
}

const btn = (color: string, bg: string, border: string, disabled = false) => ({
  color: disabled ? '#444' : color,
  background: disabled ? '#111' : bg,
  border: `1px solid ${disabled ? '#222' : border}`,
  borderRadius: 5, padding: '4px 10px',
  fontSize: 11, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.5 : 1,
})

const numInput = {
  width: 70, background: '#1A1A1A', border: '1px solid #2A2A2A',
  borderRadius: 5, color: '#fff', fontSize: 12,
  padding: '4px 8px', textAlign: 'center' as const, outline: 'none',
}

interface Props {
  refreshSignal?: number
}

export function CompareView({ refreshSignal }: Props) {
  const { data: cfg } = useSWR<Record<string, unknown>>('/config', fetcher)
  const playlistId = (cfg?.playlist_id as string) || '37i9dQZF1DX4SBhb3fqCJd'

  const [draftFrom, setDraftFrom] = useState(1)
  const [draftTo,   setDraftTo]   = useState(50)
  const [range,     setRange]     = useState({ from: 1, to: 50 })

  const offset = range.from - 1
  const limit  = Math.max(1, range.to - range.from + 1)

  const { data, isLoading, error, mutate } = useSWR<PlaylistResponse>(
    `/spotify/playlist/${playlistId}?offset=${offset}&limit=${limit}`,
    fetcher,
  )

  const prevSignal = useRef(refreshSignal)
  useEffect(() => {
    if (refreshSignal !== undefined && refreshSignal !== prevSignal.current) {
      prevSignal.current = refreshSignal
      mutate()
    }
  }, [refreshSignal, mutate])

  const applyRange = () => {
    const from = Math.max(1, draftFrom)
    const to   = Math.max(from, draftTo)
    setDraftFrom(from)
    setDraftTo(to)
    setRange({ from, to })
  }

  const handleKey = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') applyRange()
  }

  const total = data?.info?.total_tracks ?? null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #1a1a1a' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', flex: 1 }}>
            Compare Library
          </h1>

          {/* Range + refresh — right-aligned, all inline */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{ fontSize: 11, color: '#555' }}>Tracks</span>
            <input
              type="number" min={1} value={draftFrom}
              onChange={e => setDraftFrom(+e.target.value)}
              onKeyDown={handleKey}
              style={numInput}
            />
            <span style={{ fontSize: 12, color: '#333' }}>–</span>
            <input
              type="number" min={1} value={draftTo}
              onChange={e => setDraftTo(+e.target.value)}
              onKeyDown={handleKey}
              style={numInput}
            />
            {total && (
              <span style={{ fontSize: 11, color: '#444', fontFamily: 'monospace' }}>/ {total}</span>
            )}
            <button
              onClick={applyRange}
              disabled={isLoading}
              style={{ ...btn('#000', '#1DB954', '#1DB954', isLoading), padding: '5px 14px', fontSize: 12 }}
            >
              Apply
            </button>

            {/* Divider */}
            <div style={{ width: 1, height: 18, background: '#2A2A2A' }} />

            <button
              onClick={() => mutate()}
              disabled={isLoading}
              style={{ ...btn('#B3B3B3', 'transparent', '#2A2A2A', isLoading), padding: '5px 12px', fontSize: 12 }}
            >
              ↻ Refresh
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: 2, background: '#1a1a1a', borderRadius: 2, marginTop: 12 }}>
          <div style={{
            width: isLoading ? '60%' : '100%',
            height: '100%', background: '#1DB954', borderRadius: 2, transition: 'width 0.4s',
          }} />
        </div>
      </div>

      {/* Stat strip */}
      {data && (
        <div style={{ display: 'flex', gap: 8, padding: '10px 20px', borderBottom: '1px solid #1a1a1a' }}>
          {[
            { label: 'FETCHED',  value: data.count,                           color: '#fff'    },
            { label: 'IN PLAYLIST', value: data.info?.total_tracks ?? '—',    color: '#1DB954' },
            { label: 'FROM',     value: range.from,                           color: '#74B9FF' },
            { label: 'TO',       value: range.from + data.count - 1,          color: '#74B9FF' },
          ].map(({ label, value, color }) => (
            <div key={label} style={{
              background: '#1A1A1A', border: '1px solid #2A2A2A',
              borderRadius: 6, padding: '7px 14px', minWidth: 80,
            }}>
              <div style={{ color, fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700 }}>{value}</div>
              <div style={{ color: '#666', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', marginTop: 2 }}>{label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {isLoading && (
          <div style={{ padding: 40, textAlign: 'center', color: '#666' }}>Loading tracks {range.from}–{range.to}...</div>
        )}
        {error && (
          <div style={{ padding: 40, textAlign: 'center', color: '#E22D44' }}>
            Error: {error.message}
          </div>
        )}
        {data && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2A2A2A' }}>
                {['#', 'TRACK', 'ARTIST', 'LANG', 'DURATION', 'ACTIONS'].map(h => (
                  <th key={h} style={{
                    padding: '8px 16px', textAlign: 'left',
                    fontSize: 10, fontWeight: 700, letterSpacing: '0.08em',
                    color: '#666', position: 'sticky', top: 0, background: '#111',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {data.tracks.map((track, i) => (
                <tr
                  key={track.spotify_id || i}
                  style={{ borderBottom: '1px solid rgba(255,255,255,0.04)', transition: 'background 0.1s' }}
                  onMouseEnter={e => (e.currentTarget.style.background = '#222')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <td style={{ padding: '8px 16px', fontSize: 11, color: '#555', fontFamily: 'monospace', width: 40 }}>
                    {range.from + i}
                  </td>
                  <td style={{ padding: '8px 16px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      {track.album_art_url
                        ? <img src={track.album_art_url} alt="" style={{ width: 32, height: 32, borderRadius: 4, objectFit: 'cover' }} />
                        : <div style={{ width: 32, height: 32, borderRadius: 4, background: '#2A2A2A' }} />
                      }
                      <span style={{ fontSize: 13, fontWeight: 500, color: '#fff', maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {track.name}
                      </span>
                    </div>
                  </td>
                  <td style={{ padding: '8px 16px', fontSize: 11, color: '#B3B3B3' }}>{track.artist}</td>
                  <td style={{ padding: '8px 16px' }}><LangBadge lang={track.language} /></td>
                  <td style={{ padding: '8px 16px', fontSize: 11, color: '#666', fontFamily: 'monospace' }}>
                    {Math.floor(track.duration_ms / 60000)}:{String(Math.floor((track.duration_ms % 60000) / 1000)).padStart(2, '0')}
                  </td>
                  <td style={{ padding: '8px 16px' }}>
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button style={btn('#1DB954', 'rgba(29,185,84,0.10)', 'rgba(29,185,84,0.3)')}>+ Queue</button>
                      <button style={btn('#B3B3B3', '#1A1A1A', '#2A2A2A')}>Search Alt</button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
