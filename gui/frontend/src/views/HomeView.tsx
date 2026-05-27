import { useState } from 'react'
import { HeroSearch } from '../components/HeroSearch'
import { PlaylistCard } from '../components/PlaylistCard'
import { TutorialSection } from '../components/TutorialSection'
import { useToast } from '../components/Toast'
import type { ResolvedPayload } from '../api/types'

export function HomeView() {
  const [payload, setPayload] = useState<ResolvedPayload | null>(null)
  const { toast } = useToast()

  return (
    <>
      <HeroSearch
        onResolved={p => {
          setPayload(p)
          toast(`${p.tracks.length} tracks cargados`, 'success')
        }}
        onError={msg => toast(msg, 'error')}
      />

      {payload && <PlaylistCard payload={payload} />}

      <TutorialSection />
    </>
  )
}
