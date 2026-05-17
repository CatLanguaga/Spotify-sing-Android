import { useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { api, fetcher } from '../api/client'
import { LangBadge } from '../components/LangBadge'
import { SkeletonRow } from '../components/Skeleton'
import { AddToQueueModal } from '../components/AddToQueueModal'
import type { SpotifyTrack } from '../api/types'

interface PlaylistResponse {
  info: { name: string; total_tracks: number }
  tracks: SpotifyTrack[]
  count: number
}

interface CompareReport {
  missing_indices: number[]
  matched: number
  blacklisted: number
  missing_count: number
  analyzed_range: { start: number; end: number }
}

type PhoneStatus = 'match' | 'missing' | 'unknown'
type GroupCol = 'artist' | 'language' | 'status'

// Columns that support grouping and their data key
const GROUPABLE: Partial<Record<string, GroupCol>> = {
  ARTIST: 'artist',
  LANG:   'language',
  STATUS: 'status',
}

const STATUS_LABEL: Record<PhoneStatus, string> = {
  match:   '✓ ON PHONE',
  missing: '✗ MISSING',
  unknown: '—',
}

const btn = (color: string, bg: string, border: string, disabled = false) => ({
  color:        disabled ? '#444' : color,
  background:   disabled ? '#111' : bg,
  border:       `1px solid ${disabled ? '#222' : border}`,
  borderRadius: 5,
  padding:      '4px 10px',
  fontSize:     11,
  fontWeight:   600,
  cursor:       disabled ? 'not-allowed' : 'pointer',
  opacity:      disabled ? 0.5 : 1,
})

const numInput = {
  width: 70, background: '#1A1A1A', border: '1px solid #2A2A2A',
  borderRadius: 5, color: '#fff', fontSize: 12,
  padding: '4px 8px', textAlign: 'center' as const, outline: 'none',
}

function StatusBadge({ status }: { status: PhoneStatus }) {
  if (status === 'match') return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
      color: '#1DB954', background: 'rgba(29,185,84,0.12)',
      border: '1px solid rgba(29,185,84,0.3)', borderRadius: 4, padding: '2px 7px',
    }}>✓ ON PHONE</span>
  )
  if (status === 'missing') return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
      color: '#E22D44', background: 'rgba(226,45,68,0.12)',
      border: '1px solid rgba(226,45,68,0.3)', borderRadius: 4, padding: '2px 7px',
    }}>✗ MISSING</span>
  )
  return (
    <span style={{
      fontSize: 10, fontWeight: 700, letterSpacing: '0.06em',
      color: '#444', background: '#1A1A1A',
      border: '1px solid #222', borderRadius: 4, padding: '2px 7px',
    }}>—</span>
  )
}

interface Props {
  refreshSignal?: number
}

interface RowData {
  track: SpotifyTrack
  realIndex: number
  status: PhoneStatus
}

