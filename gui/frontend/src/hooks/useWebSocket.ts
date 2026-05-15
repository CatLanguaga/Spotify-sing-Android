import { useCallback, useEffect, useRef, useState } from 'react'

export interface LogLine {
  raw: string
  level: 'INFO' | 'WARNING' | 'ERROR' | 'OTHER'
  timestamp: string
  message: string
}

function parseLine(raw: string): LogLine {
  const m = raw.match(/^\[(\d{2}:\d{2}:\d{2})\]\s+\[(INFO|WARNING|ERROR)\]\s+(.*)$/)
  if (m) return { raw, level: m[2] as LogLine['level'], timestamp: m[1], message: m[3] }
  const m2 = raw.match(/^\[(INFO|WARNING|ERROR)\]\s+(.*)$/)
  if (m2) return { raw, level: m2[1] as LogLine['level'], timestamp: '', message: m2[2] }
  return { raw, level: 'OTHER', timestamp: '', message: raw }
}

export function useWebSocket(script: string | null) {
  const [lines, setLines] = useState<LogLine[]>([])
  const [running, setRunning] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)

  const start = useCallback(() => {
    if (!script || wsRef.current) return
    setLines([])
    setRunning(true)
    const ws = new WebSocket(`ws://localhost:8000/ws/logs?script=${script}`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const line = parseLine(e.data.trimEnd())
      setLines((prev) => [...prev, line])
    }
    ws.onclose = () => {
      setRunning(false)
      wsRef.current = null
    }
    ws.onerror = () => {
      setRunning(false)
      wsRef.current = null
    }
  }, [script])

  const stop = useCallback(() => {
    wsRef.current?.close()
  }, [])

  const clear = useCallback(() => setLines([]), [])

  useEffect(() => () => { wsRef.current?.close() }, [])

  return { lines, running, start, stop, clear }
}
