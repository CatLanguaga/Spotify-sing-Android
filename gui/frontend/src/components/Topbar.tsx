type View = 'home' | 'settings'

interface Props {
  view: View
  onNav: (v: View) => void
}

export function Topbar({ onNav }: Props) {
  const scrollTo = (id: string) => {
    onNav('home')
    setTimeout(() => {
      const el = document.getElementById(id)
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }

  const nav = (
    <>
      <button onClick={() => onNav('home')}>Inicio</button>
      <button onClick={() => scrollTo('tutorial')}>Como funciona</button>
      <button onClick={() => scrollTo('faq')}>FAQ</button>
      <button onClick={() => onNav('settings')}>Configuracion</button>
    </>
  )

  return (
    <>
      <header className="topbar">
        <button className="brand" onClick={() => onNav('home')} aria-label="Inicio">
          <span className="logo">♪</span>
          Spotify Sing
        </button>
        <nav className="desktop-nav">{nav}</nav>
      </header>
      <nav className="mobile-nav" aria-label="Navegacion principal">
        {nav}
      </nav>
    </>
  )
}
