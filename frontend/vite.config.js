import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico'],
      manifest: {
        name: 'CRM Уют',
        short_name: 'CRM Уют',
        description: 'Умная CRM система для управления клиентами',
        theme_color: '#1890ff',
        background_color: '#f0f2f5',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: '/vite.svg',
            sizes: '512x512',
            type: 'image/svg+xml'
          }
        ]
      }
    })
  ],
  server: {
    host: '0.0.0.0',
    port: 3000,
    strictPort: true,
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '.ngrok-free.app',  // Разрешает все ngrok поддомены
      'a7a9-194-58-37-17.ngrok-free.app',
      '553e-194-58-37-17.ngrok-free.app'
    ],
    watch: {
      usePolling: true,
    },
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
