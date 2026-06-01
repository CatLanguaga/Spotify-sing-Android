import { NavLink } from 'react-router-dom'

export function Topbar() {
  const nav = (
    <>
      <NavLink to="/" end>Inicio</NavLink>
      <NavLink to="/how-it-works">Como funciona</NavLink>
      <NavLink to="/faq">FAQ</NavLink>
      <NavLink to="/settings">Configuracion</NavLink>
    </>
  )

  return (
    <>
      <header className="topbar">
        <NavLink className="brand" to="/">
          <span className="logo" aria-hidden="true">♪</span>
          Spotify Sing
        </NavLink>
        <nav className="desktop-nav" aria-label="Navegacion principal">{nav}</nav>
      </header>
      <nav className="mobile-nav" aria-label="Navegacion principal">
        {nav}
      </nav>
    </>
  )
}
