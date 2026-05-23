import { useCallback, useState } from 'react'
import { Sidebar } from './components/Sidebar'
import { ToastProvider, useToast } from './components/Toast'
import { QueueView } from './views/QueueView'
import { MonitorView } from './views/MonitorView'
import { SettingsView } from './views/SettingsView'

type View = 'queue' | 'monitor' | 'settings'

function AppInner() {
  const [view, setView] = useState<View>('queue')
  const { toast } = useToast()

  const handleScriptComplete = useCallback((script: string) => {
    const label = script.replace('.py', '')
    toast(`Script "${label}" finished`, 'success')
  }, [toast])

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0D0D0D', overflow: 'hidden', flexDirection: 'column' }}>
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <Sidebar active={view} onNav={setView} />
        <main style={{ flex: 1, minWidth: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {view === 'queue'    && <QueueView onDownloadComplete={() => toast('Download started', 'info')} />}
          {view === 'monitor'  && <MonitorView onScriptComplete={handleScriptComplete} />}
          {view === 'settings' && <SettingsView />}
        </main>
      </div>
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
