import { useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { LangBadge } from '../components/LangBadge'
import { SkeletonCard } from '../components/Skeleton'
import { YouTubeSearchModal } from '../components/YouTubeSearchModal'
import type { QueueItem } from '../api/types'

const btn = (color: string, bg: string, border: string, disabled = false) => ({
  color: disabled ? '#444' : color,
  background: disabled ? '#111' : bg,
  border: `1px solid ${disabled ? '#222' : border}`,
  borderRadius: 5, padding: '5px 11px', fontSize: 11, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1,
  whiteSpace: 'nowrap' as const,
})

const STATUS_STYLE: Record<string, { color: string; bg: string; border: string; label: string }> = {
  pending:     { color: '#888',    bg: '#1A1A1A',              border: '#2A2A2A',              label: 'PENDING'     },
  approved:    { color: '#1DB954', bg: 'rgba(29,185,84,0.10)', border: 'rgba(29,185,84,0.3)',  label: 'APPROVED'    },
  rejected:    { color: '#E22D44', bg: 'rgba(226,45,68,0.10)', border: 'rgba(226,45,68,0.3)',  label: 'REJECTED'    },
  downloading: { color: '#F59B23', bg: 'rgba(245,155,35,0.10)',border: 'rgba(245,155,35,0.3)', label: '⏳ DOWNLOADING'},
  done:        { color: '#1DB954', bg: 'rgba(29,185,84,0.15)', border: 'rgba(29,185,84,0.5)',  label: '✓ DONE'      },
  error:       { color: '#E22D44', bg: 'rgba(226,45,68,0.15)', border: 'rgba(226,45,68,0.5)',  label: '✗ ERROR'     },
}

function StatusChip({ status }: { status: string }) {
  const s = STATUS_STYLE[status] ?? STATUS_STYLE.pending
  return (
    <span style={{
      fontSize: 9, fontWeight: 700, letterSpacing: '0.08em',
      color: s.color, background: s.bg, border: `1px solid ${s.border}`,
      borderRadius: 4, padding: '2px 6px',
    }}>{s.label}</span>
  )
}

interface Props {
  onDownloadComplete?: () => void
}

export function QueueView({ onDownloadComplete }: Props) {
  const { data, isLoading, error, mutate } = useSWR<QueueItem[]>('/queue', fetcher)
  const items = data ?? []

  const [searchItem,    setSearchItem]    = useState<QueueItem | null>(null)
  const [downloading,   setDownloading]   = useState<Set<string>>(new Set())

  // ─── actions ───────────────────────────────────────────────────────────────

  const remove = async (id: string) => {
    await api.delete(`/queue/${id}`)
    mutate()
  }

  const setYouTubeUrl = async (id: string, url: string) => {
    await api.patch(`/queue/${id}`, { youtube_url: url })
    mutate()
    setSearchItem(null)
  }

  const downloadItem = async (item: QueueItem) => {
    setDownloading(prev => new Set([...prev, item.id]))
    try {
      await api.post(`/queue/${item.id}/download`, {})
      onDownloadComplete?.()
      mutate()
    } catch (e: unknown) {
      mutate() // refresh to show error status
    } finally {
      setDownloading(prev => { const s = new Set(prev); s.delete(item.id); return s })
    }
  }

  const clearDone = async () => {
    const done = items.filter(i => i.status === 'done' || i.status === 'error')
    await Promise.all(done.map(i => api.delete(`/queue/${i.id}`)))
    mutate()
  }

  const hasDone = items.some(i => i.status === 'done' || i.status === 'error')

  // ─── render ────────────────────────────────────────────────────────────────

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>

      {/* Header */}
      <div style={{
        padding: '16px 20px', borderBottom: '1px solid #1a1a1a',
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
      }}>
        <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' }}>
          Download Queue
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {hasDone && (
            <button onClick={clearDone} style={btn('#888', 'transparent', '#2A2A2A')}>
              Clear finished
            </button>
          )}
          <button onClick={() => mutate()} disabled={isLoading} style={btn('#B3B3B3', 'transparent', '#2A2A2A', isLoading)}>
            ↻ Refresh
          </button>
        </div>
      </div>

      {/* Flow hint */}
      <div style={{
        padding: '8px 20px', background: '#111', borderBottom: '1px solid #1a1a1a',
        fontSize: 11, color: '#555', display: 'flex', gap: 10, alignItems: 'center',
      }}>
        <span>Flow:</span>
        <span style={{ color: '#888' }}>Add from Compare</span>
        <span>→</span>
        <span style={{ color: '#74B9FF' }}>🔍 Search on YouTube</span>
        <span>→</span>
        <span style={{ color: '#F59B23' }}>Select version</span>
        <span>→</span>
        <span style={{ color: '#1DB954' }}>⬇ Download to phone</span>
      </div>

      {/* List */}
      <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 8 }}>

        {error && (
          <div style={{
            padding: '14px 18px',
            background: 'rgba(226,45,68,0.06)', border: '1px solid rgba(226,45,68,0.25)',
            borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 18 }}>⚠</span>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#E22D44' }}>Failed to load queue</div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>{error.message}</div>
            </div>
            <button onClick={() => mutate()} style={btn('#B3B3B3', '#1A1A1A', '#2A2A2A')}>Retry</button>
          </div>
        )}

        {isLoading && Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}

        {!isLoading && !error && items.length === 0 && (
          <div style={{ padding: 48, textAlign: 'center', color: '#555', fontSize: 13 }}>
            Queue is empty — add tracks from the Compare view.
          </div>
        )}

        {!isLoading && items.map(item => {
          const isDownloading = downloading.has(item.id) || item.status === 'downloading'
          const isDone        = item.status === 'done'
          const isError       = item.status === 'error'
          const hasUrl        = !!item.youtube_url
          const canDownload   = hasUrl && !isDownloading && !isDone

          return (
            <div key={item.id} style={{
              background: '#1A1A1A',
              border: `1px solid ${isDone ? 'rgba(29,185,84,0.3)' : isError ? 'rgba(226,45,68,0.3)' : '#2A2A2A'}`,
              borderRadius: 10, padding: '12px 14px',
              opacity: isDone ? 0.7 : 1,
              display: 'flex', flexDirection: 'column', gap: 10,
            }}>

              {/* Top row: cover + info + status + remove */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {item.cover_url
                  ? <img src={item.cover_url} alt="" style={{ width: 48, height: 48, borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
                  : <div style={{ width: 48, height: 48, borderRadius: 6, background: '#2A2A2A', flexShrink: 0 }} />
                }
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {item.title}
                  </div>
                  <div style={{ fontSize: 11, color: '#888', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
                    {item.artist}
                    <span style={{ color: '#333' }}>·</span>
                    <LangBadge lang={item.language} />
                    <span style={{ color: '#333' }}>·</span>
                    <span style={{ fontFamily: 'monospace', color: '#555' }}>{item.fmt?.toUpperCase()} {item.quality}k</span>
                  </div>
                </div>
                <StatusChip status={item.status} />
                <button
                  onClick={() => remove(item.id)}
                  disabled={isDownloading}
                  style={{ background: 'none', border: 'none', color: '#444', fontSize: 16, cursor: isDownloading ? 'not-allowed' : 'pointer', padding: '2px 4px', lineHeight: 1 }}
                  title="Remove"
                >✕</button>
              </div>

              {/* YouTube selection row */}
              {!isDone && (
                <div style={{
                  display: 'flex', alignItems: 'center', gap: 8,
                  padding: '8px 10px',
                  background: '#111', borderRadius: 6,
                  border: `1px solid ${hasUrl ? 'rgba(29,185,84,0.2)' : '#1A1A1A'}`,
                }}>
                  {hasUrl ? (
                    <>
                      <span style={{ fontSize: 10, color: '#E22D44', flexShrink: 0 }}>▶ YT</span>
                      <span style={{ flex: 1, fontSize: 11, color: '#888', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                        {item.youtube_url}
                      </span>
                      <button
                        onClick={() => setSearchItem(item)}
                        disabled={isDownloading}
                        style={btn('#74B9FF', 'transparent', 'rgba(116,185,255,0.3)', isDownloading)}
                      >
                        🔍 Change
                      </button>
                    </>
                  ) : (
                    <>
                      <span style={{ flex: 1, fontSize: 11, color: '#555' }}>No YouTube source selected</span>
                      <button
                        onClick={() => setSearchItem(item)}
                        style={btn('#74B9FF', 'rgba(116,185,255,0.08)', 'rgba(116,185,255,0.35)')}
                      >
                        🔍 Search on YouTube
                      </button>
                    </>
                  )}
                </div>
              )}

              {/* Download button row */}
              {!isDone && (
                <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
                  <button
                    disabled={!canDownload}
                    onClick={() => downloadItem(item)}
                    style={{
                      ...btn('#000', '#1DB954', '#1DB954', !canDownload),
                      padding: '7px 20px', fontSize: 12,
                    }}
                    title={!hasUrl ? 'Search on YouTube first' : ''}
                  >
                    {isDownloading ? '⏳ Downloading...' : '⬇ Download to Phone'}
                  </button>
                </div>
              )}

              {isError && (
                <div style={{ fontSize: 11, color: '#E22D44', padding: '0 2px' }}>
                  Download failed — try changing the YouTube source and retry.
                </div>
              )}
            </div>
          )
        })}
      </div>

      {searchItem && (
        <YouTubeSearchModal
          item={searchItem}
          onClose={() => setSearchItem(null)}
          onSelect={url => setYouTubeUrl(searchItem.id, url)}
        />
      )}
    </div>
  )
}
