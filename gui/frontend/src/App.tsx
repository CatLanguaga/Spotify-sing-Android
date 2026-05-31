import { Routes, Route, Navigate } from 'react-router-dom'
import { Topbar } from './components/Topbar'
import { Footer } from './components/Footer'
import { ToastProvider } from './components/Toast'
import { LandingView } from './views/LandingView'
import { SettingsView } from './views/SettingsView'

function AppInner() {
  return (
    <>
      <Topbar />
      <main>
        <Routes>
          <Route path="/"         element={<LandingView />} />
          <Route path="/app"      element={<Navigate to="/" replace />} />
          <Route path="/settings" element={<SettingsView />} />
          <Route path="*"         element={<Navigate to="/" replace />} />
        </Routes>
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
