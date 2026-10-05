import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  base: '/app/',
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/v1': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
      '/openapi.json': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
      '/health': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
      '/docs': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
      '/redoc': {
        target: 'http://api:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
  build: {
    outDir: 'dist',
  },
});