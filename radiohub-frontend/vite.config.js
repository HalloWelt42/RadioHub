import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';

export default defineConfig({
  plugins: [svelte()],
  test: {
    environment: 'node',
    include: ['tests/**/*.test.js']
  },
  server: {
    host: '0.0.0.0',
    port: 5180,
    strictPort: true,
    cors: true,
    proxy: {
      '/api': {
        target: 'http://localhost:9091',
        changeOrigin: true
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
});
