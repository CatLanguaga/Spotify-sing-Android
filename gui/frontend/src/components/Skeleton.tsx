const shimmer = {
  background: 'linear-gradient(90deg, #1A1A1A 0%, #2A2A2A 50%, #1A1A1A 100%)',
  backgroundSize: '200% 100%',
  animation: 'skeletonPulse 1.6s linear infinite',
  borderRadius: 4,
}

const ROW_WIDTHS = [40, 260, 140, 60, 80, 120]

export function SkeletonRow({ cols = 6 }: { cols?: number }) {
  return (
    <tr style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
      {Array.from({ length: cols }).map((_, i) => (
        <td key={i} style={{ padding: '11px 16px' }}>
          {i === 1 ? (
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{ ...shimmer, width: 32, height: 32, borderRadius: 4, flexShrink: 0 }} />
              <div style={{ ...shimmer, height: 13, width: 180 }} />
            </div>
          ) : (
            <div style={{ ...shimmer, height: 13, width: ROW_WIDTHS[i] ?? 80 }} />
          )}
        </td>
      ))}
    </tr>
  )
}

export function SkeletonCard() {
  return (
    <div style={{
      background: '#1A1A1A', border: '1px solid #2A2A2A',
      borderRadius: 8, padding: 12,
      display: 'flex', alignItems: 'center', gap: 12,
    }}>
      <div style={{ ...shimmer, width: 48, height: 48, borderRadius: 6, flexShrink: 0 }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 7 }}>
        <div style={{ ...shimmer, height: 13, width: '55%' }} />
        <div style={{ ...shimmer, height: 11, width: '35%' }} />
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        {[52, 26, 26, 26, 26].map((w, i) => (
          <div key={i} style={{ ...shimmer, height: 28, width: w, borderRadius: 5 }} />
        ))}
      </div>
    </div>
  )
}
