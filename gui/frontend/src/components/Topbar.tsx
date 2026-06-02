import { NavLink } from 'react-router-dom'
import useSWR from 'swr'
import { fetcher } from '../api/client'
import { usePreferences } from '../preferences'

type AdminSession = {
  authenticated: boolean
}

export function Topbar() {
  const { data: session } = useSWR<AdminSession>('/admin/session', fetcher)
  const { t } = usePreferences()
  const isAdmin = !!session?.authenticated

  const nav = (
    <>
      <NavLink to="/" end>{t('home')}</NavLink>
      <NavLink to="/how-it-works">{t('howItWorks')}</NavLink>
      <NavLink to="/faq">{t('faq')}</NavLink>
      {isAdmin && <NavLink to="/settings">{t('settings')}</NavLink>}
    </>
  )

  return (
    <>
      <header className="topbar">
        <NavLink className="brand" to="/">
          <span className="logo" aria-hidden="true">♪</span>
          Mp3vine
        </NavLink>
        <nav className="desktop-nav" aria-label="Primary navigation">{nav}</nav>
      </header>
      <nav className="mobile-nav" aria-label="Primary navigation">
        {nav}
      </nav>
    </>
  )
}
