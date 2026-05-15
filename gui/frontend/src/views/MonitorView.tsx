import { useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { fetcher } from '../api/client'
import { useWebSocket } from '../hooks/useWebSocket'
import type { ScriptInfo } from '../api/types'

interface Props {
  onScriptComplete?: (script: string) => void
}

const LEVEL_COLORS = {
  INFO:    { label: '#1DB954', msg: '#A8C9A8' },
  WARNING: { label: '#F59B23', msg: '#E0C87A' },
  ERROR:   { label: '#E22D44', msg: '#FF8A9A' },
  OTHER:   { label: '#666',    msg: '#999'    },
}

const btn = (color: string, bg: string, border: string, disabled = false) => ({
  color: disabled ? '#444' : color, background: disabled ? '#111' : bg,
  border: `1px solid ${disabled ? '#222' : border}`,
  borderRadius: 5, padding: '5px 12px', fontSize: 12, fontWeight: 600,
  cursor: disabled ? 'not-allowed' : 'pointer', opacity: disabled ? 0.5 : 1,
})

export function MonitorView({ onScriptComplete }: Props) {
  const { data: scripts = [] } = useSWR<ScriptInfo[]>('/scripts', fetcher)
  const [selected, setSelected] = useState<string>('smart_compare.py')
  const { lines, running, start, stop, clear } = useWebSocket(selected)
  const bottomRef = useRef<HTMLDivElement>(null)
  const prevRunning = useRef(false)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [lines])

  useEffect(() => {
    if (prevRunning.current && !running) {
      onScriptComplete?.(selected)
    }
    prevRunning.current = running
  }, [running, selected, onScriptComplete])

  const progress = (() => {
    const last = [...lines].reverse().find(l => l.raw.match(/\[(\d+)\/(\d+)\]/))
    if (!last) return null
    const m = last.raw.match(/\[(\d+)\/(\d+)\]/)
    if (!m) return null
    return { current: parseInt(m[1]), total: parseInt(m[2]) }
  })()

  const pct = progress ? Math.round((progress.current / progress.total) * 100) : 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Header */}
      <div style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a1a' }}>
        <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff' }}>
          Process Monitor
        </h1>
      </div>

      {/* Toolbar */}
      <div style={{
        padding: '8px 16px', background: '#1A1A1A', borderBottom: '1px solid #2A2A2A',
        display: 'flex', alignItems: 'center', gap: 8,
      }}>
        <select
          value={selected}
          onChange={e => setSelected(e.target.value)}
          disabled={running}
          style={{
            background: '#111', border: '1px solid #2A2A2A', borderRadius: 5,
            color: '#fff', fontSize: 12, padding: '5px 8px', cursor: 'pointer',
          }}
        >
          {scripts.map(s => <option key={s.name} value={s.name}>{s.name}</option>)}
        </select>

        <button onClick={start} disabled={running} style={btn('#000', '#1DB954', '#1DB954', running)}>▶ Run</button>
        <button onClick={stop}  disabled={!running} style={btn('#B3B3B3', '#1A1A1A', '#2A2A2A', !running)}>■ Stop</button>
        <button onClick={clear} disabled={running}  style={btn('#B3B3B3', '#1A1A1A', '#2A2A2A', running)}>Clear</button>

        {/* Progress */}
        <div style={{ flex: 1, display: 'flex', alignItems: 'center', gap: 8, marginLeft: 8 }}>
          <div style={{ flex: 1, height: 4, background: '#2A2A2A', borderRadius: 2 }}>
            <div style={{
              width: `${running && !progress ? 40 : pct}%`,
              height: '100%', background: '#1DB954', borderRadius: 2,
              transition: 'width 0.3s',
            }} />
          </div>
          {progress && (
            <span style={{ fontSize: 11, color: '#B3B3B3', fontFamily: 'monospace', whiteSpace: 'nowrap' }}>
              {progress.current}/{progress.total} ({pct}%)
            </span>
          )}
          {running && !progress && (
            <span style={{ fontSize: 11, color: '#666', fontFamily: 'monospace' }}>Running...</span>
          )}
        </div>
      </div>

      {/* Terminal */}
      <div style={{
        flex: 1, overflow: 'auto', background: '#090909',
        padding: '12px 14px', fontFamily: 'JetBrains Mono, monospace',
        fontSize: 11.5, lineHeight: 1.75,
      }}>
        {lines.length === 0 && (
          <span style={{ color: '#333' }}>Select a script and press ▶ Run to start...</span>
        )}
        {lines.map((line, i) => {
          const c = LEVEL_COLORS[line.level]
          return (
            <div key={i} style={{ display: 'flex', gap: 0 }}>
              {line.timestamp && (
                <span style={{ color: '#444', width: 70, flexShrink: 0 }}>{line.timestamp}</span>
              )}
              {line.level !== 'OTHER' && (
                <span style={{ color: c.label, width: 72, flexShrink: 0, fontWeight: 700 }}>
                  [{line.level}]
                </span>
              )}
              <span style={{ color: c.msg }}>{line.message || line.raw}</span>
            </div>
          )
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  )
}
