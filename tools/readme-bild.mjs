// README-Bild (.github/bilder/geraete.png, RAD-110): Rechner, Telefon und Uhr mit RadioHub in gezeichneten Geräten
// (docs/readme-bild/buehne.html, Vorlage aus TubeVault und Wetterwarte). Die Bildschirme sind Aufnahmen mit frischem
// Browserprofil, nie aus dem Betrieb:
//   Rechner: RadioHub PRO aus dem Probebetrieb (Kopie der Daten, Anmeldung zum Schein), das Radio hell, ein Sender spielt
//   Telefon: RadioHub Basic, dunkel, großer Spieler mit einer Folge von morfCast + chill (nur dieses Probe-Abo)
//   Uhr: dunkel, dieselbe Folge (gezeichnet in der Präsentation, Titel und Bild aus der Telefonaufnahme)
// Chrome über den Appkern (browser.mjs, nichts bleibt liegen), Ton aus. Rechner und Telefon einzeln, weil Probebetrieb
// und Basic selten zugleich laufen:
//
//   node tools/readme-bild.mjs --nur rechner --rechner http://localhost:5182/ --sitzung sitzung-probebetrieb
//   node tools/readme-bild.mjs --nur telefon --app http://localhost:5190/RadioHub/     # Basic (Vite, --mode web)
//   node tools/readme-bild.mjs --nur buehne          # nur die Präsentation neu aus den vorhandenen Aufnahmen
//   node tools/readme-bild.mjs --nur basic           # media/webversion.png: Basic am Rechner, dunkel, Podcasts
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const WURZEL = join(dirname(fileURLToPath(import.meta.url)), "..");
const { oeffneSeite } = await import(pathToFileURL(join(WURZEL, "frontend/node_modules/appkern-oberflaeche/oberflaeche/werkzeuge/browser.mjs")).href);

const argumente = Object.fromEntries(process.argv.slice(2).join(" ").split("--").filter(Boolean).map((a) => a.trim().split(/\s+/)));
const APP = (argumente.app ?? "http://localhost:5190/RadioHub/").replace(/\/?$/, "/");
/** PRO für den Rechner (Probebetrieb) und die Sitzung dort; ohne Angabe Basic wie das Telefon */
const RECHNER = (argumente.rechner ?? APP).replace(/\/?$/, "/");
const SITZUNG = argumente.sitzung ?? "";
const NUR = argumente.nur ?? ("nur-buehne" in argumente ? "buehne" : "alles");
const MIT = (teil) => NUR === "alles" || NUR === teil;
const BASIC_BILD = join(WURZEL, "media/webversion.png");
/** das beworbene Abo (Nutzer 22.11.2026) */
const PODCAST = { feed: "https://anchor.fm/s/11972ae38/podcast/rss", titel: "morfCast + chill" };
const ORDNER = join(WURZEL, "docs/readme-bild/aufnahmen");   // nicht im Repo (.gitignore), nur das fertige Bild
const STAND = join(ORDNER, "stand.json");
const ZIEL = join(WURZEL, ".github/bilder/geraete.png");

const warte = (ms) => new Promise((r) => setTimeout(r, ms));
const seite = await oeffneSeite({ frist: 60000 });
const warnungen = new Set();
seite.beiEreignis((m) => {
  if (m.method === "Runtime.exceptionThrown") warnungen.add(String(m.params.exceptionDetails.exception?.description ?? "").slice(0, 200));
});
const rufe = async (method, params = {}) => {
  const m = await seite.rufe(method, params);
  if (m.error) throw new Error(`${method}: ${m.error.message}`);
  return m.result;
};
const auswerten = async (ausdruck) => (await rufe("Runtime.evaluate", { expression: ausdruck, awaitPromise: true, returnByValue: true })).result?.value;

/** warten, bis der Ausdruck wahr ist (höchstens 40 s), dann kurz für Bilder und Übergänge */
async function bisDa(ausdruck, was, nachher = 1500) {
  for (let i = 0; i < 160; i++) {
    if (await auswerten(ausdruck)) return warte(nachher);
    await warte(250);
  }
  throw new Error(`nicht fertig: ${was}`);
}

async function aufnehmen(datei) {
  const { data } = await rufe("Page.captureScreenshot", { format: "png" });
  mkdirSync(dirname(datei), { recursive: true });
  writeFileSync(datei, Buffer.from(data, "base64"));
  console.log("geschrieben:", datei.replace(WURZEL + "/", ""));
}

async function geraet(breite, hoehe, dichte, mobil) {
  await rufe("Emulation.setDeviceMetricsOverride", { width: breite, height: hoehe, deviceScaleFactor: dichte, mobile: mobil });
  await rufe("Emulation.setTouchEmulationEnabled", mobil ? { enabled: true, maxTouchPoints: 5 } : { enabled: false });
}

/** Angaben im Speicher des Browsers setzen (auf einer Seite derselben Herkunft), dann die Ansicht laden */
async function oeffnen(basis, pfad, angaben) {
  await rufe("Page.navigate", { url: `${basis}radio` });
  await warte(1500);
  await auswerten(`localStorage.clear(); for (const [k, v] of Object.entries(${JSON.stringify(angaben)})) localStorage.setItem(k, v); true`);
  await rufe("Page.navigate", { url: basis + pfad });
}

