import { lazy, Suspense, useEffect, useState } from 'react'
import { HeroSearch } from '../components/HeroSearch'
import { TutorialSection } from '../components/TutorialSection'
import { useToast } from '../components/toast-context'
import { usePreferences } from '../preferences'
import type { ResolvedPayload, SpotifyTrack } from '../api/types'

const PlaylistCard = lazy(() =>
  import('../components/PlaylistCard').then(module => ({ default: module.PlaylistCard })),
)

const QuickTrackModal = lazy(() =>
  import('../components/QuickTrackModal').then(module => ({ default: module.QuickTrackModal })),
)

function ResultsSkeleton({ ariaLabel }: { ariaLabel: string }) {
  return (
    <section className="results" id="results" aria-label={ariaLabel}>
      <div className="pl-card loading-card">
        <div className="pl-head">
          <span className="sk cover-sk-lg" />
          <div className="loading-copy">
            <span className="sk kicker-sk" />
            <span className="sk heading-sk" />
            <span className="sk stat-sk" />
          </div>
          <div className="loading-actions">
            <span className="sk select-sk" />
            <span className="sk button-sk" />
          </div>
        </div>
        <div className="track-skeletons static" aria-hidden="true">
          {Array.from({ length: 6 }).map((_, i) => (
            <div className="track-skeleton" key={i}>
              <span className="sk idx-sk" />
              <span className="sk cover-sk" />
              <span className="sk title-sk" />
              <span className="sk badge-sk" />
              <span className="sk dur-sk" />
              <span className="sk btn-sk" />
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

interface LandingViewProps {
  focusSection?: 'tutorial' | 'faq'
}

export function LandingView({ focusSection }: LandingViewProps) {
  const [payload, setPayload] = useState<ResolvedPayload | null>(null)
  const [sourceUrl, setSourceUrl] = useState('')
  const [searching, setSearching] = useState(false)
  const [quickTrack, setQuickTrack] = useState<SpotifyTrack | null>(null)
  const { toast } = useToast()
  const { t } = usePreferences()

  useEffect(() => {
    if (!focusSection || payload || quickTrack || searching) return
    window.setTimeout(() => {
      document.getElementById(focusSection)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }, 50)
  }, [focusSection, payload, quickTrack, searching])

  return (
    <>
      <HeroSearch
        onResolved={(p, url) => {
          setSourceUrl(url)
          if (p.kind === 'track' && p.tracks[0]) {
            setPayload(null)
            setQuickTrack(p.tracks[0])
            toast(t('plTrackReady'), 'success')
          } else {
            setQuickTrack(null)
            setPayload(p)
            toast(t('plTracksLoaded')(p.tracks.length), 'success')
          }
        }}
        onError={msg => toast(msg, 'error')}
        onLoadingChange={setSearching}
      />

      {searching && !payload && !quickTrack && <ResultsSkeleton ariaLabel={t('plLoadingResults')} />}
      <Suspense fallback={null}>
        {payload && <PlaylistCard payload={payload} sourceUrl={sourceUrl} />}
        {quickTrack && <QuickTrackModal track={quickTrack} onClose={() => setQuickTrack(null)} />}
      </Suspense>

      {!payload && !quickTrack && !searching && <TutorialSection />}
    </>
  )
}
