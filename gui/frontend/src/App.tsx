import { useCallback, useState } from 'react'
import useSWR from 'swr'
import { Sidebar } from './components/Sidebar'
import { ToastProvider, useToast } from './components/Toast'
import { CompareView } from './views/CompareView'
import { QueueView } from './views/QueueView'
import { MonitorView } from './views/MonitorView'
import { SettingsView } from './views/SettingsView'
import { fetcher } from './api/client'

type View = 'compare' | 'queue' | 'monitor' | 'settings'

function AppInner() {
  const [view, setView] = useState<View>('compare')
  const [compareRefreshSignal, setCompareRefreshSignal] = useState(0)
  const { toast } = useToast()

  const { data: adbStatus } = useSWR<{ connected: boolean }>(
    '/adb/status',
    (u: string) => fetcher<{ connected: boolean }>(u).catch(() => ({ connected: false })),
    { refreshInterval: 5000 },
  )

  const handleScriptComplete = useCallback((script: string) => {
    const label = script.replace('.py', '')
    toast(`Script "${label}" finished`, 'success')
    if (script === 'smart_compare.py' || script === 'generate_report.py') {
      setCompareRefreshSignal(n => n + 1)
    }
  }, [toast])

  const renderView = () => {
    switch (view) {
      case 'compare':  return <CompareView refreshSignal={compareRefreshSignal} />
      case 'queue':    return <QueueView />
      case 'monitor':  return <MonitorView onScriptComplete={handleScriptComplete} />
      case 'settings': return <SettingsView />
    }
  }

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0D0D0D', overflow: 'hidden' }}>
      <Sidebar active={view} onNav={setView} adbConnected={adbStatus?.connected ?? false} />
      <main style={{ flex: 1, minWidth: 0, height: '100vh', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
        {renderView()}
      </main>
    </div>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  )
}
