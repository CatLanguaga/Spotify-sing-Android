const features = [
  {
    title: 'Links de Spotify',
    body: 'Acepta canciones, albumes y playlists completas desde open.spotify.com. La app identifica el tipo de enlace y carga los datos principales antes de descargar.',
  },
  {
    title: 'Metadata completa',
    body: 'Usa Spotify para nombre, artista, album, portada, duracion y orden de tracks. Esa informacion se embebe en el archivo cuando el formato lo permite.',
  },
  {
    title: 'Formatos flexibles',
    body: 'Puedes elegir MP3, M4A u OPUS y ajustar la calidad entre 128, 192 y 320 kbps segun compatibilidad, tamano o eficiencia.',
  },
  {
    title: 'Playlists grandes',
    body: 'Las listas se muestran en paginas de 50 canciones para que el navegador y el backend sigan respondiendo bien incluso con colecciones largas.',
  },
  {
    title: 'Filtros utiles',
    body: 'Incluye busqueda por texto y filtro por idioma para revisar mejor canciones en espanol, ingles, japones, coreano y otros grupos detectados.',
  },
  {
    title: 'Descarga individual o lote',
    body: 'Puedes descargar una cancion suelta, toda la pagina visible o generar un ZIP para manejar lotes sin perder los fallos individuales.',
  },
]

const limits = [
  'Spotify aporta la metadata; el audio no sale directamente de Spotify.',
  'La disponibilidad depende de fuentes publicas encontradas en YouTube.',
  'Algunas coincidencias pueden fallar por region, duracion distinta, remixes, covers o videos mal titulados.',
  'Las playlists se revisan en bloques de 50 canciones por pagina para mantener estable la experiencia.',
  'El servidor necesita credenciales gratuitas de Spotify API para resolver albumes, playlists y tracks.',
  'La calidad final tambien depende de la fuente original, no solo del bitrate elegido.',
]

const sectionLinks = [
  { href: '#que-es', label: 'Que es' },
  { href: '#caracteristicas', label: 'Caracteristicas' },
  { href: '#tutorial-uso', label: 'Tutorial' },
  { href: '#limites', label: 'Limites' },
  { href: '#faq', label: 'FAQ' },
]

export function TutorialSection() {
  return (
    <section className="tutorial" id="tutorial">
      <div className="section-title">
        <div className="kicker">Guia de uso</div>
        <h2>Descargar musica de Spotify con mas contexto y control</h2>
      </div>

      <nav className="section-jump" aria-label="Secciones de la guia">
        {sectionLinks.map((link) => (
          <a href={link.href} key={link.href}>{link.label}</a>
        ))}
      </nav>

      <section className="info-block about-page" id="que-es" aria-labelledby="que-es-title">
        <div>
          <div className="kicker">Que es esta pagina</div>
          <h3 id="que-es-title">Una herramienta web para convertir links de Spotify en archivos de audio descargables</h3>
        </div>
        <div className="info-copy">
          <p>
            Spotify Sing es una pagina auto-hospedable para pegar un enlace de Spotify, resolver sus canciones y descargar audio
            en MP3, M4A u OPUS desde el navegador. Sirve para trabajar con tracks individuales, albumes y playlists sin instalar
            una app de escritorio ni conectar un telefono por cable.
          </p>
          <p>
            La pagina usa Spotify como fuente de informacion musical: titulo, artista, album, portada, duracion y orden de la
            playlist. Despues busca una fuente de audio compatible, normalmente en YouTube, y prepara el archivo con metadata para
            que sea facil de organizar en tu reproductor.
          </p>
        </div>
      </section>

      <section className="info-block" id="caracteristicas" aria-labelledby="features-title">
        <div className="section-subtitle">
          <div className="kicker">Caracteristicas</div>
          <h3 id="features-title">Lo que puedes hacer aqui</h3>
        </div>

        <div className="feature-grid">
          {features.map((feature) => (
            <article className="feature-card" key={feature.title}>
              <h4>{feature.title}</h4>
              <p>{feature.body}</p>
            </article>
          ))}
        </div>
      </section>

      <section className="info-block" id="tutorial-uso" aria-labelledby="tutorial-title">
        <div className="section-subtitle">
          <div className="kicker">Tutorial rapido</div>
          <h3 id="tutorial-title">Como usar Spotify Sing</h3>
        </div>

        <div className="steps">
          <div className="step">
            <div className="num">1</div>
            <h4>Copia un link de Spotify</h4>
            <p>Abre Spotify web o la app, busca una cancion, album o playlist, y usa Compartir para copiar el enlace.</p>
            <div className="demo-line">https://<span className="hl">open.spotify.com/playlist/</span>37i9dQZF...</div>
          </div>
          <div className="step">
            <div className="num">2</div>
            <h4>Pegalo en el buscador</h4>
            <p>La pagina detecta el tipo de enlace, carga portada y tracks, y te deja filtrar por texto o idioma antes de descargar.</p>
            <div className="demo-line">Track / Album / <span className="hl">Playlist OK</span></div>
          </div>
          <div className="step">
            <div className="num">3</div>
            <h4>Elige formato y descarga</h4>
            <p>Selecciona MP3, M4A u OPUS, define la calidad y descarga una cancion, la pagina visible o un ZIP del lote.</p>
            <div className="demo-line"><span className="hl">Download</span> mp3 / 320 kbps / metadata incluida</div>
          </div>
        </div>
      </section>

      <section className="info-block limits-block" id="limites" aria-labelledby="limits-title">
        <div className="section-subtitle">
          <div className="kicker">Consciencia de limites</div>
          <h3 id="limits-title">Lo que conviene saber antes de descargar</h3>
        </div>

        <ul className="limit-list">
          {limits.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </section>

      <div className="faq" id="faq">
        <h3>Preguntas frecuentes</h3>

        <details open>
          <summary>Necesito una cuenta de Spotify?</summary>
          <p>No necesitas iniciar sesion como usuario para pegar links. El servidor si necesita credenciales gratuitas de Spotify API configuradas por quien hospeda la pagina.</p>
        </details>

        <details>
          <summary>De donde sale el audio?</summary>
          <p>Spotify se usa para metadata y estructura. El audio se resuelve desde fuentes publicas, normalmente YouTube, usando busquedas y validaciones de artista, titulo y duracion.</p>
        </details>

        <details>
          <summary>Por que una cancion puede salir con otro audio?</summary>
          <p>Puede pasar si YouTube devuelve un cover, remix, video en vivo o resultado mal titulado. Para esos casos existe revision manual y reintento con otra fuente.</p>
        </details>

        <details>
          <summary>Como funcionan las playlists grandes?</summary>
          <p>La pagina carga 50 canciones por pagina. Puedes saltar a una pagina concreta, filtrar lo visible y descargar por partes para evitar saturar el navegador o el servidor.</p>
        </details>

        <details>
          <summary>Que significa la categoria Otros en idioma?</summary>
          <p>Otros agrupa canciones con texto muy corto, idioma mixto, instrumental, nombres propios o senales insuficientes para clasificar con confianza.</p>
        </details>

        <details>
          <summary>Que formato y calidad debo elegir?</summary>
          <p>MP3 a 320 kbps es lo mas compatible. M4A suele equilibrar calidad y tamano. OPUS es eficiente, pero funciona mejor en reproductores modernos.</p>
        </details>

        <details>
          <summary>Puedo usarla desde el celular?</summary>
          <p>Si. Abre la pagina en el navegador movil, comparte o pega el link de Spotify y descarga el archivo directo al dispositivo.</p>
        </details>
      </div>
    </section>
  )
}
