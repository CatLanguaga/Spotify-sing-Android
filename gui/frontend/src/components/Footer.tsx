import { Link } from 'react-router-dom'
import useSWR from 'swr'
import { fetcher } from '../api/client'
import { usePreferences } from '../preferences'

type PublicConfig = {
  admin_footer_link?: boolean
}

export function Footer() {
  const { language, setLanguage, t } = usePreferences()
  // /config/public is unauthenticated + cheap; reuse SWR cache across the app.
  const { data: pub } = useSWR<PublicConfig>('/config/public', fetcher)
  const showAdminLink = pub?.admin_footer_link !== false

  return (
    <footer>
      <div className="footer-info">
        <div>© {new Date().getFullYear()} Mp3vine · Self-hosted</div>
        <div className="footer-disclaimer">{t('footerDisclaimer')}</div>
      </div>
      <div className="links">
        <Link to="/terms">{t('footerTerms')}</Link>
        <Link to="/privacy">{t('footerPrivacy')}</Link>
        {showAdminLink && (
          <Link to="/settings" className="footer-admin">{t('footerAdmin')}</Link>
        )}
        <a href="https://github.com" target="_blank" rel="noreferrer">GitHub</a>
        <a href="/docs" target="_blank" rel="noreferrer">API Docs</a>
        <label className="footer-lang">
          <span>{t('languageLabel')}</span>
          <select value={language} onChange={e => setLanguage(e.target.value === 'es' ? 'es' : 'en')}>
            <option value="en">EN</option>
            <option value="es">ES</option>
          </select>
        </label>
      </div>
    </footer>
  )
}
