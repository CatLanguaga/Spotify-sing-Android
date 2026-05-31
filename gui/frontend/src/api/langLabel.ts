/**
 * Shared language-label mapping. Backend returns full language names
 * ("Spanish", "Japanese/Chinese", …); the UI shows short codes.
 *
 * No blind default to English: anything we can't classify is 'OTHER'.
 */
export function normalizeLang(raw: string | null | undefined): string {
  if (!raw) return 'OTHER'
  const s = raw.toUpperCase()
  if (s.includes('JP') || s.includes('JAPAN')) return 'JP'
  if (s.includes('KR') || s.includes('KOREAN')) return 'KR'
  if (s.includes('CN') || s.includes('CHINESE')) return 'CN'
  if (s.includes('RU') || s.includes('RUSSIAN')) return 'RU'
  if (s.includes('AR') || s.includes('ARABIC')) return 'AR'
  if (s.includes('ES') || s.includes('SPANISH')) return 'ES'
  if (s.includes('PT') || s.includes('PORTUG')) return 'PT'
  if (s.includes('IT') || s.includes('ITALIAN')) return 'IT'
  if (s.includes('FR') || s.includes('FRENCH')) return 'FR'
  if (s.includes('EN') || s.includes('ENGLISH')) return 'EN'
  return 'OTHER'
}
