import { useMemo, useRef, useState } from 'react'

export interface TrackRange {
  from: number
  to: number
}

interface Props {
  total: number
  range: TrackRange
  maxWindow?: number
  loading?: boolean
  onChange: (range: TrackRange) => void
}

const DEFAULT_MAX_WINDOW = 50

function clamp(n: number, min: number, max: number) {
  return Math.min(max, Math.max(min, n))
}

function windowSize(range: TrackRange) {
  return range.to - range.from + 1
}

function normalizeRange(
  next: TrackRange,
  total: number,
  maxWindow: number,
  changed: 'from' | 'to' | 'window' = 'window',
): TrackRange {
  let from = clamp(Math.round(next.from), 1, total)
  let to = clamp(Math.round(next.to), 1, total)

  if (from > to) {
    if (changed === 'from') to = from
    else from = to
  }

  if (to - from + 1 > maxWindow) {
    if (changed === 'from') {
      to = Math.min(total, from + maxWindow - 1)
      from = Math.max(1, to - maxWindow + 1)
    } else {
      from = Math.max(1, to - maxWindow + 1)
      to = Math.min(total, from + maxWindow - 1)
    }
  }

  return { from, to }
}

function pct(value: number, total: number) {
  if (total <= 1) return 0
  return ((value - 1) / (total - 1)) * 100
}

export function TrackRangeSlider({
  total,
  range,
  maxWindow = DEFAULT_MAX_WINDOW,
  loading = false,
  onChange,
}: Props) {
  const railRef = useRef<HTMLDivElement | null>(null)
  const dragStart = useRef<{ x: number; from: number; to: number } | null>(null)
  const [draggingWindow, setDraggingWindow] = useState(false)

  const marks = useMemo(() => {
    const values: number[] = []
    for (let value = 10; value <= total; value += 10) values.push(value)
    if (total > 1 && values[values.length - 1] !== total) values.push(total)
    return values
  }, [total])

  const canPrev = range.from > 1
  const canNext = range.to < total

  const commit = (next: TrackRange, changed?: 'from' | 'to' | 'window') => {
    onChange(normalizeRange(next, total, maxWindow, changed))
  }

  const setFirst = () => commit({ from: 1, to: Math.min(maxWindow, total) }, 'window')
  const setNext = () => {
    const width = windowSize(range)
    const from = clamp(range.from + width, 1, Math.max(1, total - width + 1))
    commit({ from, to: from + width - 1 }, 'window')
  }
  const setLast = () => {
    const width = Math.min(maxWindow, total)
    commit({ from: Math.max(1, total - width + 1), to: total }, 'window')
  }

  const startWindowDrag = (e: React.PointerEvent<HTMLButtonElement>) => {
    dragStart.current = { x: e.clientX, from: range.from, to: range.to }
    setDraggingWindow(true)
    e.currentTarget.setPointerCapture(e.pointerId)
  }

  const moveWindow = (e: React.PointerEvent<HTMLButtonElement>) => {
    const startState = dragStart.current
    const rail = railRef.current
    if (!startState || !rail) return

    const widthPx = rail.getBoundingClientRect().width
    if (widthPx <= 0) return

    const itemPx = widthPx / Math.max(total - 1, 1)
    const deltaItems = Math.round((e.clientX - startState.x) / itemPx)
    const width = windowSize({ from: startState.from, to: startState.to })
    const from = clamp(startState.from + deltaItems, 1, Math.max(1, total - width + 1))
    commit({ from, to: from + width - 1 }, 'window')
  }

  const endWindowDrag = (e: React.PointerEvent<HTMLButtonElement>) => {
    dragStart.current = null
    setDraggingWindow(false)
    e.currentTarget.releasePointerCapture(e.pointerId)
  }

  return (
    <section className="range-panel" aria-label="Seleccionar rango de canciones">
      <div className="range-head">
        <div>
          <span className="range-kicker">Rango de descarga</span>
          <strong>Mostrando {range.from}-{range.to} de {total}</strong>
        </div>
        {loading && <span className="range-loading"><span className="spinner" /> Cargando</span>}
      </div>

      <div className="range-rail-wrap">
        <div className="range-rail" ref={railRef}>
          <div
            className="range-window-fill"
            style={{
              left: `${pct(range.from, total)}%`,
              width: `${Math.max(0, pct(range.to, total) - pct(range.from, total))}%`,
            }}
          />
          <button
            className={`range-window ${draggingWindow ? 'dragging' : ''}`}
            type="button"
            aria-label="Mover ventana seleccionada"
            style={{
              left: `${pct(range.from, total)}%`,
              width: `${Math.max(3, pct(range.to, total) - pct(range.from, total))}%`,
            }}
            onPointerDown={startWindowDrag}
            onPointerMove={moveWindow}
            onPointerUp={endWindowDrag}
            onPointerCancel={endWindowDrag}
          />
          <div className="range-marks" aria-hidden="true">
            {marks.map(mark => (
              <span
                key={mark}
                className="range-mark"
                style={{ left: `${pct(mark, total)}%` }}
              >
                {mark % 50 === 0 || mark === total ? <em>{mark}</em> : null}
              </span>
            ))}
          </div>
        </div>

        <input
          className="range-input range-from"
          type="range"
          min={1}
          max={total}
          value={range.from}
          aria-label="Primera cancion visible"
          onChange={e => commit({ from: Number(e.target.value), to: range.to }, 'from')}
        />
        <input
          className="range-input range-to"
          type="range"
          min={1}
          max={total}
          value={range.to}
          aria-label="Ultima cancion visible"
          onChange={e => commit({ from: range.from, to: Number(e.target.value) }, 'to')}
        />
      </div>

      <div className="range-actions">
        <button type="button" onClick={setFirst} disabled={range.from === 1}>Primeras 50</button>
        <button type="button" onClick={setNext} disabled={!canNext}>Siguientes 50</button>
        <button type="button" onClick={setLast} disabled={!canPrev && range.to === total}>Últimas 50</button>
      </div>
    </section>
  )
}
