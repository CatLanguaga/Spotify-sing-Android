import { useEffect } from 'react'

type PageMeta = {
  title: string
  description: string
  path: string
}

const SITE_NAME = 'Spotify Sing'
const DEFAULT_DESCRIPTION = 'Pagina web para descargar musica de Spotify desde links de tracks, albumes y playlists como MP3, M4A u OPUS con metadata, filtros y descarga por lote.'

const META_BY_PATH: Record<string, PageMeta> = {
  '/': {
    title: 'Spotify Sing - descarga musica desde links de Spotify',
    description: DEFAULT_DESCRIPTION,
    path: '/',
  },
  '/how-it-works': {
    title: 'Como funciona Spotify Sing',
    description: 'Aprende como pegar un link de Spotify, resolver tracks, albumes o playlists, revisar limites y descargar audio en el formato que prefieras.',
    path: '/how-it-works',
  },
  '/faq': {
    title: 'Preguntas frecuentes de Spotify Sing',
    description: 'Respuestas sobre credenciales de Spotify, fuentes de audio, formatos, limites de playlist, idioma, uso movil y fallos de descarga.',
    path: '/faq',
  },
  '/settings': {
    title: 'Configuracion de Spotify Sing',
    description: 'Configura credenciales de Spotify, formato por defecto, calidad y revision manual de fuentes de YouTube.',
    path: '/settings',
  },
}

function absoluteUrl(path: string): string {
  return new URL(path, window.location.origin).toString()
}

function upsertMeta(selector: string, attrs: Record<string, string>) {
  let el = document.head.querySelector<HTMLMetaElement>(selector)
  if (!el) {
    el = document.createElement('meta')
    document.head.appendChild(el)
  }
  Object.entries(attrs).forEach(([key, value]) => el?.setAttribute(key, value))
}

function upsertLink(selector: string, attrs: Record<string, string>) {
  let el = document.head.querySelector<HTMLLinkElement>(selector)
  if (!el) {
    el = document.createElement('link')
    document.head.appendChild(el)
  }
  Object.entries(attrs).forEach(([key, value]) => el?.setAttribute(key, value))
}

function upsertJsonLd(id: string, data: unknown) {
  let el = document.getElementById(id) as HTMLScriptElement | null
  if (!el) {
    el = document.createElement('script')
    el.id = id
    el.type = 'application/ld+json'
    document.head.appendChild(el)
  }
  el.textContent = JSON.stringify(data)
}

function webAppSchema(url: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: SITE_NAME,
    url,
    applicationCategory: 'MultimediaApplication',
    operatingSystem: 'Web',
    description: DEFAULT_DESCRIPTION,
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
    featureList: [
      'Resolver tracks, albumes y playlists de Spotify',
      'Descargar audio en MP3, M4A u OPUS',
      'Embeder metadata y portada de Spotify en los archivos',
      'Filtrar playlists por idioma',
      'Descarga por lotes y ZIP',
    ],
  }
}

function webPageSchema(url: string, title: string, description: string) {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebPage',
    name: title,
    url,
    description,
    isPartOf: {
      '@type': 'WebSite',
      name: SITE_NAME,
      url: absoluteUrl('/'),
    },
    about: {
      '@type': 'SoftwareApplication',
      name: SITE_NAME,
      applicationCategory: 'MultimediaApplication',
      operatingSystem: 'Web',
    },
    hasPart: [
      {
        '@type': 'WebPageElement',
        name: 'Que es esta pagina',
        url: `${absoluteUrl('/')}#que-es`,
        description: 'Definicion de Spotify Sing como pagina auto-hospedable para convertir links de Spotify en archivos de audio descargables.',
      },
      {
        '@type': 'WebPageElement',
        name: 'Caracteristicas',
        url: `${absoluteUrl('/')}#caracteristicas`,
        description: 'Resumen de links soportados, metadata, formatos, filtros, playlists grandes y descarga por lote.',
      },
      {
        '@type': 'WebPageElement',
        name: 'Tutorial',
        url: `${absoluteUrl('/')}#tutorial-uso`,
        description: 'Pasos para copiar un enlace de Spotify, pegarlo en el buscador, elegir formato y descargar.',
      },
      {
        '@type': 'WebPageElement',
        name: 'Limites',
        url: `${absoluteUrl('/')}#limites`,
        description: 'Notas sobre metadata de Spotify, fuentes publicas de audio, paginacion, credenciales y calidad final.',
      },
      {
        '@type': 'WebPageElement',
        name: 'Preguntas frecuentes',
        url: `${absoluteUrl('/')}#faq`,
        description: 'Respuestas sobre cuenta de Spotify, fuente de audio, fallos de match, playlists grandes, idioma, formato y uso movil.',
      },
    ],
  }
}

export function pageMetaFor(pathname: string): PageMeta {
  return META_BY_PATH[pathname] ?? META_BY_PATH['/']
}

export function usePageSeo(pathname: string) {
  useEffect(() => {
    const meta = pageMetaFor(pathname)
    const url = absoluteUrl(meta.path)
    document.title = meta.title

    upsertMeta('meta[name="description"]', { name: 'description', content: meta.description })
    upsertMeta('meta[name="robots"]', { name: 'robots', content: 'index,follow' })
    upsertMeta('meta[property="og:title"]', { property: 'og:title', content: meta.title })
    upsertMeta('meta[property="og:description"]', { property: 'og:description', content: meta.description })
    upsertMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' })
    upsertMeta('meta[property="og:url"]', { property: 'og:url', content: url })
    upsertMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: SITE_NAME })
    upsertMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary' })
    upsertMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: meta.title })
    upsertMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: meta.description })
    upsertLink('link[rel="canonical"]', { rel: 'canonical', href: url })
    upsertJsonLd('schema-webapp', webAppSchema(absoluteUrl('/')))
    upsertJsonLd('schema-webpage', webPageSchema(url, meta.title, meta.description))
  }, [pathname])
}
