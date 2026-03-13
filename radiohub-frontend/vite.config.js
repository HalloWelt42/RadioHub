import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { readFileSync } from 'fs';

const pkg = JSON.parse(readFileSync('./package.json', 'utf-8'));

export default defineConfig({
  plugins: [svelte()],
  define: {
    __APP_VERSION__: JSON.stringify(pkg.version)
  },
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
      },
      '/health': {
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
