import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// During `npm run dev` the browser calls same-origin /api which Vite proxies
// to the FastAPI container.  Production uses the nginx proxy instead.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: process.env.VITE_API_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
})
