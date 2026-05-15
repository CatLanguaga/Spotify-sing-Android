import { useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { LangBadge } from '../components/LangBadge'
import { ScoreBadge } from '../components/ScoreBadge'
import { YouTubeSearchModal } from '../components/YouTubeSearchModal'
import type { QueueItem } from '../api/types'

const btn = (color: string, bg: string, border: string) => ({
  color, background: bg, border: `1px solid ${border}`,
  borderRadius: 5, padding: '4px 10px', fontSize: 11, fontWeight: 600, cursor: 'pointer',
})

export function QueueView() {
  const { data = [], mutate } = useSWR<QueueItem[]>('/queue', fetcher)
  const [searchItem, setSearchItem] = useState<QueueItem | null>(null)

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
      data.filter(i => i.status === 'pending').map(i => api.patch(`/queue/${i.id}`, { status: 'approved' }))
    )
    mutate()
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
          <button onClick={approveAll} style={btn('#1DB954', 'rgba(29,185,84,0.10)', 'rgba(29,185,84,0.3)')}>
            ✓ Approve All
          </button>
          <button style={btn('#000', '#1DB954', '#1DB954')}>
            ↓ Download ({data.filter(i => i.status === 'approved').length})
          </button>
        </div>
      </div>

      <div style={{ flex: 1, overflow: 'auto', padding: '12px 20px', display: 'flex', flexDirection: 'column', gap: 6 }}>
        {data.length === 0 && (
          <div style={{ padding: 40, textAlign: 'center', color: '#666' }}>
            Queue is empty. Add tracks from Compare view.
          </div>
        )}
        {data.map(item => (
          <div key={item.id} style={{
            background: item.status === 'rejected' ? 'rgba(226,45,68,0.05)' : '#1A1A1A',
            border: `1px solid ${statusBorder[item.status] ?? '#2A2A2A'}`,
            borderRadius: 8, padding: 12,
            opacity: item.status === 'rejected' ? 0.5 : 1,
            borderTop: item.status === 'approved' ? '2px solid #1DB954' : undefined,
            display: 'flex', alignItems: 'center', gap: 12,
          }}>
            {/* Cover */}
            {item.cover_url
              ? <img src={item.cover_url} alt="" style={{ width: 48, height: 48, borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
              : <div style={{ width: 48, height: 48, borderRadius: 6, background: '#2A2A2A', flexShrink: 0 }} />
            }

            {/* Info */}
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {item.title}
              </div>
              <div style={{ fontSize: 11, color: '#B3B3B3', marginTop: 2, display: 'flex', alignItems: 'center', gap: 6 }}>
                {item.artist} · <LangBadge lang={item.language} />
                {item.youtube_url && (
                  <span style={{ color: '#E22D44', fontSize: 10 }}>▶ YT</span>
                )}
              </div>
            </div>

            {/* Score + actions */}
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