export function CompareView({ refreshSignal }: Props) {
  const { data: cfg } = useSWR<Record<string, unknown>>('/config', fetcher)
  const playlistId = (cfg?.playlist_id as string) || '37i9dQZF1DX4SBhb3fqCJd'

  const [draftFrom, setDraftFrom] = useState(1)
  const [draftTo,   setDraftTo]   = useState(50)
  const [range,     setRange]     = useState({ from: 1, to: 50 })

  const [report,        setReport]        = useState<CompareReport | null>(null)
  const [loadingReport, setLoadingReport] = useState(false)
  const [comparing,     setComparing]     = useState(false)
  const [compareError,  setCompareError]  = useState<string | null>(null)

  const offset = range.from - 1
  const limit  = Math.max(1, range.to - range.from + 1)

  const { data, isLoading, error, mutate } = useSWR<PlaylistResponse>(
    `/spotify/playlist/${playlistId}?offset=${offset}&limit=${limit}`,
    fetcher,
  )

  const loadReport = async () => {
    setLoadingReport(true)
    try {
      const r = await api.get<CompareReport>('/compare/report')
      setReport(r)
    } catch {
      // Silently ignore 404 (no report yet) — no banner needed
    } finally {
      setLoadingReport(false)
    }
  }

  const runCompare = async () => {
    setComparing(true)
    setCompareError(null)
    try {
      // script expects: <playlist_id> [offset] [max_tracks]
      const offset    = String(range.from - 1)
      const maxTracks = String(range.to - range.from + 1)
      await api.post('/scripts/run', { script: 'smart_compare.py', args: [playlistId, offset, maxTracks] })
      await loadReport()
      mutate()
    } catch (e: unknown) {
      setCompareError(e instanceof Error ? e.message : 'Compare failed')
    } finally {
      setComparing(false)
    }
  }

  // Auto-load report on mount (non-blocking — 404 just means no report yet)
  useEffect(() => { loadReport() }, [])

  // When Monitor finishes smart_compare.py, refreshSignal increments → reload report
  const prevSignal = useRef(refreshSignal)
  useEffect(() => {
    if (refreshSignal !== undefined && refreshSignal !== prevSignal.current) {
      prevSignal.current = refreshSignal
      mutate()
      loadReport()
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

  const missingSet = new Set(report?.missing_indices ?? [])

  const getStatus = (realIndex: number): PhoneStatus => {
    if (!report) return 'unknown'
    const { start, end } = report.analyzed_range
    if (realIndex < start || realIndex > end) return 'unknown'
    return missingSet.has(realIndex) ? 'missing' : 'match'
  }

  const total = data?.info?.total_tracks ?? null

  // Filter by phone status (null = show all)
  const [filterStatus, setFilterStatus] = useState<PhoneStatus | null>(null)

  // Group by column (null = no grouping)
  const [groupBy, setGroupBy] = useState<GroupCol | null>(null)

  // Reset filter and grouping when range changes
  useEffect(() => {
    setFilterStatus(null)
    setGroupBy(null)
  }, [range])

  const handleHeaderClick = (h: string) => {
    const col = GROUPABLE[h]
    if (!col) return
    setGroupBy(prev => prev === col ? null : col)
  }

  // Track which spotify_ids are already in the queue (fetched on mount)
  const [queuedIds, setQueuedIds] = useState<Set<string>>(new Set())

  useEffect(() => {
    api.get<{ spotify_id: string }[]>('/queue')
      .then(items => setQueuedIds(new Set(items.map(i => i.spotify_id))))
      .catch(() => {})
  }, [])

  // Add-to-queue modal state
  const [queuePending, setQueuePending] = useState<{ track: SpotifyTrack; realIndex: number } | null>(null)

  const addToQueue = async (track: SpotifyTrack, _realIndex: number, fmt: string, quality: number) => {
    await api.post('/queue', {
      spotify_id: track.spotify_id,
      title:      track.name,
      artist:     track.artist,
      album:      track.album,
      language:   track.language,
      cover_url:  track.album_art_url,
      fmt,
      quality,
    })
    setQueuedIds(prev => new Set([...prev, track.spotify_id]))
    setQueuePending(null)
  }

  const rangeInReport = report
    ? range.to >= report.analyzed_range.start && range.from <= report.analyzed_range.end
    : false

  // Build filtered rows
  const filteredRows: RowData[] = data
    ? data.tracks
        .map((track, i) => ({ track, realIndex: range.from + i, status: getStatus(range.from + i) }))
        .filter(({ track }) => !queuedIds.has(track.spotify_id))
        .filter(({ status }) => filterStatus === null || status === filterStatus)
    : []

  const getGroupKey = (row: RowData): string => {
    if (groupBy === 'artist')   return row.track.artist || '?'
    if (groupBy === 'language') return row.track.language || '?'
    if (groupBy === 'status')   return STATUS_LABEL[row.status]
    return ''
  }

  const renderTrackRow = (row: RowData) => {
    const { track, realIndex, status } = row
    const isMissing = status === 'missing'
    return (
      <tr
        key={track.spotify_id || realIndex}
        style={{
          borderBottom: '1px solid rgba(255,255,255,0.04)',
          transition:   'background 0.1s',
          background:   isMissing ? 'rgba(226,45,68,0.03)' : 'transparent',
        }}
        onMouseEnter={e => (e.currentTarget.style.background = '#222')}
        onMouseLeave={e => (e.currentTarget.style.background = isMissing ? 'rgba(226,45,68,0.03)' : 'transparent')}
      >
        <td style={{ padding: '8px 16px', fontSize: 11, color: '#555', fontFamily: 'monospace', width: 40 }}>
          {realIndex}
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
          <StatusBadge status={status} />
        </td>
        <td style={{ padding: '8px 16px' }}>
          <button
            onClick={() => setQueuePending({ track, realIndex })}
            style={btn('#1DB954', 'rgba(29,185,84,0.10)', 'rgba(29,185,84,0.3)')}
          >
            + Queue
          </button>
        </td>
      </tr>
    )
  }

  const buildTableBody = () => {
    if (isLoading) return Array.from({ length: 10 }).map((_, i) => <SkeletonRow key={i} cols={7} />)

    if (!groupBy) return filteredRows.map(renderTrackRow)

    // Group rows preserving insertion order
    const groups = new Map<string, RowData[]>()
    for (const row of filteredRows) {
      const key = getGroupKey(row)
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key)!.push(row)
    }

    const result: React.ReactNode[] = []
    for (const [key, rows] of groups) {
      result.push(
        <tr key={`grp-${key}`} style={{ background: '#161616' }}>
          <td colSpan={7} style={{
            padding: '6px 16px',
            fontSize: 10, fontWeight: 700, letterSpacing: '0.1em',
            color: '#888', borderBottom: '1px solid #2A2A2A',
            borderTop: '1px solid #2A2A2A',
          }}>
            {key}
            <span style={{ marginLeft: 8, color: '#444', fontWeight: 400 }}>{rows.length} track{rows.length !== 1 ? 's' : ''}</span>
          </td>
        </tr>
      )
      rows.forEach(row => result.push(renderTrackRow(row)))
    }
    return result
  }

  const HEADERS = ['#', 'TRACK', 'ARTIST', 'LANG', 'DURATION', 'STATUS', 'ACTIONS']

  return (
    <div style={{ display: 'flex', flexDirection: 'column', flex: 1, minHeight: 0 }}>
      {/* Header */}
      <div style={{ padding: '14px 20px', borderBottom: '1px solid #1a1a1a' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ margin: 0, fontSize: 17, fontWeight: 700, letterSpacing: '-0.02em', color: '#fff', flex: 1 }}>
            Compare Library
          </h1>

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
            <div style={{ width: 1, height: 18, background: '#2A2A2A' }} />
            <button
              onClick={() => mutate()}
              disabled={isLoading}
              style={{ ...btn('#B3B3B3', 'transparent', '#2A2A2A', isLoading), padding: '5px 12px', fontSize: 12 }}
            >
              ↻ Refresh
            </button>
            <button
              onClick={runCompare}
              disabled={comparing || isLoading}
              style={{
                ...btn('#74B9FF', 'rgba(116,185,255,0.1)', 'rgba(116,185,255,0.35)', comparing || isLoading),
                padding: '5px 14px', fontSize: 12,
              }}
            >
              {comparing ? '⏳ Comparing...' : '📱 Compare Android'}
            </button>
          </div>
        </div>

        {/* Progress bar */}
        <div style={{ height: 2, background: '#1a1a1a', borderRadius: 2, marginTop: 12 }}>
          <div style={{
            width:      (isLoading || loadingReport || comparing) ? '60%' : '100%',
            height:     '100%',
            background: comparing ? '#74B9FF' : '#1DB954',
            borderRadius: 2, transition: 'width 0.4s',
          }} />
        </div>
      </div>

      {/* Stat strip */}
      {(data && !isLoading) && (
        <div style={{ display: 'flex', gap: 8, padding: '10px 20px', borderBottom: '1px solid #1a1a1a', flexWrap: 'wrap', alignItems: 'center' }}>
          {[
            { label: 'FETCHED',     value: data.count,                      color: '#fff',    filter: null              },
            { label: 'IN PLAYLIST', value: data.info?.total_tracks ?? '—',  color: '#1DB954', filter: null              },
            { label: 'FROM',        value: range.from,                       color: '#74B9FF', filter: null              },
            { label: 'TO',          value: range.from + data.count - 1,     color: '#74B9FF', filter: null              },
            ...(report ? [
              { label: 'ON PHONE', value: report.matched,       color: '#1DB954', filter: 'match'   as PhoneStatus },
              { label: 'MISSING',  value: report.missing_count, color: '#E22D44', filter: 'missing' as PhoneStatus },
            ] : []),
          ].map(({ label, value, color, filter }) => {
            const isActive    = filter !== null && filterStatus === filter
            const isClickable = filter !== null && report !== null
            return (
              <div
                key={label}
                onClick={isClickable ? () => setFilterStatus(isActive ? null : filter) : undefined}
                style={{
                  background:  isActive ? `${color}18` : '#1A1A1A',
                  border:      `1px solid ${isActive ? color : '#2A2A2A'}`,
                  borderRadius: 6, padding: '7px 14px', minWidth: 80,
                  cursor:      isClickable ? 'pointer' : 'default',
                  transition:  'border-color 0.15s, background 0.15s',
                  userSelect:  'none',
                }}
              >
                <div style={{ color, fontFamily: 'JetBrains Mono, monospace', fontSize: 20, fontWeight: 700 }}>{value}</div>
                <div style={{ color: isActive ? color : '#666', fontSize: 10, fontWeight: 700, letterSpacing: '0.08em', marginTop: 2 }}>
                  {label}{isClickable && <span style={{ opacity: 0.5, fontWeight: 400 }}> {isActive ? '▲' : '▼'}</span>}
                </div>
              </div>
            )
          })}

          {/* Report range indicator */}
          {report && (
            <div style={{ marginLeft: 'auto', fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
              Report covers #{report.analyzed_range.start}–#{report.analyzed_range.end}
              {!rangeInReport && (
                <span style={{ color: '#F59B23', marginLeft: 6 }}>⚠ current view outside report range</span>
              )}
            </div>
          )}

          {/* No report yet hint */}
          {!report && !loadingReport && (
            <div style={{ marginLeft: 'auto', fontSize: 11, color: '#555' }}>
              No report — press <strong style={{ color: '#74B9FF' }}>Compare Android</strong> to scan
            </div>
          )}
        </div>
      )}

      {/* Compare error banner */}
      {compareError && (
        <div style={{
          margin: '8px 20px 0', padding: '10px 14px',
          background: 'rgba(226,45,68,0.06)', border: '1px solid rgba(226,45,68,0.25)',
          borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ fontSize: 16 }}>⚠</span>
          <div style={{ fontSize: 12, color: '#E22D44' }}>{compareError}</div>
          <button onClick={() => setCompareError(null)} style={{ marginLeft: 'auto', ...btn('#B3B3B3', '#1A1A1A', '#2A2A2A'), padding: '4px 10px' }}>
            Dismiss
          </button>
        </div>
      )}

      {/* Add to Queue modal */}
      {queuePending && (
        <AddToQueueModal
          track={queuePending.track}
          realIndex={queuePending.realIndex}
          onConfirm={(fmt, quality) => addToQueue(queuePending.track, queuePending.realIndex, fmt, quality)}
          onClose={() => setQueuePending(null)}
        />
      )}

      {/* Table */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {error && (
          <div style={{
            margin: 24, padding: '14px 18px',
            background: 'rgba(226,45,68,0.06)', border: '1px solid rgba(226,45,68,0.25)',
            borderRadius: 8, display: 'flex', alignItems: 'center', gap: 10,
          }}>
            <span style={{ fontSize: 18 }}>⚠</span>
            <div>
              <div style={{ fontSize: 13, fontWeight: 600, color: '#E22D44' }}>Failed to load tracks</div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 3 }}>{error.message}</div>
            </div>
            <button onClick={() => mutate()} style={{ marginLeft: 'auto', ...btn('#B3B3B3', '#1A1A1A', '#2A2A2A'), padding: '5px 12px' }}>
              Retry
            </button>
          </div>
        )}

        {(isLoading || data) && (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid #2A2A2A' }}>
                {HEADERS.map(h => {
                  const isGroupable = h in GROUPABLE
                  const isGrouped   = groupBy === GROUPABLE[h]
                  return (
                    <th
                      key={h}
                      onClick={() => handleHeaderClick(h)}
                      style={{
                        padding:    '8px 16px',
                        textAlign:  'left',
                        fontSize:   10,
                        fontWeight: 700,
                        letterSpacing: '0.08em',
                        color:      isGrouped ? '#fff' : isGroupable ? '#999' : '#666',
                        position:   'sticky', top: 0,
                        background: isGrouped ? '#1A1A1A' : '#111',
                        cursor:     isGroupable ? 'pointer' : 'default',
                        userSelect: 'none',
                        transition: 'color 0.15s, background 0.15s',
                        borderBottom: isGrouped ? '2px solid #74B9FF' : '1px solid transparent',
                      }}
                    >
                      {h}{isGroupable && <span style={{ marginLeft: 4, opacity: 0.4, fontSize: 9 }}>{isGrouped ? '▲' : '⊞'}</span>}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {buildTableBody()}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
