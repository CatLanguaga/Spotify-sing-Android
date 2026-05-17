import { useState } from 'react'
import type { SpotifyTrack } from '../api/types'

interface Props {
  track: SpotifyTrack
  realIndex: number
  onConfirm: (fmt: string, quality: number) => void
  onClose: () => void
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 8000, backdropFilter: 'blur(4px)',
}

function OptionGroup<T extends string | number>({
  label, options, value, onChange,
}: {
  label: string
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div style={{ marginBottom: 16 }}>
      <div style={{ fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', color: '#666', marginBottom: 6 }}>{label}</div>
      <div style={{ display: 'flex', gap: 6 }}>
        {options.map(opt => {
          const active = opt.value === value
          return (
            <button
              key={String(opt.value)}
              onClick={() => onChange(opt.value)}
              style={{
                flex: 1, padding: '7px 0', borderRadius: 6, cursor: 'pointer',
                fontSize: 12, fontWeight: 700,
                background: active ? 'rgba(29,185,84,0.15)' : '#1A1A1A',
                border: `1px solid ${active ? 'rgba(29,185,84,0.5)' : '#2A2A2A'}`,
                color: active ? '#1DB954' : '#888',
                transition: 'all 0.15s',
              }}
            >
              {opt.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}

export function AddToQueueModal({ track, realIndex, onConfirm, onClose }: Props) {
  const [fmt,     setFmt]     = useState('mp3')
  const [quality, setQuality] = useState(320)

  const handleConfirm = () => onConfirm(fmt, quality)

  return (
    <div style={overlay} onClick={onClose}>
      <div
        style={{
          background: '#141414', border: '1px solid #2A2A2A', borderRadius: 12,
          padding: '24px 28px', width: 380,
          boxShadow: '0 20px 60px rgba(0,0,0,0.7)',
          animation: 'slideIn 0.18s ease',
        }}
        onClick={e => e.stopPropagation()}
      >
        {/* Track info */}
        <div style={{ display: 'flex', gap: 12, marginBottom: 20, alignItems: 'center' }}>
          {track.album_art_url
            ? <img src={track.album_art_url} alt="" style={{ width: 48, height: 48, borderRadius: 6, objectFit: 'cover', flexShrink: 0 }} />
            : <div style={{ width: 48, height: 48, borderRadius: 6, background: '#2A2A2A', flexShrink: 0 }} />
          }
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {track.name}
            </div>
            <div style={{ fontSize: 12, color: '#888', marginTop: 2 }}>{track.artist}</div>
            <div style={{ fontSize: 10, color: '#555', fontFamily: 'monospace', marginTop: 1 }}>#{realIndex}</div>
          </div>
        </div>

        <OptionGroup
          label="FORMAT"
          options={[
            { value: 'mp3',  label: 'MP3'  },
            { value: 'm4a',  label: 'M4A'  },
            { value: 'opus', label: 'OPUS' },
          ]}
          value={fmt}
          onChange={setFmt}
        />

        <OptionGroup
          label="QUALITY"
          options={[
            { value: 128, label: '128 kbps' },
            { value: 192, label: '192 kbps' },
            { value: 320, label: '320 kbps' },
          ]}
          value={quality}
          onChange={(v) => setQuality(v as number)}
        />

        <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
          <button
            onClick={onClose}
            style={{
              flex: 1, padding: '9px 0', borderRadius: 7,
              border: '1px solid #2A2A2A', background: 'transparent',
              color: '#888', fontSize: 13, fontWeight: 700, cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleConfirm}
            style={{
              flex: 1, padding: '9px 0', borderRadius: 7,
              border: 'none', background: '#1DB954',
              color: '#000', fontSize: 13, fontWeight: 700, cursor: 'pointer',
            }}
          >
            + Add to Queue
          </button>
        </div>
      </div>
    </div>
  )
}
