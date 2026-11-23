import { copyFileSync, cpSync, existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { svelte } from "@sveltejs/vite-plugin-svelte";
import type { Plugin } from "vite";
import { defineConfig } from "vitest/config";
import { DARSTELLUNG, darstellungVorab } from "./src/lib/darstellung-vorab";
// Statusleiste: die Regel des Rahmens aus dem Appkern (lib/rahmen-vorab.ts)
import { rahmenVorab } from "./node_modules/appkern-oberflaeche/oberflaeche/lib/rahmen-vorab";

// Fassung aus version.json im Wurzelordner des Repos (einzige Quelle, gezählt vom Git-Haken): eingebaut ins Skript
// (__APP_FASSUNG__) und als Meta in die Startseite, an der Schale und Ausrollen die ausgelieferte Fassung prüfen.
const FASSUNG = JSON.parse(readFileSync(new URL("../version.json", import.meta.url), "utf-8")).version as string;
const fassungEinsetzen = {
  name: "fassung-einsetzen",
  transformIndexHtml: (html: string) => html.replace("</head>", `  <meta name="app-fassung" content="${FASSUNG}" />\n  </head>`),
};

// Darstellung (Vorlage, Thema, Schriftstufe) vor jeder Gestaltung anwenden, damit nichts aufblitzt: dieselbe Funktion wie
// zur Laufzeit (lib/darstellung-vorab.ts), als kleines Skript an den Anfang des Kopfs der Startseite
const darstellungEinsetzen = {
  name: "darstellung-einsetzen",
  transformIndexHtml: (html: string) =>
    html.replace("<head>", `<head>\n    <script>(${darstellungVorab.toString()})(${JSON.stringify(DARSTELLUNG)});</script>`)
      // Statusleiste: direkt hinter dem Viewport-Tag, das es anpasst (Appkern, lib/rahmen-vorab.ts)
      .replace(/(<meta name="viewport"[^>]*>)/, `$1\n  <script>(${rahmenVorab.toString()})();</script>`),
};

// Zwei Bauziele aus einer Oberfläche (RAD-4, Entscheidung 28): die volle App (Vorgabe) und die Webversion nur mit Radio
// für GitHub Pages (`vite build --mode web`). Was sich unterscheidet, steht an einem Ort: src/ziel/voll oder
// src/ziel/web (Senderquelle und Wurzel), eingebunden über den Alias $ziel.
const ZIEL = (mode: string) => (mode === "web" ? "web" : "voll");
const ORDNER = (pfad: string) => fileURLToPath(new URL(pfad, import.meta.url));

// Webversion: Basis des Repos auf GitHub Pages (https://hallowelt42.github.io/RadioHub/)
const WEB_BASIS = "/RadioHub/";
// aus public die Symbole und der Ordner, den auch die Basic liest: legal (Texte unter Über und im Fenster Datenschutz und
// Herkunft; RAD-36: fehlten sie, zeigte Über "Text nicht gefunden"); dazu die statische Senderliste aus web/daten (per
// Skript erzeugt, LIESMICH dort)
const WEB_SYMBOLE = ["favicon.ico", "favicon-32.png", "favicon.svg", "icon-192.png", "icon-512.png", "icon-maskable-192.png",
  "icon-maskable-512.png", "apple-touch-icon.png"];
const WEB_ORDNER = ["legal"];
const WEB_DATEN = ORDNER("../web/daten");
// Adressen der Basic ohne Kennung (Bereiche und Reiter der Einstellungen), siehe webDateien
const WEB_ADRESSEN = ["radio", "einstellungen", "einstellungen/radio", "einstellungen/radio/regeln", "einstellungen/radio/ausgeblendet",
  "einstellungen/radio/laender", "einstellungen/radio/datei", "einstellungen/allgemein", "einstellungen/allgemein/bedienung",
  "einstellungen/allgemein/tastatur", "einstellungen/allgemein/ueber", "einstellungen/darstellung",
  "einstellungen/wecker", "einstellungen/wecker/zeitansage", "einstellungen/wecker/ort"];
// Name der Webversion: RadioHub Basic (die volle Version ist RadioHub PRO, Nutzer 20.11.2026)
const WEB_NAME = "RadioHub Basic";

/** Typen der Dateien, die der Entwicklungsdienst der Webversion selbst ausliefert */
const ARTEN: Record<string, string> = { svg: "image/svg+xml", png: "image/png", ico: "image/x-icon", md: "text/markdown; charset=utf-8",
  json: "application/json" };

/** Manifest der Webversion: Pfade unter der Basis */
function webManifest(): string {
  const m = JSON.parse(readFileSync(ORDNER("public/site.webmanifest"), "utf-8"));
  const unter = (p: string) => WEB_BASIS + p.replace(/^\//, "");
  return JSON.stringify({ ...m, name: WEB_NAME, short_name: WEB_NAME, id: WEB_BASIS, start_url: unter("radio"), scope: WEB_BASIS,
    icons: m.icons.map((i: { src: string }) => ({ ...i, src: unter(i.src) })) }, null, 2);
}

/** Dateien der Webversion: beim Entwickeln ausgeliefert, beim Bau in den Ausgabeordner gelegt; dazu 404.html als Kopie
 *  der Startseite, damit Pages tiefe Adressen (/RadioHub/radio/...) an die App gibt */
function webDateien(): Plugin {
  let aus = "";
  return {
    name: "web-dateien",
    configResolved: (c) => { aus = c.build.outDir; },
    // Verweise der Startseite auf Symbole und Manifest unter die Basis (ohne öffentlichen Ordner setzt Vite sie nicht)
    transformIndexHtml: (html) => html.replace(/href="\/([^"/]+\.(?:ico|png|svg|webmanifest))"/g, `href="${WEB_BASIS}$1"`)
      .replace("<title>RadioHub</title>", `<title>${WEB_NAME}</title>`).replace('content="RadioHub"', `content="${WEB_NAME}"`),
    configureServer(server) {
      server.middlewares.use((req, res, weiter) => {
        const pfad = (req.url ?? "").split("?")[0].replace(WEB_BASIS, "/");
        const name = pfad.replace(/^\//, "");
        const datei = name === "site.webmanifest" ? null : name.startsWith("daten/") ? `${WEB_DATEN}/${name.slice(6)}`
          : WEB_SYMBOLE.includes(name) || WEB_ORDNER.some((o) => name.startsWith(`${o}/`)) ? ORDNER(`public/${name}`) : "";
        if (datei === null) { res.setHeader("Content-Type", "application/manifest+json"); res.end(webManifest()); return; }
        if (!datei || !existsSync(datei)) return weiter();
        const art = ARTEN[datei.slice(datei.lastIndexOf(".") + 1)];
        if (art) res.setHeader("Content-Type", art);          // ohne Typ zeigt der Browser etwa SVG nicht als Bild
        res.end(readFileSync(datei));
      });
    },
    closeBundle() {
      for (const n of WEB_SYMBOLE) copyFileSync(ORDNER(`public/${n}`), `${aus}/${n}`);
      for (const o of WEB_ORDNER) cpSync(ORDNER(`public/${o}`), `${aus}/${o}`, { recursive: true });
      writeFileSync(`${aus}/site.webmanifest`, webManifest());
      mkdirSync(`${aus}/daten`, { recursive: true });
      if (existsSync(WEB_DATEN)) cpSync(WEB_DATEN, `${aus}/daten`, { recursive: true });
      copyFileSync(`${aus}/index.html`, `${aus}/404.html`);
      // feste Adressen der Basic als eigene Startseiten: Pages antwortet dort mit 200 statt mit 404.html (RAD-10);
      // nur Direktlinks auf einen Sender gehen weiter über 404.html
      for (const pfad of WEB_ADRESSEN) {
        mkdirSync(`${aus}/${pfad}`, { recursive: true });
        copyFileSync(`${aus}/index.html`, `${aus}/${pfad}/index.html`);
      }
    },
  };
}

// Beim Entwickeln leitet Vite /api und /health ans Backend (nur am eigenen Rechner); im Betrieb liefert das Backend die
// gebaute Oberfläche selbst aus.
const BACKEND = "http://127.0.0.1:9091";

export default defineConfig(({ mode }) => ({
  base: ZIEL(mode) === "web" ? WEB_BASIS : "/",
  plugins: [svelte(), fassungEinsetzen, darstellungEinsetzen, ...(ZIEL(mode) === "web" ? [webDateien()] : [])],
  define: { __APP_FASSUNG__: JSON.stringify(FASSUNG) },
  resolve: { alias: { $ziel: ORDNER(`src/ziel/${ZIEL(mode)}`) } },
  publicDir: ZIEL(mode) === "web" ? false : "public",
  // Die Oberfläche des Appkerns kommt als Svelte-Quelltext mit TypeScript; Vite bündelt sie nicht vor, sie wird wie
  // eigener Code übersetzt (sonst scheitert das Vorbündeln an den .svelte.ts-Dateien)
  optimizeDeps: { exclude: ["appkern-oberflaeche"] },
  test: { environment: "node", include: ["tests/**/*.test.js", "tests/**/*.test.ts"] },
  server: {
    host: "127.0.0.1",
    port: ZIEL(mode) === "web" ? 5190 : 5180,
    strictPort: true,
    proxy: {
      "/api": { target: BACKEND, changeOrigin: false },
      "/health": { target: BACKEND, changeOrigin: false },
    },
  },
  build: { outDir: ZIEL(mode) === "web" ? "dist-web" : "dist", assetsDir: "assets" },
}));
