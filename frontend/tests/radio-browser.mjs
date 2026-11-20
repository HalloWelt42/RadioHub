// Ansichtsprüfung der Radio-Ansichten (RAD-7) im Probebetrieb (Kopie der Daten): jede Ansicht in allen Breiten, hell und dunkel,
// Schrift normal und sehr groß, Vorlage HiFi und Klassisch. Misst seitliches Rollen, Überlauf, abgeschnittene
// Bedienelemente, umbrechende Knöpfe, ungleiche Tastenreihen, Konsolenfehler, Antworten ab 400.
// Aufruf bei laufendem Probebetrieb (Backend auf einer Kopie der Daten, Oberfläche per npm run dev):
//   RADIOHUB_OBERFLAECHE=http://127.0.0.1:5180 node frontend/tests/radio-browser.mjs [--bilder ORDNER] [--nur NAME] [--breiten 375,1280] [--gegentest]
import fs from "node:fs";
import { oeffneSeite } from "../node_modules/appkern-oberflaeche/oberflaeche/werkzeuge/browser.mjs";

const BASIS = process.env.RADIOHUB_OBERFLAECHE ?? "http://localhost:5180";
const arg = (n) => { const i = process.argv.indexOf(n); return i > 0 ? process.argv[i + 1] : null; };
const BILDER = arg("--bilder");
const NUR = arg("--nur");
const BREITEN = (arg("--breiten") ?? "375,768,900,1024,1280,1532,1920").split(",").map(Number);
const HOEHE = (b) => (b === 375 ? 812 : b === 768 ? 1024 : b >= 1900 ? 1080 : b >= 1500 ? 900 : 800);
const NEUTRAL = `(() => { for (const el of document.querySelectorAll('.rh-logo-bild.mit-bild')) { const z = el.closest('.rh-sender, .tf-sender, .rh-a-zeile'); const n = (z?.querySelector('b')?.textContent ?? '?').replace(/[^\\p{L}\\p{N} ]/gu, ' ').trim().split(/\\s+/); el.classList.remove('mit-bild'); el.textContent = n.slice(0, 2).map((t) => t[0] ?? '').join('').toUpperCase(); } return 1; })()`;
const UUID = "9605edb3-0601-11e8-ae97-52543be04c81";
// Ansichten: Pfad und was danach geschieht (Zustand herstellen)
const SEITEN = [
  { name: "radio", pfad: "/radio?land=DE" },
  { name: "radio-details", pfad: `/radio/78012206-1aa1-11e9-a80b-52543be04c81?land=DE&land=AT&land=CH&genre=Pop&genre=Rock&genre=Dance&qualitaet=mittel&qualitaet=hoch&codec=MP3&stimmen=10&bitrate=128&erreichbar=0&favoriten=1`,
    nach: `document.querySelector('.rh-varianten-knopf:not(.rh-varianten-knopf-schmal)')?.click(); 1`, rechner: true },
  { name: "radio-lang", pfad: "/radio?land=DE&sort=name", nach: `document.querySelectorAll('.rh-sender .rh-aktionen > button:last-child')[1]?.click(); 1` },
  { name: "radio-tafel", pfad: "/radio?land=DE", nach: `document.querySelector('.rh-filter-auf')?.click(); 1`, nurBreiten: [900, 1024] },
  { name: "regeln", pfad: "/einstellungen/radio/regeln", rechner: true },
  { name: "regeln-vorschau", pfad: "/einstellungen/radio/regeln", rechner: true,
    nach: `(async () => { [...document.querySelectorAll('.rh-arten button')][0].click(); const i = document.querySelector('.rh-neu input[type=search]'); i.value = 'chin'; i.dispatchEvent(new Event('input', {bubbles: true})); await new Promise(r => setTimeout(r, 1500)); document.querySelector('.rh-neu').scrollIntoView(); return 1; })()` },
  { name: "ausgeblendet", pfad: "/einstellungen/radio/ausgeblendet", rechner: true },
  { name: "laender", pfad: "/einstellungen/radio/laender", rechner: true },
  { name: "werbung", pfad: "/einstellungen/radio/werbung", rechner: true },
  { name: "abgleich", pfad: "/einstellungen/radio/abgleich", rechner: true },
  { name: "kategorien", pfad: "/einstellungen/radio/kategorien", rechner: true },
  { name: "telefon-blatt", pfad: "/radio?land=DE&genre=Pop", telefon: true, nach: `[...document.querySelectorAll('.t-suche .knopf')].pop()?.click(); 1` },
];
const VARIANTEN = [];
for (const vorlage of ["hifi", "klassisch"]) for (const thema of ["dunkel", "hell"]) for (const schrift of ["mittel", "sehr-gross"])
  for (const b of BREITEN) if (vorlage === "hifi" || [375, 1280].includes(b)) VARIANTEN.push({ vorlage, thema, schrift, b });

