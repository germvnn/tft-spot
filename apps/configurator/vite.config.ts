import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const apiProxy = {
  '/api': 'http://127.0.0.1:8000',
  '/game-assets': 'http://127.0.0.1:8000',
}

export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    host: '127.0.0.1',
    proxy: apiProxy,
  },
  preview: {
    host: '127.0.0.1',
    proxy: apiProxy,
  },
})
