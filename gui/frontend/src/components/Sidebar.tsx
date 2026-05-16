import { useWindowWidth } from '../hooks/useWindowWidth'

type View = 'compare' | 'queue' | 'monitor' | 'settings'

const NAV = [
  { id: 'compare',  icon: '⇄', label: 'Compare'  },
  { id: 'queue',    icon: '↓', label: 'Queue'    },
  { id: 'monitor',  icon: '▶', label: 'Monitor'  },
  { id: 'settings', icon: '⚙', label: 'Settings' },
] as const

interface Props {
  active: View
  onNav: (v: View) => void
  adbConnected?: boolean
  adbScanning?: boolean
}

export function Sidebar({ active, onNav, adbConnected = false, adbScanning = false }: Props) {
  const width = useWindowWidth()
  const expanded = width >= 768

  const dotColor = adbConnected ? '#1DB954' : adbScanning ? '#F59B23' : '#333'
  const dotGlow  = adbConnected ? '0 0 6px #1DB954' : adbScanning ? '0 0 6px #F59B23' : 'none'
  const dotAnim  = (adbConnected || adbScanning) ? 'pulse 2s infinite' : 'none'
  const statusLabel = adbConnected ? 'Device connected' : adbScanning ? 'Scanning...' : 'No device'
  const statusColor = adbConnected ? '#1DB954' : adbScanning ? '#F59B23' : '#555'

  return (
    <aside style={{
      width: expanded ? 200 : 60,
      minHeight: '100%',
      background: '#080808',
      display: 'flex',
      flexDirection: 'column',
      alignItems: expanded ? 'stretch' : 'center',
      paddingTop: 16,
      paddingBottom: 20,
      borderRight: '1px solid #1a1a1a',
      flexShrink: 0,
      transition: 'width 0.2s ease',
      overflow: 'hidden',
    }}>
      {/* Logo */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        gap: expanded ? 10 : 0,
        padding: expanded ? '0 16px' : '0',
        justifyContent: expanded ? 'flex-start' : 'center',
        marginBottom: 28,
      }}>
        <div style={{
          width: 32, height: 32, borderRadius: '50%',
          background: '#1DB954',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontSize: 15, flexShrink: 0,
        }}>
          ♫
        </div>
        {expanded && (
          <div>
            <div style={{ fontSize: 13, fontWeight: 700, color: '#fff', lineHeight: 1.2, whiteSpace: 'nowrap' }}>Spotify Sync</div>
            <div style={{ fontSize: 10, color: '#666', lineHeight: 1.2 }}>Manager</div>
          </div>
        )}
      </div>

      {/* Nav items */}
      <nav style={{
        display: 'flex', flexDirection: 'column', gap: 2,
        padding: expanded ? '0 8px' : '0',
        width: '100%',
        alignItems: expanded ? 'stretch' : 'center',
      }}>
        {NAV.map(({ id, icon, label }) => {
          const isActive = active === id
          return (
            <button
              key={id}
              title={expanded ? undefined : label}
              onClick={() => onNav(id as View)}
              style={{
                width: expanded ? '100%' : 46,
                height: expanded ? 'auto' : 46,
                padding: expanded ? '9px 12px' : '0',
                borderRadius: 8, border: 'none', cursor: 'pointer',
                background: isActive ? 'rgba(29,185,84,0.12)' : 'transparent',
                color: isActive ? '#1DB954' : '#888',
                display: 'flex', alignItems: 'center',
                justifyContent: expanded ? 'flex-start' : 'center',
                gap: expanded ? 10 : 0,
                fontSize: expanded ? 13 : 18,
                fontWeight: isActive ? 600 : 400,
                textAlign: 'left',
                transition: 'background 0.1s, color 0.1s',
              }}
              onMouseEnter={e => {
                if (!isActive) {
                  e.currentTarget.style.background = 'rgba(255,255,255,0.05)'
                  e.currentTarget.style.color = '#ccc'
                }
              }}
              onMouseLeave={e => {
                if (!isActive) {
                  e.currentTarget.style.background = 'transparent'
                  e.currentTarget.style.color = '#888'
                }
              }}
            >
              <span style={{ fontSize: 16, width: expanded ? 20 : undefined, textAlign: 'center', flexShrink: 0 }}>
                {icon}
              </span>
              {expanded && label}
            </button>
          )
        })}
      </nav>

      {/* Spacer */}
      <div style={{ flex: 1 }} />

      {/* ADB status */}
      {expanded ? (
        <div style={{
          margin: '0 8px', padding: '10px 12px',
          background: '#0F0F0F', borderRadius: 8, border: '1px solid #1a1a1a',
          display: 'flex', alignItems: 'center', gap: 8,
        }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: dotColor,
            boxShadow: dotGlow,
            animation: dotAnim,
          }} />
          <div>
            <div style={{ fontSize: 11, fontWeight: 600, color: statusColor }}>
              {statusLabel}
            </div>
            <div style={{ fontSize: 10, color: '#444', marginTop: 1 }}>ADB</div>
          </div>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 4 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%',
            background: dotColor,
            boxShadow: dotGlow,
            animation: dotAnim,
          }} />
          <span style={{ fontSize: 8, color: '#666', fontFamily: 'monospace' }}>ADB</span>
        </div>
      )}
    </aside>
  )
}
