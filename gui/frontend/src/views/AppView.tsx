import { useState } from 'react'
import { HeroSearch } from '../components/HeroSearch'
import { PlaylistCard } from '../components/PlaylistCard'
import { QuickTrackModal } from '../components/QuickTrackModal'
import { useToast } from '../components/toast-context'
import type { ResolvedPayload, SpotifyTrack } from '../api/types'

function ResultsSkeleton() {
  return (
    <section className="results" id="results" aria-label="Cargando resultados">
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

export function AppView() {
  const [payload, setPayload] = useState<ResolvedPayload | null>(null)
  const [sourceUrl, setSourceUrl] = useState('')
  const [searching, setSearching] = useState(false)
  const [quickTrack, setQuickTrack] = useState<SpotifyTrack | null>(null)
  const { toast } = useToast()

  return (
    <>
      <HeroSearch
        onResolved={(p, url) => {
          setSourceUrl(url)
          if (p.kind === 'track' && p.tracks[0]) {
            setPayload(null)
            setQuickTrack(p.tracks[0])
            toast('Track listo para descargar', 'success')
          } else {
            setQuickTrack(null)
            setPayload(p)
            toast(`${p.tracks.length} tracks cargados`, 'success')
          }
        }}
        onError={msg => toast(msg, 'error')}
        onLoadingChange={setSearching}
      />

      {searching && !payload && !quickTrack && <ResultsSkeleton />}
      {payload && <PlaylistCard payload={payload} sourceUrl={sourceUrl} />}
      {quickTrack && <QuickTrackModal track={quickTrack} onClose={() => setQuickTrack(null)} />}
    </>
  )
}
