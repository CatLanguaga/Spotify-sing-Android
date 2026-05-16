import { useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { LangBadge } from '../components/LangBadge'
import { ScoreBadge } from '../components/ScoreBadge'
import { SkeletonCard } from '../components/Skeleton'
import { YouTubeSearchModal } from '../components/YouTubeSearchModal'
import type { QueueItem } from '../api/types'

const btn = (color: string, bg: string, border: string, disabled = false) => ({
  color: disabled ? '#444' : color,
  background: disabled ? '#111' : bg,
  border: `1px solid ${disabled ? '#222' : border}`,
  borderRadius: 5, padding: '4px 10px', fontSize: 11, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1,
})

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.65)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 7000, backdropFilter: 'blur(3px)',
}

interface Props {
  onDownloadComplete?: () => void
}

export function QueueView({ onDownloadComplete }: Props) {
  const { data, isLoading, error, mutate } = useSWR<QueueItem[]>('/queue', fetcher)
  const items = data ?? []
  const [searchItem,       setSearchItem]       = useState<QueueItem | null>(null)
  const [showConfirm,      setShowConfirm]      = useState(false)
  const [downloading,      setDownloading]      = useState(false)

  const approved = items.filter(i => i.status === 'approved')

  const patch = async (id: string, status: QueueItem['status']) => {
    await api.patch(`/queue/${id}`, { status })
    mutate()
  }

  const remove = async (id: string) => {
    await api.delete(`/queue/${id}`)
    mutate()
  }

  const applyYouTubeUrl = async (id: string, url: string) => {
    await api.patch(`/queue/${id}`, { youtube_url: url })
    mutate()
    setSearchItem(null)
  }

  const approveAll = async () => {
    await Promise.all(
      items.filter(i => i.status === 'pending').map(i => api.patch(`/queue/${i.id}`, { status: 'approved' }))
    )
    mutate()
  }

  const startDownload = async () => {
    setDownloading(true)
    setShowConfirm(false)
    try {
      await api.post('/scripts/run', { script: 'download_missing.py' })
      onDownloadComplete?.()
    } catch {
      // script errors surface in the Monitor view
    } finally {
      setDownloading(false)
    }
  }

  const statusBorder: Record<string, string> = {
    approved: 'rgba(29,185,84,0.3)',
    rejected: 'rgba(226,45,68,0.3)',
    pending: '#2A2A2A',
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a1a', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' }}>
          Download Queue
        </h1>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={approveAll} disabled={isLoading} style={btn('#1DB954', 'rgba(29,185,84,0.10)', 'rgba(29,185,84,0.3)', isLoading)}>
            ✓ Approve All
          </button>
          <button
            disabled={approved.length === 0 || downloading}
            onClick={() => setShowConfirm(true)}
            style={btn('#000', '#1DB954', '#1DB954', approved.length === 0 || downloading)}
          >
            {downloading ? '↓ Starting...' : `↓ Download (${approved.length})`}
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {/* Error state */}
        {error && (
          <div style={{
            padding: '14px 18px',
            background: 'rgba(226,45,68,0.06)', border: '1px solid rgba(226,45,68,0.25)',
            borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 18 }}>⚠</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#E22D44' }}>Failed to load queue</div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 3 }}>{error.message}</div>
            </div>
            <button onClick={() => mutate()} style={{ marginLeft: 'auto', ...btn('#B3B3B3', '#1A1A1A', '#2A2A2A') }}>
              Retry
            </button>
          </div>
        )}

        {/* Loading skeletons */}
        {isLoading && Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)}

        {/* Empty state */}
        {!isLoading && !error && items.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#666' }}>
            Queue is empty. Add tracks from Compare view.
          </div>
        )}

        {/* Items */}
        {!isLoading && items.map(item => (
          <div key={item.id} style={{
            background: item.status === 'rejected' ? 'rgba(226,45,68,0.05)' : '#1A1A1A',
            border: `1px solid ${statusBorder[item.status] ?? '#2A2A2A'}`,
            borderRadius: 8, padding: 12,
            opacity: item.status === 'rejected' ? 0.5 : 1,
            borderTop: item.status === 'approved' ? '2px solid #1DB954' : undefined,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            {item.cover_url
              ? <img src={item.cover_url} alt="" style={{ width: 48, height: 48, borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
              : <div style={{ width: 48, height: 48, borderRadius: 6, background: '#2A2A2A', flexShrink: 0 }} />
            }
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.title}
              </div>
              <div style={{ fontSize: 11, color: '#B3B3B3', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
                {item.artist} · <LangBadge lang={item.language} />
                {item.youtube_url && <span style={{ color: '#E22D44', fontSize: 10 }}>▶ YT</span>}
              </div>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexShrink: 0 }}>
              <ScoreBadge score={Math.round(item.score)} />
              <button onClick={() => setSearchItem(item)} style={btn('#B3B3B3', '#111', '#2A2A2A')}>⌕</button>
              <button onClick={() => patch(item.id, 'approved')} style={btn('#1DB954', 'rgba(29,185,84,0.10)', 'rgba(29,185,84,0.3)')}>✓</button>
              <button onClick={() => patch(item.id, 'rejected')} style={btn('#E22D44', 'rgba(226,45,68,0.10)', 'rgba(226,45,68,0.3)')}>✗</button>
              <button onClick={() => remove(item.id)} style={btn('#666', '#1A1A1A', '#2A2A2A')}>🗑</button>
            </div>
          </div>
        ))}
      </div>

      {/* Download confirmation modal */}
      {showConfirm && (
        <div style={overlay} onClick={() => setShowConfirm(false)}>
          <div style={{
            background: '#141414', border: '1px solid #2A2A2A', borderRadius: 12,
            padding: '28px 32px', width: 360,
            animation: 'slideIn 0.2s ease', boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
          }} onClick={e => e.stopPropagation()}>
            <div style={{ fontSize: 15, fontWeight: 700, color: '#fff', marginBottom: 8 }}>
              Start download?
            </div>
            <div style={{ fontSize: 13, color: '#888', marginBottom: 24, lineHeight: 1.6 }}>
              This will run <code style={{ color: '#1DB954', background: '#0F1A0F', padding: '1px 5px', borderRadius: 3 }}>download_missing.py</code> for{' '}
              <strong style={{ color: '#fff' }}>{approved.length} approved track{approved.length !== 1 ? 's' : ''}</strong>.
              You can follow progress in the Monitor view.
            </div>
            <div style={{ display: 'flex', gap: 8 }}>
              <button
                onClick={() => setShowConfirm(false)}
                style={{ flex: 1, padding: '9px 0', borderRadius: 7, border: '1px solid #2A2A2A', background: 'transparent', color: '#888', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
              >
                Cancel
              </button>
              <button
                onClick={startDownload}
                style={{ flex: 1, padding: '9px 0', borderRadius: 7, border: 'none', background: '#1DB954', color: '#000', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}
              >
                Download
              </button>
            </div>
          </div>
        </div>
      )}

      {searchItem && (
        <YouTubeSearchModal
          item={searchItem}
          onClose={() => setSearchItem(null)}
          onSelect={(url) => applyYouTubeUrl(searchItem.id, url)}
        />
      )}
    </div>
  )
}
