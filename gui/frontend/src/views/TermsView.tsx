import { usePreferences } from '../preferences'

export function TermsView() {
  const { language } = usePreferences()
  return (
    <div className="legal-wrap">
      {language === 'es' ? <TermsES /> : <TermsEN />}
    </div>
  )
}

function TermsEN() {
  return (
    <article>
      <h1>Terms of Service</h1>
      <p className="legal-meta">Last updated: June 2026</p>

      <h2>1. About this service</h2>
      <p>
        Mp3vine is a self-hosted tool that reads public metadata from
        Spotify links (tracks, albums, playlists, shortlinks) and helps the
        user save audio files to their own device using publicly available
        sources. The tool is provided free of charge and is intended for
        personal, non-commercial use.
      </p>

      <h2>2. Not affiliated with Spotify</h2>
      <p>
        Mp3vine is an independent project. It is not affiliated with,
        endorsed by, sponsored by, or otherwise connected to Spotify AB or any
        of its subsidiaries. &quot;Spotify&quot; is a trademark of Spotify AB.
        All track titles, artist names, cover art, and other metadata remain
        the property of their respective owners.
      </p>

      <h2>3. User responsibility</h2>
      <p>
        You are solely responsible for the way you use this tool. Before
        downloading any content you must make sure that doing so is allowed by:
      </p>
      <ul>
        <li>the copyright laws that apply where you live;</li>
        <li>the terms of service of Spotify and of the source platform; and</li>
        <li>any license attached to the specific work.</li>
      </ul>
      <p>
        Downloading copyrighted material that you do not own and that is not
        covered by a personal-use exception may be illegal. Do not use this
        tool to redistribute, sell, broadcast, or otherwise commercially
        exploit protected content.
      </p>

      <h2>4. No warranty</h2>
      <p>
        The service is provided &quot;as is&quot;, without warranty of any kind,
        express or implied. We do not guarantee that the tool will be
        available, error-free, or that the resulting audio matches the original
        recording in quality, length, or metadata. Use of the service is at
        your own risk.
      </p>

      <h2>5. Limitation of liability</h2>
      <p>
        To the maximum extent permitted by law, the operators of Mp3vine
        shall not be liable for any direct, indirect, incidental, special, or
        consequential damages arising out of the use of, or inability to use,
        the service.
      </p>

      <h2>6. Takedown requests</h2>
      <p>
        If you believe that the tool is being used to infringe your rights,
        contact the operator of the instance you are using. This project does
        not host audio files; it streams them through the user&apos;s browser
        from third-party sources, which are responsible for the content they
        publish.
      </p>

      <h2>7. Changes</h2>
      <p>
        These terms may change without notice. The version published on this
        page is the one currently in force.
      </p>
    </article>
  )
}

function TermsES() {
  return (
    <article>
      <h1>Términos de servicio</h1>
      <p className="legal-meta">Última actualización: junio de 2026</p>

      <h2>1. Sobre este servicio</h2>
      <p>
        Mp3vine es una herramienta autoalojada que lee metadatos públicos
        de enlaces de Spotify (canciones, álbumes, playlists, shortlinks) y
        ayuda al usuario a guardar archivos de audio en su propio dispositivo
        usando fuentes públicas. La herramienta se ofrece de forma gratuita y
        está pensada para uso personal y no comercial.
      </p>

      <h2>2. No afiliada a Spotify</h2>
      <p>
        Mp3vine es un proyecto independiente. No está afiliada, avalada,
        patrocinada ni conectada de ningún otro modo con Spotify AB o
        cualquiera de sus filiales. &quot;Spotify&quot; es una marca registrada
        de Spotify AB. Los títulos, nombres de artistas, portadas y demás
        metadatos siguen siendo propiedad de sus respectivos titulares.
      </p>

      <h2>3. Responsabilidad del usuario</h2>
      <p>
        Eres el único responsable del uso que hagas de esta herramienta. Antes
        de descargar cualquier contenido debes asegurarte de que esa descarga
        está permitida por:
      </p>
      <ul>
        <li>la legislación sobre derechos de autor del país donde te encuentres;</li>
        <li>los términos de servicio de Spotify y de la plataforma de origen; y</li>
        <li>la licencia concreta de la obra.</li>
      </ul>
      <p>
        Descargar material protegido por derechos de autor que no te pertenece y
        que no esté amparado por una excepción de uso personal puede ser
        ilegal. No uses esta herramienta para redistribuir, vender, emitir o
        explotar comercialmente contenido protegido.
      </p>

      <h2>4. Sin garantías</h2>
      <p>
        El servicio se ofrece &quot;tal cual&quot;, sin ninguna garantía
        expresa o implícita. No garantizamos que la herramienta esté siempre
        disponible, que esté libre de errores, ni que el audio resultante
        coincida con la grabación original en calidad, duración o metadatos.
        El uso del servicio es bajo tu propio riesgo.
      </p>

      <h2>5. Limitación de responsabilidad</h2>
      <p>
        En la máxima medida permitida por la ley, los operadores de Spotify
        Sing no serán responsables por daños directos, indirectos, incidentales,
        especiales o consecuentes derivados del uso o de la imposibilidad de
        usar el servicio.
      </p>

      <h2>6. Solicitudes de retirada</h2>
      <p>
        Si crees que la herramienta se está usando para infringir tus derechos,
        contacta al operador de la instancia que estés utilizando. Este
        proyecto no aloja archivos de audio; los transmite a través del
        navegador del usuario desde fuentes de terceros, que son las
        responsables del contenido que publican.
      </p>

      <h2>7. Cambios</h2>
      <p>
        Estos términos pueden cambiar sin previo aviso. La versión publicada en
        esta página es la que está vigente.
      </p>
    </article>
  )
}
