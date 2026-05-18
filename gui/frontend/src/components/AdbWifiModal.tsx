import { useState } from 'react'
import { api } from '../api/client'

interface Props {
  onDismiss: () => void
  onConnected: (model: string) => void
}

type Step = 'enable' | 'connect'

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
  width: 380,
  animation: 'slideIn 0.2s ease',
  boxShadow: '0 16px 48px rgba(0,0,0,0.6)',
}

const btn = (primary: boolean, disabled = false): React.CSSProperties => ({
  flex: 1, padding: '9px 0', borderRadius: 7,
  border: primary ? 'none' : '1px solid #2A2A2A',
  background: primary ? (disabled ? '#0d6e30' : '#1DB954') : 'transparent',
  color: primary ? '#000' : '#888',
  fontSize: 13, fontWeight: 700,
  cursor: disabled ? 'not-allowed' : 'pointer',
  opacity: disabled ? 0.6 : 1,
})

const input: React.CSSProperties = {
  width: '100%', padding: '9px 12px',
  background: '#0F0F0F', border: '1px solid #2A2A2A',
  borderRadius: 7, color: '#fff', fontSize: 13,
  fontFamily: 'monospace', boxSizing: 'border-box',
  outline: 'none',
}

export function AdbWifiModal({ onDismiss, onConnected }: Props) {
  const [step, setStep] = useState<Step>('enable')
  const [ip, setIp] = useState('')
  const [loading, setLoading] = useState(false)
  const [msg, setMsg] = useState('')

  async function handleEnable() {
    setLoading(true)
    setMsg('')
    try {
      const r = await api.post<{ ok: boolean; message: string }>('/adb/enable-wifi', {})
      if (r.ok) {
        // Try to auto-detect IP
        const ipRes = await api.get<{ ip: string | null }>('/adb/device-ip')
        if (ipRes.ip) setIp(ipRes.ip)
        setStep('connect')
        setMsg(r.message)
      } else {
        setMsg(r.message || 'Failed — is USB device connected?')
      }
    } catch (e: any) {
      setMsg(e.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  async function handleConnect() {
    if (!ip.trim()) return
    setLoading(true)
    setMsg('')
    try {
      const r = await api.post<{ ok: boolean; message: string }>('/adb/connect-wifi', { ip: ip.trim() })
      if (r.ok) {
        onConnected(ip.trim())
      } else {
        setMsg(r.message || 'Connection failed')
      }
    } catch (e: any) {
      setMsg(e.message || 'Error')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={overlay} onClick={onDismiss}>
      <div style={modal} onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20 }}>
          <div style={{
            width: 44, height: 44, borderRadius: 10,
            background: 'rgba(29,185,84,0.12)',
            border: '1px solid rgba(29,185,84,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22,
          }}>
            📶
          </div>
          <div>
            <div style={{ fontSize: 14, fontWeight: 700, color: '#fff', marginBottom: 2 }}>
              Connect via WiFi
            </div>
            <div style={{ fontSize: 11, color: '#555' }}>
              {step === 'enable' ? 'Step 1 of 2 — Enable on USB device' : 'Step 2 of 2 — Enter device IP'}
            </div>
          </div>
        </div>

        {/* Step content */}
        {step === 'enable' ? (
          <>
            <div style={{
              background: '#0F0F0F', border: '1px solid #222',
              borderRadius: 8, padding: '12px 14px', marginBottom: 16, fontSize: 12, color: '#888', lineHeight: 1.6,
            }}>
              Connect Android via USB first, then click Enable. You can unplug USB after.
              <br />
              <span style={{ color: '#555', fontSize: 11 }}>Android 11+: use Wireless Debugging in Developer Options instead.</span>
            </div>
            {msg && <div style={{ fontSize: 11, color: '#E22D44', marginBottom: 12 }}>{msg}</div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={btn(false)} onClick={onDismiss}>Cancel</button>
              <button style={btn(true, loading)} onClick={handleEnable} disabled={loading}>
                {loading ? 'Enabling…' : 'Enable WiFi mode'}
              </button>
            </div>
          </>
        ) : (
          <>
            <div style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 11, color: '#666', marginBottom: 6 }}>Device IP address</div>
              <input
                style={input}
                value={ip}
                onChange={e => setIp(e.target.value)}
                placeholder="192.168.1.X"
                onKeyDown={e => e.key === 'Enter' && handleConnect()}
                autoFocus
              />
            </div>
            {msg && <div style={{ fontSize: 11, color: '#E22D44', marginBottom: 12 }}>{msg}</div>}
            <div style={{ display: 'flex', gap: 8 }}>
              <button style={btn(false)} onClick={() => setStep('enable')}>Back</button>
              <button style={btn(true, loading || !ip.trim())} onClick={handleConnect} disabled={loading || !ip.trim()}>
                {loading ? 'Connecting…' : 'Connect'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}
