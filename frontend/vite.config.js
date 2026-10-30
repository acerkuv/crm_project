import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [
    react(),
    // VitePWA — ОТКЛЮЧЁН (кэширует API-ответы, ломает данные)
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '.ngrok-free.app',
      'a7a9-194-58-37-17.ngrok-free.app',
      '553e-194-58-37-17.ngrok-free.app',
    ],
    watch: { usePolling: true },
    cors: {
      origin: '*',
      methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
      allowedHeaders: ['*'],
    },
  },
  preview: {
    host: '0.0.0.0',
    port: 3000,
  },
})