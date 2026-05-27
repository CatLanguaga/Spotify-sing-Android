export type Language = 'JP' | 'KR' | 'EN' | 'ES' | 'CN' | 'RU' | 'OTHER'
export type QueueStatus = 'pending' | 'approved' | 'rejected' | 'downloading' | 'done' | 'error'

export interface SpotifyTrack {
  name: string
  artist: string
  all_artists: string
  duration_ms: number
  album: string
  album_art_url: string | null
  language: string
  spotify_id: string
  year: string
  track_number: number
}

export interface QueueItem {
  id: string
  title: string
  artist: string
  album: string
  language: string
  score: number
  status: QueueStatus
  spotify_id: string
  cover_url: string | null
  youtube_url: string | null
  local_path: string | null
  fmt: string
  quality: number
}

export interface SpotifyConfig {
  client_id: string
  client_secret: string
  playlist_id: string
  default_fmt: string
  default_quality: number
}

export type ResolvedKind = 'track' | 'album' | 'playlist'

export interface ResolvedInfo {
  name: string
  owner?: string
  image_url?: string | null
  total_tracks?: number
}

export interface ResolvedPayload {
  kind: ResolvedKind
  info: ResolvedInfo
  tracks: SpotifyTrack[]
  total: number
  returned: number
  offset: number
}

export interface TrackDownloadResponse {
  item_id: string
  title: string
  artist: string
}
