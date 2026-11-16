import { defineConfig } from 'vite';
import { svelte } from '@sveltejs/vite-plugin-svelte';
import { readFileSync } from 'fs';

// Fassung aus version.json im Wurzelordner des Repos (einzige Quelle, gezählt vom Git-Haken): eingebaut ins Skript
// (__APP_VERSION__) und als Meta in die Startseite, an der das Ausrollen die ausgelieferte Fassung prüft.
const FASSUNG = JSON.parse(readFileSync(new URL('../version.json', import.meta.url), 'utf-8')).version;
const fassungEinsetzen = {
  name: 'fassung-einsetzen',
  transformIndexHtml: (html) => html.replace('</head>', `  <meta name="app-fassung" content="${FASSUNG}">\n</head>`)
};

export default defineConfig({
  plugins: [svelte(), fassungEinsetzen],
  define: {
    __APP_VERSION__: JSON.stringify(FASSUNG)
  },
  test: {
    environment: 'node',
    include: ['tests/**/*.test.js']
  },
  server: {
    host: '0.0.0.0',
    port: 5180,
    strictPort: true,
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