const MESSEN = `(() => {
  const befunde = [];
  const w = innerWidth, h = innerHeight;
  const name = (el) => el.id ? '#' + el.id : el.tagName.toLowerCase() + (el.classList.length ? '.' + [...el.classList].slice(0, 2).join('.') : '');
  const pfad = (el) => { const t = []; for (let e = el; e && e !== document.body && t.length < 4; e = e.parentElement) t.unshift(name(e)); return t.join(' > '); };
  if (document.documentElement.scrollWidth > w + 1) befunde.push('Seite rollt seitlich: ' + document.documentElement.scrollWidth + ' > ' + w);
  const sichtbar = (el) => { const s = getComputedStyle(el); if (s.visibility === 'hidden' || s.display === 'none') return false; const r = el.getBoundingClientRect(); return r.width > 0 && r.height > 0 && el.closest('[hidden]') === null; };
  // Rollfelder mit verstecktem seitlichem Überlauf
  for (const el of document.querySelectorAll('*')) {
    const s = getComputedStyle(el);
    if (!['auto', 'scroll', 'hidden', 'clip'].includes(s.overflowX) && !['auto', 'scroll'].includes(s.overflowY)) continue;
    if (!sichtbar(el)) continue;
    if (s.textOverflow === 'ellipsis') continue;
    if (el.closest('ak-segmente, ak-pegel, ak-schirm, ak-dreh, ak-schieber, .ak-dreh-koerper')) continue;
    if (el.scrollWidth > el.clientWidth + 2) befunde.push('Überlauf seitlich in ' + pfad(el) + ': ' + el.scrollWidth + ' > ' + el.clientWidth);
  }
  // Überschriften und Etiketten ganz lesbar: gekürzt mit Auslassungspunkten nur Inhalte wie Sendernamen, nie Titel
  for (const el of document.querySelectorAll('h1, h2, h3, .ak-geraet-kopf b, .ak-etikett, .rh-gruppe-kopf h3, .rh-spaltenkopf span')) {
    if (!sichtbar(el)) continue;
    if (el.scrollWidth > el.clientWidth + 1) befunde.push('Überschrift gekürzt: ' + pfad(el) + ' "' + el.textContent.trim().slice(0, 30) + '"');
  }
  // Bedienelemente: im Fenster und nicht über den Rand eines abschneidenden Vorfahren hinaus (seitlich)
  const bedien = document.querySelectorAll('button, a, input, .chip, ak-dreh, ak-schieber, ak-taster, ak-wahl, label.rh-facette');
  for (const el of bedien) {
    if (!sichtbar(el)) continue;
    const r = el.getBoundingClientRect();
    if (el.closest('.rh-telefon')) {
      const f = el.closest('.rh-telefon').getBoundingClientRect();
      if (r.right > f.right + 1 || r.left < f.left - 1) befunde.push('ragt aus dem Telefon: ' + pfad(el));
      continue;
    }
    if (r.right > w + 1 || r.left < -1) { befunde.push('außerhalb des Fensters: ' + pfad(el) + ' (' + Math.round(r.left) + '..' + Math.round(r.right) + ')'); continue; }
    for (let a = el.parentElement; a && a !== document.body; a = a.parentElement) {
      const s = getComputedStyle(a);
      if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
      const ra = a.getBoundingClientRect();
      if (r.right > ra.right + 1.5 || r.left < ra.left - 1.5) befunde.push('abgeschnitten seitlich: ' + pfad(el) + ' in ' + name(a));
      break;
    }
  }
  // Knöpfe, deren Text umbricht (Zeilen über Textknoten)
  for (const el of document.querySelectorAll('button, .knopf, .chip, .rh-nav-knopf, .auswahl-knopf')) {
    if (!sichtbar(el) || el.closest('.rh-treffer, .rh-variante, .auswahl-liste, .t-geraet, .rh-facette, ak-taster')) continue;
    const rechtecke = [];
    const tw = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    for (let n = tw.nextNode(); n; n = tw.nextNode()) { if (!n.textContent.trim()) continue; const rg = document.createRange(); rg.selectNodeContents(n); for (const q of rg.getClientRects()) if (q.width > 1) rechtecke.push(q); }
    // Zeilen: Rechtecke, die sich senkrecht nicht überlappen, liegen auf verschiedenen Zeilen
    rechtecke.sort((x, y) => x.top - y.top);
    let zeilen = 0, unten = -1e9;
    for (const q of rechtecke) { if (q.top >= unten - 3) { zeilen++; unten = q.bottom; } else unten = Math.max(unten, q.bottom); }
    if (zeilen > 1) befunde.push('Knopftext bricht um: ' + pfad(el) + ' "' + el.textContent.trim().slice(0, 30) + '"');
  }
  // Tastenreihen: alle Tasten einer Reihe gleich hoch und auf einer Grundlinie (getBoundingClientRect)
  const REIHEN = '.rh-steuerung, .t-transport, .rh-kanzel-kompakt, .t-spieler, .rh-nav-schiene, .rh-kopf-rechts, .rh-werkzeug-zeile, .rh-aktiv-chips, .rh-aktionen, .rh-zeit-knoepfe, .rh-haus-knoepfe, .t-suche, .t-chips, .rh-vorschau-knoepfe, .rh-arten, .t-blatt-kopf, .rh-puffer-zeile, .rh-schrift-wahl, .rh-a-werkzeug, .rh-seiten, .t-kopf-rechts, .rh-bewerten, .t-versatz';
  for (const reihe of document.querySelectorAll(REIHEN)) {
    if (!sichtbar(reihe)) continue;
    const tasten = [...reihe.querySelectorAll(':scope > button, :scope > a.knopf, :scope > .rh-nav-knopf, :scope > .chip, :scope > .suche, :scope > label.suche, :scope > .auswahl > .auswahl-knopf, :scope > ak-taster > .ak-taster-knopf, :scope > span > button.rund, :scope > span > button.knopf, :scope > .rh-status, :scope > .rh-darstellung > .knopf, :scope > .rh-hinweis, :scope > .t-treffer, :scope > .t-haus-mini, :scope > .rh-stern')].filter(sichtbar);
    // Zeilen bilden (umgebrochene Reihen getrennt prüfen)
    const zeilen = [];
    for (const k of tasten) { const r = k.getBoundingClientRect(); let z = zeilen.find((x) => r.top < x.unten - 4 && r.bottom > x.oben + 4); if (!z) zeilen.push(z = { oben: r.top, unten: r.bottom, liste: [] }); z.liste.push([k, r]); z.oben = Math.min(z.oben, r.top); z.unten = Math.max(z.unten, r.bottom); }
    for (const z of zeilen) {
      if (z.liste.length < 2) continue;
      const hoehen = z.liste.map(([, r]) => Math.round(r.height)), boeden = z.liste.map(([, r]) => Math.round(r.bottom));
      if (Math.max(...hoehen) - Math.min(...hoehen) > 1 || Math.max(...boeden) - Math.min(...boeden) > 1)
        befunde.push('ungleiche Tasten in ' + pfad(reihe) + ': Höhen ' + hoehen.join('/') + ', Unterkanten ' + boeden.join('/'));
    }
  }
  return befunde;
})()`;

