import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

const backendPort = Number(process.env.GODCV_BACKEND_PORT) || 9001
const frontendPort = Number(process.env.GODCV_FRONTEND_PORT) || 3001

export default defineConfig({
  plugins: [vue()],
  server: {
    port: frontendPort,
    strictPort: true,
    proxy: {
      '/api': {
        target: `http://localhost:${backendPort}`,
        changeOrigin: true,
      },
    },
  },
})
