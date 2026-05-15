function scoreColor(score: number) {
  if (score >= 85) return { color: '#1DB954', bg: 'rgba(29,185,84,0.10)' }
  if (score >= 65) return { color: '#F59B23', bg: 'rgba(245,155,35,0.10)' }
  return { color: '#E22D44', bg: 'rgba(226,45,68,0.10)' }
}

export function ScoreBadge({ score }: { score: number }) {
  const { color, bg } = scoreColor(score)
  return (
    <span style={{
      color, background: bg,
      border: `1px solid ${color}44`,
      borderRadius: 3, padding: '1px 6px',
      fontSize: 11, fontWeight: 700,
      fontFamily: 'JetBrains Mono, monospace',
    }}>
      {score}%
    </span>
  )
}
