const LANG_COLORS: Record<string, { color: string; bg: string }> = {
  JP: { color: '#FF6B9D', bg: 'rgba(255,107,157,0.10)' },
  KR: { color: '#A29BFE', bg: 'rgba(162,155,254,0.10)' },
  EN: { color: '#74B9FF', bg: 'rgba(116,185,255,0.10)' },
  ES: { color: '#FDCB6E', bg: 'rgba(253,203,110,0.10)' },
  CN: { color: '#FF7675', bg: 'rgba(255,118,117,0.10)' },
  RU: { color: '#55EFC4', bg: 'rgba(85,239,196,0.10)' },
}

function detectLang(raw: string): string {
  const s = raw.toUpperCase()
  if (s.includes('JAPANESE') || s.includes('JP')) return 'JP'
  if (s.includes('KOREAN') || s.includes('KR')) return 'KR'
  if (s.includes('ENGLISH') || s.includes('EN')) return 'EN'
  if (s.includes('SPANISH') || s.includes('ES')) return 'ES'
  if (s.includes('CHINESE') || s.includes('CN')) return 'CN'
  if (s.includes('RUSSIAN') || s.includes('RU')) return 'RU'
  return 'EN'
}

export function LangBadge({ lang }: { lang: string }) {
  const key = detectLang(lang)
  const { color, bg } = LANG_COLORS[key] ?? LANG_COLORS.EN
  return (
    <span style={{
      color, background: bg,
      border: `1px solid ${color}44`,
      borderRadius: 3, padding: '1px 5px',
      fontSize: 10, fontWeight: 700,
      fontFamily: 'JetBrains Mono, monospace',
      letterSpacing: '0.04em',
    }}>
      {key}
    </span>
  )
}
