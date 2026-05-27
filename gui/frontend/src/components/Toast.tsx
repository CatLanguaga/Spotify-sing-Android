import { createContext, useCallback, useContext, useRef, useState } from 'react'

interface ToastItem {
  id: number
  message: string
  type: 'success' | 'error' | 'info'
}

interface ToastContextValue {
  toast: (message: string, type?: ToastItem['type']) => void
}

const ToastContext = createContext<ToastContextValue>({ toast: () => {} })

export function useToast() {
  return useContext(ToastContext)
}

const COLORS = {
  success: '#1DB954',
  error:   '#E22D44',
  info:    '#74B9FF',
}

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([])
  const counter = useRef(0)

  const toast = useCallback((message: string, type: ToastItem['type'] = 'success') => {
    const id = ++counter.current
    setToasts(prev => [...prev, { id, message, type }])
    setTimeout(() => setToasts(prev => prev.filter(t => t.id !== id)), 3500)
  }, [])

  return (
    <ToastContext.Provider value={{ toast }}>
      {children}
      <div style={{
        position: 'fixed', bottom: 24, right: 24,
        display: 'flex', flexDirection: 'column', gap: 8,
        zIndex: 9999, pointerEvents: 'none',
      }}>
        {toasts.map(t => (
          <div key={t.id} style={{
            background: '#fff',
            border: `1px solid ${COLORS[t.type]}`,
            borderLeft: `3px solid ${COLORS[t.type]}`,
            borderRadius: 10, padding: '12px 18px',
            color: '#0F0F11', fontSize: 14, fontWeight: 500,
            boxShadow: '0 8px 24px rgba(15,15,17,0.12)',
            minWidth: 240, pointerEvents: 'auto',
            animation: 'fadeInUp 0.18s ease',
          }}>
            {t.message}
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  )
}
