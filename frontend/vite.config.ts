import { readFileSync } from "node:fs";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import { defineConfig } from "vitest/config";

// Fassung aus version.json im Wurzelordner des Repos (einzige Quelle, gezählt vom Git-Haken): eingebaut ins Skript
// (__APP_FASSUNG__) und als Meta in die Startseite, an der Schale und Ausrollen die ausgelieferte Fassung prüfen.
const FASSUNG = JSON.parse(readFileSync(new URL("../version.json", import.meta.url), "utf-8")).version as string;
const fassungEinsetzen = {
  name: "fassung-einsetzen",
  transformIndexHtml: (html: string) => html.replace("</head>", `  <meta name="app-fassung" content="${FASSUNG}" />\n  </head>`),
};

// Beim Entwickeln leitet Vite /api und /health ans Backend (nur am eigenen Rechner); im Betrieb liefert das Backend die
// gebaute Oberfläche selbst aus.
const BACKEND = "http://127.0.0.1:9091";

export default defineConfig({
  plugins: [svelte(), fassungEinsetzen],
  define: { __APP_FASSUNG__: JSON.stringify(FASSUNG) },
  // Die Oberfläche des Appkerns kommt als Svelte-Quelltext mit TypeScript; Vite bündelt sie nicht vor, sie wird wie
  // eigener Code übersetzt (sonst scheitert das Vorbündeln an den .svelte.ts-Dateien)
  optimizeDeps: { exclude: ["appkern-oberflaeche"] },
  test: { environment: "node", include: ["tests/**/*.test.js"] },
  server: {
    host: "127.0.0.1",
    port: 5180,
    strictPort: true,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: false },
      "/health": { target: BACKEND, changeOrigin: false },
    },
  },
  build: { outDir: "dist", assetsDir: "assets" },
});
