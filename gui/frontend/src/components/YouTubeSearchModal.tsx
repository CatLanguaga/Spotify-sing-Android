import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { QueueItem } from '../api/types'

interface YTResult {
  title: string
  url: string
  duration: number | null
  channel: string | null
  thumbnail: string | null
}

interface Props {
  item: QueueItem
  onClose: () => void
  onSelect: (url: string) => void
}

export function YouTubeSearchModal({ item, onClose, onSelect }: Props) {
  const [results, setResults] = useState<YTResult[]>([])
  const [loading, setLoading] = useState(false)
  const [query, setQuery] = useState(`${item.title} ${item.artist}`)

  const search = async (q: string) => {
    if (!q.trim()) return
    setLoading(true)
    setResults([])
    try {
      const params = new URLSearchParams({ song: q, artist: item.artist })
      const res = await api.get<YTResult[]>(`/youtube/search?${params}`)
      setResults(res)
    } catch {
      setResults([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { search(query) }, [])

  const fmtDuration = (sec: number) =>
    `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#1A1A1A', border: '1px solid #2A2A2A', borderRadius: 12,
          width: 560, maxHeight: '70vh', display: 'flex', flexDirection: 'column',
          overflow: 'hidden',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div style={{
          padding: '12px 16px', borderBottom: '1px solid #2A2A2A',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontWeight: 700, fontSize: 14, color: '#fff' }}>YouTube Search</span>
          <span style={{ color: '#666', fontSize: 11, flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {item.title} — {item.artist}
          </span>
          <button
            onClick={onClose}
            style={{ background: 'none', border: 'none', color: '#666', fontSize: 18, cursor: 'pointer', lineHeight: 1 }}
          >
            ✕
          </button>
        </div>

        {/* Search bar */}
        <div style={{ padding: '10px 16px', borderBottom: '1px solid #1a1a1a', display: 'flex', gap: 8 }}>
          <input
            value={query}
            onChange={e => setQuery(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && search(query)}
            style={{
              flex: 1, background: '#111', border: '1px solid #2A2A2A', borderRadius: 6,
              color: '#fff', fontSize: 12, padding: '6px 10px', outline: 'none',
            }}
            placeholder="Search YouTube..."
            autoFocus
          />
          <button
            onClick={() => search(query)}
            disabled={loading}
            style={{
              background: '#1DB954', border: 'none', borderRadius: 6,
              color: '#000', fontWeight: 700, fontSize: 12,
              padding: '6px 14px', cursor: loading ? 'not-allowed' : 'pointer',
              opacity: loading ? 0.7 : 1,
            }}
          >
            {loading ? '…' : 'Search'}
          </button>
        </div>

        {/* Results */}
        <div style={{ overflow: 'auto', flex: 1 }}>
          {loading && (
            <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>Searching...</div>
          )}
          {!loading && results.length === 0 && (
            <div style={{ padding: 24, textAlign: 'center', color: '#666', fontSize: 12 }}>No results.</div>
          )}
          {results.map((r, i) => (
            <div
              key={i}
              style={{
                display: 'flex', alignItems: 'center', gap: 12, padding: '10px 16px',
                borderBottom: '1px solid rgba(255,255,255,0.04)', cursor: 'pointer',
              }}
              onMouseEnter={e => (e.currentTarget.style.background = '#222')}
              onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
            >
              {r.thumbnail
                ? <img src={r.thumbnail} alt="" style={{ width: 64, height: 36, borderRadius: 4, objectFit: 'cover', flexShrink: 0 }} />
                : <div style={{ width: 64, height: 36, background: '#2A2A2A', borderRadius: 4, flexShrink: 0 }} />
              }
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 12, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {r.title}
                </div>
                {r.channel && (
                  <div style={{ fontSize: 11, color: '#B3B3B3', marginTop: 2 }}>{r.channel}</div>
                )}
              </div>
              {r.duration != null && (
                <span style={{ fontSize: 11, color: '#666', fontFamily: 'monospace', flexShrink: 0 }}>
                  {fmtDuration(r.duration)}
                </span>
              )}
              <button
                onClick={() => onSelect(r.url)}
                style={{
                  background: '#1DB954', border: 'none', borderRadius: 5,
                  color: '#000', fontWeight: 700, fontSize: 11,
                  padding: '5px 12px', cursor: 'pointer', flexShrink: 0,
                }}
              >
                Use
              </button>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
