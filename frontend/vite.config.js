import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/auth': 'http://127.0.0.1:8000',
      '/query': 'http://127.0.0.1:8000',
      '/history': 'http://127.0.0.1:8000',
      '/upload': 'http://127.0.0.1:8000',
      '/tts': 'http://127.0.0.1:8000',
      '/process-audio': 'http://127.0.0.1:8000'
    }
  }
})
