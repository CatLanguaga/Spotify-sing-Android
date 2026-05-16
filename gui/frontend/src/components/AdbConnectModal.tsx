interface Device {
  serial: string
  model: string
}

interface Props {
  device: Device
  onConfirm: () => void
  onDismiss: () => void
}

const overlay: React.CSSProperties = {
  position: 'fixed', inset: 0,
  background: 'rgba(0,0,0,0.7)',
  display: 'flex', alignItems: 'center', justifyContent: 'center',
  zIndex: 8000,
  backdropFilter: 'blur(4px)',
}

const modal: React.CSSProperties = {
  background: '#141414',
  border: '1px solid #2A2A2A',
  borderRadius: 12,
  padding: '28px 32px',
  width: 360,
  animation: 'slideIn 0.2s ease',
  boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
}

const btn = (primary: boolean): React.CSSProperties => ({
  flex: 1, padding: '9px 0', borderRadius: 7,
  border: primary ? 'none' : '1px solid #2A2A2A',
  background: primary ? '#1DB954' : 'transparent',
  color: primary ? '#000' : '#888',
  fontSize: 13, fontWeight: 700,
  cursor: 'pointer',
})

export function AdbConnectModal({ device, onConfirm, onDismiss }: Props) {
  return (
    <div style={overlay} onClick={onDismiss}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        {/* Icon */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10,
            background: 'rgba(29,185,84,0.12)',
            border: '1px solid rgba(29,185,84,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
          }}>
            📱
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 2 }}>
              Android device detected
            </div>
            <div style={{ fontSize: 11, color: '#1DB954' }}>Ready to connect</div>
          </div>
        </div>

        {/* Device info */}
        <div style={{
          background: '#0F0F0F', border: '1px solid #222',
          borderRadius: 8, padding: '12px 14px', marginBottom: 24,
        }}>
          <div style={{ fontSize: 15, fontWeight: 600, color: '#fff', marginBottom: 4 }}>
            {device.model}
          </div>
          <div style={{ fontSize: 11, color: '#555', fontFamily: 'monospace' }}>
            {device.serial}
          </div>
        </div>

        {/* Actions */}
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={btn(false)} onClick={onDismiss}>Dismiss</button>
          <button style={btn(true)} onClick={onConfirm}>Use this device</button>
        </div>
      </div>
    </div>
  )
}