const seite = await oeffneSeite({ frist: 60000 });
let fehler = [];
seite.beiEreignis((m) => {
  if (m.method === "Runtime.exceptionThrown") fehler.push("Ausnahme: " + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(m.params.type)) fehler.push("Konsole: " + m.params.args.map((a) => a.value ?? a.description).join(" ").slice(0, 200));
  if (m.method === "Network.responseReceived" && m.params.response.status >= 400 && !m.params.response.url.includes("/api/favicon/")) fehler.push("Netz " + m.params.response.status + ": " + m.params.response.url);
});
for (const d of ["Runtime.enable", "Network.enable", "Page.enable"]) await seite.rufe(d);
const warte = (ms) => new Promise((r) => setTimeout(r, ms));
const werte = async (a) => (await seite.rufe("Runtime.evaluate", { expression: a, returnByValue: true, awaitPromise: true })).result?.result?.value;
await seite.rufe("Emulation.setDeviceMetricsOverride", { width: 1280, height: 800, deviceScaleFactor: 1, mobile: false });
await seite.rufe("Page.navigate", { url: BASIS + "/radio" });
await warte(1500);
let befundeGesamt = 0, laeufe = 0;
for (const s of SEITEN) {
  if (NUR && s.name !== NUR) continue;
  for (const v of VARIANTEN) {
    if (s.rechner && v.b < 900) continue;
    if (s.telefon && v.b >= 900) continue;
    if (s.nurBreiten && !s.nurBreiten.includes(v.b)) continue;
    const telefon = v.b < 900;
    await werte(`localStorage.setItem('radiohub_sitzung','sitzung-probebetrieb'); localStorage.setItem('radiohub_thema','${v.thema}'); localStorage.setItem('radiohub_schrift','${v.schrift}'); localStorage.setItem('appkern_vorlage','${v.vorlage}'); 1`);
    await seite.rufe("Emulation.setDeviceMetricsOverride", { width: v.b, height: HOEHE(v.b), deviceScaleFactor: 1, mobile: telefon });
    await seite.rufe("Emulation.setTouchEmulationEnabled", { enabled: telefon, maxTouchPoints: telefon ? 5 : 1 });
    await seite.rufe("Emulation.setEmulatedMedia", { features: [{ name: "pointer", value: telefon ? "coarse" : "fine" }, { name: "hover", value: telefon ? "none" : "hover" }] });
    fehler = [];
    await seite.rufe("Page.navigate", { url: BASIS + s.pfad });
    await warte(2600);
    if (s.nach) { await werte(s.nach); await warte(1600); }
    const ansicht = await werte(`document.querySelector('.rh-telefon') ? 'telefon' : 'rechner'`);
    const befunde = [...(await werte(MESSEN)) ?? ["Messung fehlgeschlagen"], ...fehler, ...(ansicht !== (telefon ? "telefon" : "rechner") ? ["falsche Ansicht: " + ansicht] : [])];
    laeufe++;
    const kennung = `${s.name} ${v.b} ${v.thema} ${v.schrift} ${v.vorlage}`;
    if (befunde.length) { befundeGesamt += befunde.length; console.log("BEFUND", kennung, "\n  " + [...new Set(befunde)].slice(0, 12).join("\n  ")); }
    if (BILDER && (v.vorlage === "hifi" ? (v.schrift === "mittel" || [375, 1280].includes(v.b)) : true)) {
      await werte(NEUTRAL); await warte(150);
      const r = await seite.rufe("Page.captureScreenshot", { format: "png" });
      fs.writeFileSync(`${BILDER}/${s.name}-${v.b}-${v.thema}${v.schrift === "mittel" ? "" : "-sehr-gross"}${v.vorlage === "hifi" ? "" : "-" + v.vorlage}.png`, Buffer.from(r.result.data, "base64"));
    }
  }
}
console.log(`FERTIG ${laeufe} Ansichten, ${befundeGesamt} Befunde`);
await seite.schliesse();
