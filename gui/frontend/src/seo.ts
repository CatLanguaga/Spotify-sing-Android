import { useEffect } from 'react'

type Language = 'en' | 'es'

type PageMeta = {
  title: string
  description: string
  path: string
}

const SITE_NAME = 'Mp3vine'

const DEFAULT_DESCRIPTION: Record<Language, string> = {
  en: 'A self-hosted web page for downloading music from Spotify track, album, playlist, and short links as MP3, M4A, or OPUS with metadata, filters, and batch downloads.',
  es: 'Una pagina web autoalojada para descargar musica de Spotify desde links de track, album, playlist y shortlinks como MP3, M4A u OPUS con metadatos, filtros y descargas por lote.',
}

const META: Record<Language, Record<string, PageMeta>> = {
  en: {
    '/': {
      title: 'Mp3vine - Spotify to MP3 downloader',
      description: DEFAULT_DESCRIPTION.en,
      path: '/',
    },
    '/how-it-works': {
      title: 'How Mp3vine works',
      description: 'Learn how to paste a Spotify link, resolve tracks, albums, or playlists, review limits, and download audio in your preferred format.',
      path: '/how-it-works',
    },
    '/faq': {
      title: 'Mp3vine FAQ',
      description: 'Answers about Spotify credentials, audio sources, formats, playlist limits, language detection, mobile use, and download failures.',
      path: '/faq',
    },
    '/settings': {
      title: 'Mp3vine admin settings',
      description: 'Admin-only settings for Spotify credentials, default format, quality, and manual YouTube source review.',
      path: '/settings',
    },
    '/terms': {
      title: 'Mp3vine terms of service',
      description: 'Terms of service for the Mp3vine self-hosted tool: scope, no Spotify affiliation, user responsibility, warranty, and takedown.',
      path: '/terms',
    },
    '/privacy': {
      title: 'Mp3vine privacy policy',
      description: 'Privacy policy for Mp3vine: minimal data, no third-party tracking, admin cookie, temporary downloads, and third-party services.',
      path: '/privacy',
    },
  },
  es: {
    '/': {
      title: 'Mp3vine - descargar MP3 desde Spotify',
      description: DEFAULT_DESCRIPTION.es,
      path: '/',
    },
    '/how-it-works': {
      title: 'Como funciona Mp3vine',
      description: 'Aprende a pegar un link de Spotify, resolver tracks, albumes o playlists, revisar limites y descargar audio en el formato que prefieras.',
      path: '/how-it-works',
    },
    '/faq': {
      title: 'FAQ de Mp3vine',
      description: 'Respuestas sobre credenciales de Spotify, fuentes de audio, formatos, limites de playlists, deteccion de idioma, uso movil y fallos de descarga.',
      path: '/faq',
    },
    '/settings': {
      title: 'Configuracion de administrador de Mp3vine',
      description: 'Configuracion solo para administradores: credenciales de Spotify, formato y calidad por defecto y revision manual de fuente YouTube.',
      path: '/settings',
    },
    '/terms': {
      title: 'Terminos de servicio de Mp3vine',
      description: 'Terminos de servicio de la herramienta autoalojada Mp3vine: alcance, sin afiliacion con Spotify, responsabilidad del usuario, garantia y takedown.',
      path: '/terms',
    },
    '/privacy': {
      title: 'Politica de privacidad de Mp3vine',
      description: 'Politica de privacidad de Mp3vine: datos minimos, sin tracking de terceros, cookie de admin, descargas temporales y servicios de terceros.',
      path: '/privacy',
    },
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

function webAppSchema(url: string, language: Language) {
  return {
    '@context': 'https://schema.org',
    '@type': 'WebApplication',
    name: SITE_NAME,
    url,
    applicationCategory: 'MultimediaApplication',
    operatingSystem: 'Web',
    description: DEFAULT_DESCRIPTION[language],
    offers: {
      '@type': 'Offer',
      price: '0',
      priceCurrency: 'USD',
    },
    featureList: language === 'es' ? [
      'Resolver tracks, albumes, playlists y shortlinks de Spotify',
      'Descargar audio como MP3, M4A u OPUS',
      'Embeber metadatos y portada de Spotify en los archivos',
      'Filtrar playlists por idioma detectado',
      'Descargas por lote y exportacion ZIP',
    ] : [
      'Resolve Spotify tracks, albums, playlists, and shortlinks',
      'Download audio as MP3, M4A, or OPUS',
      'Embed Spotify metadata and cover art in files',
      'Filter playlists by detected language',
      'Batch downloads and ZIP export',
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
  }
}

export function pageMetaFor(pathname: string, language: Language = 'en'): PageMeta {
  const set = META[language] ?? META.en
  return set[pathname] ?? set['/']
}

export function usePageSeo(pathname: string, language: Language = 'en') {
  useEffect(() => {
    const meta = pageMetaFor(pathname, language)
    const url = absoluteUrl(meta.path)
    document.title = meta.title

    upsertMeta('meta[name="description"]', { name: 'description', content: meta.description })
    upsertMeta('meta[name="robots"]', { name: 'robots', content: 'index,follow' })
    upsertMeta('meta[property="og:title"]', { property: 'og:title', content: meta.title })
    upsertMeta('meta[property="og:description"]', { property: 'og:description', content: meta.description })
    upsertMeta('meta[property="og:type"]', { property: 'og:type', content: 'website' })
    upsertMeta('meta[property="og:url"]', { property: 'og:url', content: url })
    upsertMeta('meta[property="og:site_name"]', { property: 'og:site_name', content: SITE_NAME })
    upsertMeta('meta[property="og:locale"]', { property: 'og:locale', content: language === 'es' ? 'es_ES' : 'en_US' })
    upsertMeta('meta[name="twitter:card"]', { name: 'twitter:card', content: 'summary' })
    upsertMeta('meta[name="twitter:title"]', { name: 'twitter:title', content: meta.title })
    upsertMeta('meta[name="twitter:description"]', { name: 'twitter:description', content: meta.description })
    upsertLink('link[rel="canonical"]', { rel: 'canonical', href: url })
    upsertJsonLd('schema-webapp', webAppSchema(absoluteUrl('/'), language))
    upsertJsonLd('schema-webpage', webPageSchema(url, meta.title, meta.description))
  }, [pathname, language])
}
