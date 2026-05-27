export function TutorialSection() {
  return (
    <section className="tutorial" id="tutorial">
      <div className="section-title">
        <div className="kicker">Cómo funciona</div>
        <h2>3 pasos, sin instalar nada</h2>
      </div>

      <div className="steps">
        <div className="step">
          <div className="num">1</div>
          <h3>Copia un link de Spotify</h3>
          <p>Abre Spotify (web o app), encuentra el track, álbum o playlist que quieras, dale a "Compartir → Copiar enlace".</p>
          <div className="demo-line">https://<span className="hl">open.spotify.com/playlist/</span>37i9dQZF...</div>
        </div>
        <div className="step">
          <div className="num">2</div>
          <h3>Pégalo arriba</h3>
          <p>Pega el link en el cuadro principal. La app detecta automáticamente si es un track, un álbum o una playlist completa.</p>
          <div className="demo-line">Track · Álbum · <span className="hl">Playlist ✓</span></div>
        </div>
        <div className="step">
          <div className="num">3</div>
          <h3>Descarga al instante</h3>
          <p>Elige formato (mp3/m4a/opus) y calidad (320/192/128 kbps). Dale a "Descargar todo" o descarga canciones sueltas. Los archivos llegan directo a tu carpeta de descargas.</p>
          <div className="demo-line"><span className="hl">⬇</span> mp3 · 320 kbps · ~21 MB</div>
        </div>
      </div>

      <div className="faq" id="faq">
        <h3>Preguntas frecuentes</h3>

        <details open>
          <summary>¿Necesito una cuenta de Spotify?</summary>
          <p>No para usar la app — pero el servidor sí necesita credenciales de la API de Spotify (gratis) configuradas por quien hospeda la app. Si tú la auto-hospedas, créalas en developer.spotify.com/dashboard. Si usas una instancia pública, ya están configuradas.</p>
        </details>

        <details>
          <summary>¿De dónde sale el audio?</summary>
          <p>La app obtiene metadata (título, artista, álbum, cover) desde la API oficial de Spotify, y luego busca el audio en YouTube usando el match más fiel posible. Por eso el resultado depende de qué tan disponible esté el track en YouTube.</p>
        </details>

        <details>
          <summary>¿Qué formato y calidad debo elegir?</summary>
          <p><strong>mp3 a 320 kbps</strong> es la opción más compatible con cualquier reproductor o coche. <strong>m4a</strong> tiene mejor relación calidad/tamaño. <strong>opus</strong> es ultra eficiente pero requiere reproductores modernos.</p>
        </details>

        <details>
          <summary>¿Hay límite de canciones por playlist?</summary>
          <p>Sí: 50 canciones por consulta. Para playlists más grandes, la app paginará en bloques (próximamente con un slider).</p>
        </details>

        <details>
          <summary>¿Es legal?</summary>
          <p>El uso para copia personal de música que ya posees o tienes derecho a escuchar varía por país. Esta herramienta es de uso bajo tu propia responsabilidad. No la uses para redistribuir contenido protegido.</p>
        </details>

        <details>
          <summary>¿Qué pasa si un track falla?</summary>
          <p>El botón cambia a rojo y aparece la opción "Reintentar". Suele ser por restricciones regionales en YouTube — puedes reintentar o buscar manualmente otra fuente.</p>
        </details>
      </div>
    </section>
  )
}