await rufe("Page.enable");
await rufe("Runtime.enable");

/** das Probe-Abo in Basic anlegen (Quelle des Entwicklungsservers) und seine Kennung liefern */
async function aboAnlegen() {
  const kennung = await auswerten(`(async () => {
    const m = await import("${APP}src/lib/podcasts/index.ts").catch(() => null);
    return m ? (await m.aboliste.abonnieren(${JSON.stringify(PODCAST.feed)})).id : null;
  })()`);
  if (kennung === null) throw new Error("Abo nicht angelegt (nur gegen den Entwicklungsserver von Basic)");
  return kennung;
}

if (NUR === "basic") {
  // Bild der Webversion in der README (media/webversion.png): Basic am Rechner, dunkel, das Abo morfCast + chill mit
  // seinen Folgen; zeigt Podcasts und Bilder, die Basic neu kann (das Radio zeigt schon das Gerätebild)
  await geraet(1440, 900, 1, false);
  await oeffnen(APP, "podcasts", { radiohub_sprache: "de", radiohub_thema: "dunkel" });
  await bisDa(`!!document.querySelector(".rh-podcast-leiste")`, "Podcasts", 300);
  const kennung = await aboAnlegen();
  await rufe("Page.navigate", { url: `${APP}podcasts/${kennung}` });
  await bisDa(`document.querySelectorAll(".rh-folge").length > 3 && [...document.querySelectorAll(".rh-folge img")].slice(0, 6).every((b) => b.complete)`, "Folgen mit Bildern", 2500);
  await aufnehmen(BASIC_BILD);
  await seite.schliesse();
  process.exit(0);
}

let stand = existsSync(STAND) ? JSON.parse(readFileSync(STAND, "utf-8")) : {};
if (MIT("rechner")) {
  // 1. Rechner: Radio hell, ein Sender spielt (Anzeige mit Name und Titel); in PRO mit der Sitzung des Probebetriebs
  await geraet(1600, 1000, 2, false);
  await oeffnen(RECHNER, "radio", { radiohub_sprache: "de", radiohub_thema: "hell", ...(SITZUNG ? { radiohub_sitzung: SITZUNG } : {}) });
  await bisDa(`document.querySelectorAll(".rh-sender-kern").length > 5`, "Senderliste");
  await auswerten(`document.querySelector(".rh-sender-kern").click(); true`);
  await warte(8000);   // Strom verbunden, Anzeige mit Name und Titel
  await aufnehmen(join(ORDNER, "rechner.png"));
}
if (MIT("telefon")) {
  // 2. Telefon: dunkel, das Abo morfCast + chill, die neueste Folge im großen Spieler
  // so hoch wie der Bildschirm in der Präsentation (382 x 873 bei 0,9795), oben der sichere Rand unter der Statusleiste
  await geraet(390, 891, 3, true);
  await rufe("Emulation.setSafeAreaInsetsOverride", { insets: { top: 47, topMax: 47, bottom: 0, bottomMax: 0, left: 0, leftMax: 0, right: 0, rightMax: 0 } })
    .catch((f) => console.warn("ohne sicheren Rand:", f.message));
  await oeffnen(APP, "podcasts", { radiohub_sprache: "de", radiohub_thema: "dunkel" });
  await bisDa(`!!document.querySelector(".t-reiter")`, "Telefonansicht", 300);
  const kennung = await aboAnlegen();
  await rufe("Page.navigate", { url: `${APP}podcasts/${kennung}` });
  await bisDa(`document.querySelectorAll(".tp-folge").length > 0`, "Folgen");
  await auswerten(`document.querySelector(".tp-folge .tf-aktionen button").click(); true`);
  await bisDa(`!!document.querySelector(".leiste-info")`, "Spielerleiste", 2500);
  await auswerten(`document.querySelector(".leiste-info").click(); true`);
  await bisDa(`!!document.querySelector(".vollbild .buehne h2")`, "großer Spieler", 3000);
  stand = await auswerten(`({ titel: document.querySelector(".vollbild .buehne h2")?.textContent?.trim() ?? "",
    podcast: document.querySelector(".vollbild .buehne .zusatz")?.textContent?.trim() ?? "",
    bild: document.querySelector(".vollbild .tf-cover img")?.src ?? "",
    zeit: new Date().toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) })`);
  await aufnehmen(join(ORDNER, "telefon.png"));
  writeFileSync(STAND, JSON.stringify(stand, null, 2) + "\n");
}

// 3. Bühne: Geräte zeichnen, Aufnahmen einsetzen, freigestellt aufnehmen
await geraet(2400, 1400, 1, false);
await rufe("Emulation.setDefaultBackgroundColorOverride", { color: { r: 0, g: 0, b: 0, a: 0 } });
const buehne = pathToFileURL(join(WURZEL, "docs/readme-bild/buehne.html")).href + "?" + new URLSearchParams(stand);
await rufe("Page.navigate", { url: buehne });
await bisDa(`document.fonts.status === "loaded" && [...document.images].every((b) => b.complete)`, "Bühne", 800);
await aufnehmen(ZIEL);

for (const w of warnungen) console.warn("Seite meldet:", w);
await seite.schliesse();
