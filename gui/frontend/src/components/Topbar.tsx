import { NavLink } from 'react-router-dom'

export function Topbar() {
  const scrollTo = (id: string) => {
    setTimeout(() => {
      document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }

  const nav = (
    <>
      <NavLink to="/" end>Inicio</NavLink>
      <a href="/#tutorial" onClick={() => scrollTo('tutorial')}>Cómo funciona</a>
      <a href="/#faq"      onClick={() => scrollTo('faq')}>FAQ</a>
      <NavLink to="/settings">Configuración</NavLink>
    </>
  )

  return (
    <>
      <header className="topbar">
        <NavLink className="brand" to="/" aria-label="Inicio">
          <span className="logo">♪</span>
          Spotify Sing
        </NavLink>
        <nav className="desktop-nav">{nav}</nav>
      </header>
      <nav className="mobile-nav" aria-label="Navegación principal">
        {nav}
      </nav>
    </>
  )
}
