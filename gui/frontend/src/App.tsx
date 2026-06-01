import { lazy, Suspense } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Topbar } from './components/Topbar'
import { Footer } from './components/Footer'
import { ToastProvider } from './components/Toast'
import { LandingView } from './views/LandingView'
import { usePageSeo } from './seo'

const SettingsView = lazy(() =>
  import('./views/SettingsView').then(module => ({ default: module.SettingsView })),
)

function AppInner() {
  const location = useLocation()
  usePageSeo(location.pathname)

  return (
    <>
      <a className="skip-link" href="#main-content">Saltar al contenido</a>
      <Topbar />
      <main id="main-content" tabIndex={-1}>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/"             element={<LandingView />} />
            <Route path="/how-it-works" element={<LandingView focusSection="tutorial" />} />
            <Route path="/faq"          element={<LandingView focusSection="faq" />} />
            <Route path="/app"          element={<Navigate to="/" replace />} />
            <Route path="/settings"     element={<SettingsView />} />
            <Route path="*"             element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
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
