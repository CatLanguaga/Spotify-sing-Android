import { useCallback, useEffect, useRef, useState } from 'react'
import useSWR from 'swr'
import { Sidebar } from './components/Sidebar'
import { ToastProvider, useToast } from './components/Toast'
import { AdbConnectModal } from './components/AdbConnectModal'
import { CompareView } from './views/CompareView'
import { QueueView } from './views/QueueView'
import { MonitorView } from './views/MonitorView'
import { SettingsView } from './views/SettingsView'
import { fetcher } from './api/client'

type View = 'compare' | 'queue' | 'monitor' | 'settings'

interface AdbStatus {
  connected: boolean
  device: { serial: string; model: string } | null
}

function AppInner() {
  const [view, setView] = useState<View>('compare')
  const [compareRefreshSignal, setCompareRefreshSignal] = useState(0)
  const [pendingDevice, setPendingDevice] = useState<AdbStatus['device']>(null)
  const { toast } = useToast()

  const { data: adbStatus, error: adbError } = useSWR<AdbStatus>(
    '/adb/status',
    (u: string) => fetcher<AdbStatus>(u).catch(() => ({ connected: false, device: null })),
    { refreshInterval: 5000 },
  )

  // Detect false → true transitions and prompt confirmation
  const prevConnected = useRef<boolean | undefined>(undefined)
  useEffect(() => {
    const curr = adbStatus?.connected ?? false
    if (prevConnected.current === false && curr === true && adbStatus?.device) {
      setPendingDevice(adbStatus.device)
    }
    prevConnected.current = curr
  }, [adbStatus])

  const handleScriptComplete = useCallback((script: string) => {
    const label = script.replace('.py', '')
    toast(`Script "${label}" finished`, 'success')
    if (script === 'smart_compare.py' || script === 'generate_report.py') {
      setCompareRefreshSignal(n => n + 1)
    }
  }, [toast])

  const confirmDevice = () => {
    toast(`Connected: ${pendingDevice?.model}`, 'success')
    setPendingDevice(null)
  }

  const backendOffline = adbError !== undefined && adbStatus === undefined

  return (
    <div style={{ display: 'flex', width: '100%', height: '100vh', background: '#0D0D0D', overflow: 'hidden', flexDirection: 'column' }}>
      {/* Backend offline banner */}
      {backendOffline && (
        <div style={{
          background: '#1A0A0A', borderBottom: '1px solid rgba(226,45,68,0.3)',
          padding: '7px 20px', display: 'flex', alignItems: 'center', gap: 8,
          fontSize: 12, color: '#E22D44', flexShrink: 0,
        }}>
          <span style={{ fontSize: 14 }}>⚠</span>
          Backend offline — start the server with <code style={{ background: '#2A1010', padding: '1px 6px', borderRadius: 3, fontSize: 11 }}>python gui/backend/main.py</code>
        </div>
      )}

      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        <Sidebar
          active={view}
          onNav={setView}
          adbConnected={adbStatus?.connected ?? false}
          adbScanning={adbStatus === undefined && !adbError}
        />
        <main style={{ flex: 1, minWidth: 0, height: '100%', overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          {/* CompareView stays mounted always so range/report state persists across navigation */}
          <div style={{ display: view === 'compare' ? 'flex' : 'none', flex: 1, minHeight: 0, flexDirection: 'column' }}>
            <CompareView refreshSignal={compareRefreshSignal} />
          </div>
          {view === 'queue'    && <QueueView onDownloadComplete={() => toast('Download started', 'info')} />}
          {view === 'monitor'  && <MonitorView onScriptComplete={handleScriptComplete} />}
          {view === 'settings' && <SettingsView />}
        </main>
      </div>

      {pendingDevice && (
        <AdbConnectModal
          device={pendingDevice}
          onConfirm={confirmDevice}
          onDismiss={() => setPendingDevice(null)}
        />
      )}
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
