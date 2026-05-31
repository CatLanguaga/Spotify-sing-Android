import { normalizeLang } from '../api/langLabel'

const LANG_COLORS: Record<string, { color: string; bg: string }> = {
  JP: { color: '#FF6B9D', bg: 'rgba(255,107,157,0.10)' },
  KR: { color: '#A29BFE', bg: 'rgba(162,155,254,0.10)' },
  EN: { color: '#74B9FF', bg: 'rgba(116,185,255,0.10)' },
  ES: { color: '#FDCB6E', bg: 'rgba(253,203,110,0.10)' },
  CN: { color: '#FF7675', bg: 'rgba(255,118,117,0.10)' },
  RU: { color: '#55EFC4', bg: 'rgba(85,239,196,0.10)' },
  PT: { color: '#00B894', bg: 'rgba(0,184,148,0.10)' },
  IT: { color: '#E17055', bg: 'rgba(225,112,85,0.10)' },
  FR: { color: '#6C5CE7', bg: 'rgba(108,92,231,0.10)' },
  AR: { color: '#D63031', bg: 'rgba(214,48,49,0.10)' },
  OTHER: { color: '#7A8290', bg: 'rgba(122,130,144,0.10)' },
}

export function LangBadge({ lang }: { lang: string }) {
  const key = normalizeLang(lang)
  const { color, bg } = LANG_COLORS[key] ?? LANG_COLORS.OTHER
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
