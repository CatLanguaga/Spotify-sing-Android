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

export interface CompareResult {
  spotify: SpotifyTrack
  score: number
  status: 'match' | 'missing' | 'dubious'
  device_file?: string
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
  download_path: string
  auto_approve_threshold: number
  min_score_to_show: number
}

export interface ScriptInfo {
  name: string
  path: string
}
