import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const host = process.env.TAURI_DEV_HOST

export default defineConfig({
  plugins: [react()],
  // Tauri expects a fixed port; clearScreen=false keeps Tauri logs visible.
  clearScreen: false,
  server: {
    host: host || false,
    port: 5173,
    strictPort: true,
    hmr: host ? { protocol: 'ws', host, port: 5183 } : undefined,
    watch: {
      // Tell Vite to ignore watching src-tauri.
      ignored: ['**/src-tauri/**'],
    },
  },
})
