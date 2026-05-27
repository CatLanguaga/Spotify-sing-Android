import { useState } from 'react'
import { Topbar } from './components/Topbar'
import { Footer } from './components/Footer'
import { ToastProvider } from './components/Toast'
import { HomeView } from './views/HomeView'
import { SettingsView } from './views/SettingsView'

type View = 'home' | 'settings'

function AppInner() {
  const [view, setView] = useState<View>('home')

  return (
    <>
      <Topbar view={view} onNav={setView} />
      <main>
        {view === 'home'     && <HomeView />}
        {view === 'settings' && <SettingsView />}
      </main>
      <Footer />
    </>
  )
}

export default function App() {
  return (
    <ToastProvider>
      <AppInner />
    </ToastProvider>
  )
}
