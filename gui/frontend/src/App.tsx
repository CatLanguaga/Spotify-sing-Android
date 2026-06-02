import { lazy, Suspense } from 'react'
import { useEffect } from 'react'
import { Routes, Route, Navigate, useLocation } from 'react-router-dom'
import { Topbar } from './components/Topbar'
import { Footer } from './components/Footer'
import { ToastProvider } from './components/Toast'
import { LandingView } from './views/LandingView'
import { usePageSeo } from './seo'
import { usePreferences } from './preferences'

const SettingsView = lazy(() =>
  import('./views/SettingsView').then(module => ({ default: module.SettingsView })),
)
const TermsView = lazy(() =>
  import('./views/TermsView').then(module => ({ default: module.TermsView })),
)
const PrivacyView = lazy(() =>
  import('./views/PrivacyView').then(module => ({ default: module.PrivacyView })),
)

function AppInner() {
  const location = useLocation()
  const { language, t } = usePreferences()
  usePageSeo(location.pathname, language)

  useEffect(() => {
    const isTypingTarget = (target: EventTarget | null) => {
      const el = target as HTMLElement | null
      if (!el) return false
      return ['INPUT', 'TEXTAREA', 'SELECT'].includes(el.tagName) || el.isContentEditable
    }

    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'v') {
        const input = document.getElementById('spotify-url') as HTMLInputElement | null
        input?.focus()
        return
      }
      if (!event.metaKey && !event.ctrlKey && !event.altKey && event.key.toLowerCase() === 'd') {
        if (isTypingTarget(event.target)) return
        window.dispatchEvent(new CustomEvent('mp3vine-download-all'))
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [])

  return (
    <>
      <a className="skip-link" href="#main-content">{t('skipToContent')}</a>
      <Topbar />
      <main id="main-content" tabIndex={-1}>
        <Suspense fallback={null}>
          <Routes>
            <Route path="/"             element={<LandingView />} />
            <Route path="/how-it-works" element={<LandingView focusSection="tutorial" />} />
            <Route path="/faq"          element={<LandingView focusSection="faq" />} />
            <Route path="/app"          element={<Navigate to="/" replace />} />
            <Route path="/settings"     element={<SettingsView />} />
            <Route path="/terms"        element={<TermsView />} />
            <Route path="/privacy"      element={<PrivacyView />} />
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
