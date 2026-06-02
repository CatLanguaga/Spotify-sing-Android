import { usePreferences } from '../preferences'

export function TutorialSection() {
  const { t } = usePreferences()

  const features = [
    { title: t('featureSpotifyLinksTitle'), body: t('featureSpotifyLinksBody') },
    { title: t('featureMetadataTitle'),     body: t('featureMetadataBody') },
    { title: t('featureFormatsTitle'),      body: t('featureFormatsBody') },
    { title: t('featureLargeTitle'),        body: t('featureLargeBody') },
    { title: t('featureFiltersTitle'),      body: t('featureFiltersBody') },
    { title: t('featureBatchTitle'),        body: t('featureBatchBody') },
  ]

  const limits = [t('limit1'), t('limit2'), t('limit3'), t('limit4'), t('limit5'), t('limit6')]

  const sectionLinks = [
    { href: '#what-is-it',  label: t('sectionWhatItIs') },
    { href: '#features',    label: t('sectionFeatures') },
    { href: '#usage-guide', label: t('sectionGuide') },
    { href: '#limits',      label: t('sectionLimits') },
    { href: '#faq',         label: t('sectionFaq') },
  ]

  const faqItems = [
    { q: t('faqQ1'), a: t('faqA1'), open: true },
    { q: t('faqQ2'), a: t('faqA2') },
    { q: t('faqQ3'), a: t('faqA3') },
    { q: t('faqQ4'), a: t('faqA4') },
    { q: t('faqQ5'), a: t('faqA5') },
    { q: t('faqQ6'), a: t('faqA6') },
    { q: t('faqQ7'), a: t('faqA7') },
  ]

  return (
    <section className="tutorial" id="tutorial">
      <div className="section-title">
        <div className="kicker">{t('tutorialKicker')}</div>
        <h2>{t('tutorialTitle')}</h2>
      </div>

      <nav className="section-jump" aria-label={t('guideSections')}>
        {sectionLinks.map((link) => (
          <a href={link.href} key={link.href}>{link.label}</a>
        ))}
      </nav>

      <section className="info-block about-page" id="what-is-it" aria-labelledby="what-is-it-title">
        <div>
          <div className="kicker">{t('whatIsItKicker')}</div>
          <h3 id="what-is-it-title">{t('whatIsItTitle')}</h3>
        </div>
        <div className="info-copy">
          <p>{t('whatIsItP1')}</p>
          <p>{t('whatIsItP2')}</p>
        </div>
      </section>

      <section className="info-block" id="features" aria-labelledby="features-title">
        <div className="section-subtitle">
          <div className="kicker">{t('featuresKicker')}</div>
          <h3 id="features-title">{t('featuresTitle')}</h3>
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

      <section className="info-block" id="usage-guide" aria-labelledby="tutorial-title">
        <div className="section-subtitle">
          <div className="kicker">{t('quickGuideKicker')}</div>
          <h3 id="tutorial-title">{t('quickGuideTitle')}</h3>
        </div>

        <div className="steps">
          <div className="step">
            <div className="num">1</div>
            <h4>{t('step1Title')}</h4>
            <p>{t('step1Body')}</p>
            <div className="demo-line">https://<span className="hl">open.spotify.com/playlist/</span>37i9dQZF...</div>
          </div>
          <div className="step">
            <div className="num">2</div>
            <h4>{t('step2Title')}</h4>
            <p>{t('step2Body')}</p>
            <div className="demo-line">{t('step2Demo')}</div>
          </div>
          <div className="step">
            <div className="num">3</div>
            <h4>{t('step3Title')}</h4>
            <p>{t('step3Body')}</p>
            <div className="demo-line">{t('step3Demo')}</div>
          </div>
        </div>
      </section>

      <section className="info-block limits-block" id="limits" aria-labelledby="limits-title">
        <div className="section-subtitle">
          <div className="kicker">{t('limitsKicker')}</div>
          <h3 id="limits-title">{t('limitsTitle')}</h3>
        </div>

        <ul className="limit-list">
          {limits.map((limit) => (
            <li key={limit}>{limit}</li>
          ))}
        </ul>
      </section>

      <div className="faq" id="faq">
        <h3>{t('faqTitle')}</h3>
        {faqItems.map((item, i) => (
          <details key={i} open={item.open}>
            <summary>{item.q}</summary>
            <p>{item.a}</p>
          </details>
        ))}
      </div>
    </section>
  )
}
