// Browserprüfung der Kanzel (RAD-8) im unsichtbaren Chrome des Appkerns (stumm, Wegwerfprofil) gegen den Probebetrieb:
//   matrix  alle Breiten (900, 1024, 1280, 1532, 1920), Schriftstufen, Hell und Dunkel, Vorlagen HiFi und Klassisch, jeder
//           Zustand; misst seitliches Rollen, Hinausragen, Abschneiden, überlappende Module, gleich hohe Tasten, Größe der
//           Rasteranzeigen und ob das Lautstärkegehäuse das Ende der Liste verdeckt; legt Bilder ab
//   ablauf  jede Bedienfunktion der alten Leiste mit echter Wiedergabe (Kennungen F01 ... wie docs/umbau/RAD-8-funktionen.md)
// Zustände ohne echte Quelle setzt die Prüfung über dieselben Module wie die App (gleiche Adresse samt ?t=).
//   RADIOHUB_OBERFLAECHE=http://127.0.0.1:5180 node frontend/tests/kanzel-browser.mjs matrix|ablauf [Bilderordner]
// Voraussetzung: Probebetrieb (backend/tests/probebetrieb.py) und Vite mit Proxy darauf; Anmeldung sitzung-probebetrieb.
import fs from "node:fs";
import path from "node:path";
import { oeffneSeite } from "../node_modules/appkern-oberflaeche/oberflaeche/werkzeuge/browser.mjs";

const BASIS = process.env.RADIOHUB_OBERFLAECHE ?? "http://127.0.0.1:5180";
const art = process.argv[2] ?? "matrix";
const HIER = path.dirname(new URL(import.meta.url).pathname);
const AUS = process.argv[3] ?? path.join(HIER, "../../docs/umbau/bilder/rad-8");
fs.mkdirSync(AUS, { recursive: true });

const seite = await oeffneSeite({ frist: 90000 });
const fehler = [];
seite.beiEreignis((m) => {
  if (m.method === "Runtime.exceptionThrown") fehler.push(m.params.exceptionDetails?.exception?.description ?? m.params.exceptionDetails?.text);
  if (m.method === "Runtime.consoleAPICalled" && m.params.type === "error") fehler.push(m.params.args.map((a) => a.value ?? a.description).join(" "));
});
await seite.rufe("Runtime.enable");
await seite.rufe("Page.enable");
await seite.rufe("Network.enable");
const anfragen = [];
seite.beiEreignis((m) => { if (m.method === "Network.requestWillBeSent") anfragen.push(m.params.request.url); });

async function werte(ausdruck) {
  const r = await seite.rufe("Runtime.evaluate", { expression: ausdruck, returnByValue: true, awaitPromise: true });
  if (r.error) throw new Error(r.error.message);
  if (r.result.exceptionDetails) throw new Error(r.result.exceptionDetails.exception?.description ?? r.result.exceptionDetails.text);
  return r.result.result.value;
}
const warte = (ms) => new Promise((r) => setTimeout(r, ms));
async function bis(ausdruck, ms = 20000) {
  const ende = Date.now() + ms;
  while (Date.now() < ende) { if (await werte(ausdruck)) return true; await warte(200); }
  return false;
}

async function laden(breite, hoehe, d) {
  await seite.rufe("Emulation.setDeviceMetricsOverride", { width: breite, height: hoehe, deviceScaleFactor: 1, mobile: false });
  await seite.rufe("Page.navigate", { url: `${BASIS}/health` });
  await warte(300);
  await werte(`localStorage.setItem("radiohub_sitzung","sitzung-probebetrieb"); localStorage.setItem("radiohub_volume","1");
    localStorage.setItem("radiohub_thema","${d.thema}"); localStorage.setItem("radiohub_schrift","${d.schrift}"); localStorage.setItem("appkern_vorlage","${d.vorlage}"); 1`);
  await seite.rufe("Page.navigate", { url: `${BASIS}/radio` });
  if (!(await bis(`!!document.querySelector(".rh-kanzel ak-taster .ak-taster-knopf") && (document.querySelectorAll(".station-wrapper").length > 0)`, 30000))) throw new Error("App lädt nicht");
  await werte(HILFEN);
  await warte(400);
}

// Werkzeuge in der Seite: dieselben Module wie die App (gleiche Adresse samt ?t=), Zustände setzen, messen
const HILFEN = `(async () => {
  const url = (teil) => performance.getEntriesByType("resource").map((e) => e.name).find((n) => n.includes(teil)) ?? teil;
  const store = await import(url("/src/lib/store.svelte.js"));
  const engine = await import(url("/src/lib/playerEngine.js"));
  const api = (await import(url("/src/lib/api.js"))).api;
  const a = store.appState;
  const audio = () => document.querySelector("audio");
  const LANG = "Deutschlandfunk Dokumente und Debatten | DLF | AAC 192k";
  const TITEL = "Crosby, Stills, Nash & Young - Ohio";
  const sender = { uuid: "rad8-probe", name: LANG, codec: "AAC", bitrate: 192, icy: false };
  const grund = { isPlaying: false, isPaused: false, isRecording: false, playerMode: "none", currentStation: null, currentEpisode: null, currentRecording: null,
    streamTitle: null, streamQuality: null, hlsStatus: null, hlsActive: false, isLive: true, currentSegment: null, recordingElapsed: 0, recordingIcyCount: 0,
    canPlayHLS: null, canPlayDirect: true };
  const hls = { first_segment: 100, last_segment: 1900, segment_duration: 1, buffered_seconds: 1800, max_segments: 1800 };
  let folgen = null;
  const PODCAST = { id: 21, title: "15 Minuten. Der tagesschau-Podcast am Morgen" };
  async function bisPosition() {
    const ende = Date.now() + 12000;
    while (Date.now() < ende && !(audio().duration > 0 && audio().currentTime > 0.5)) await new Promise((r) => setTimeout(r, 100));
    if (audio().duration > 120) { audio().currentTime = audio().duration * 0.38; await new Promise((r) => setTimeout(r, 900)); }
  }
  async function folge() {
    folgen ??= (await api.getEpisodes(21, 3)).episodes;
    return folgen[0];
  }
  async function podcastSpielen() {
    await engine.playPodcast(await folge(), PODCAST);
    await bisPosition();
  }
  async function aufnahmeSpielen() {
    const f = await folge();
    await engine.playRecording({ name: "Mitschnitt 17.11.2026 07:15", session_id: "rad8", station_name: "Deutschlandfunk Kultur", playUrl: api.getEpisodeStreamUrl(f.id), source: "cutter" });
    await bisPosition();
  }
  async function zustand(name) {
    await engine.stop();
    Object.assign(a, grund);
    const ab = (ev) => audio().dispatchEvent(new Event(ev));
    switch (name) {
      case "leer": break;
      case "laedt": Object.assign(a, { currentStation: sender, isPlaying: true, playerMode: "direct" }); ab("loadstart"); break;
      case "direkt": Object.assign(a, { currentStation: sender, isPlaying: true, playerMode: "direct", streamTitle: TITEL, canPlayHLS: true }); ab("loadstart"); ab("playing"); break;
      case "live": Object.assign(a, { currentStation: sender, isPlaying: true, playerMode: "hls", hlsActive: true, hlsStatus: hls, isLive: true, currentSegment: 1900,
        streamQuality: { inputCodec: "aac", inputBitrate: 192, outputBitrate: 192 }, streamTitle: TITEL, canPlayHLS: true }); ab("loadstart"); ab("playing"); break;
      case "versatz": Object.assign(a, { currentStation: sender, isPlaying: true, playerMode: "hls", hlsActive: true, hlsStatus: hls, isLive: false, currentSegment: 1648,
        streamQuality: { inputCodec: "aac", inputBitrate: 192, outputBitrate: 192 }, streamTitle: TITEL, canPlayHLS: true }); ab("loadstart"); ab("playing"); break;
      case "pause": Object.assign(a, { currentStation: sender, isPlaying: true, isPaused: true, playerMode: "hls", hlsActive: true, hlsStatus: hls, isLive: false,
        currentSegment: 1880, streamTitle: TITEL }); ab("playing"); break;
      case "aufnahme": Object.assign(a, { currentStation: sender, isPlaying: true, playerMode: "hls", hlsActive: true, hlsStatus: hls, isLive: true, currentSegment: 1900,
        isRecording: true, recordingElapsed: 768, recordingIcyCount: 3, streamQuality: { inputCodec: "aac", inputBitrate: 192, outputBitrate: 192 }, streamTitle: TITEL });
        ab("playing"); break;
      case "podcast": await podcastSpielen(); break;
      case "wiedergabe": await aufnahmeSpielen(); break;
      case "fehler": await engine.playStation({ uuid: "rad8-gibt-es-nicht", name: LANG, codec: "MP3", bitrate: 128 });
        { const ende = Date.now() + 6000; while (Date.now() < ende && document.querySelector(".rh-kanzel")?.dataset.zustand !== "fehler") await new Promise((r) => setTimeout(r, 100)); }
        break;
    }
    await new Promise((r) => setTimeout(r, 450));
    return document.querySelector(".rh-kanzel").dataset.zustand;
  }
  function beschreibe(el) {
    return el.tagName.toLowerCase() + (el.className && typeof el.className === "string" ? "." + el.className.trim().split(/\\s+/).join(".") : "") + (el.textContent ? " '" + el.textContent.trim().slice(0, 30) + "'" : "");
  }
  function messen() {
    const k = document.querySelector(".rh-kanzel"), kr = k.getBoundingClientRect();
    const befunde = [], hinweise = [];
    if (document.documentElement.scrollWidth > innerWidth + 0.5) befunde.push("seitliches Rollen " + document.documentElement.scrollWidth);
    for (const el of k.querySelectorAll("*")) {
      if (el.closest("svg") && el.tagName !== "svg") continue;
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height || getComputedStyle(el).visibility === "hidden") continue;
      if (r.right > innerWidth + 0.5 || r.left < -0.5) befunde.push("ragt seitlich hinaus: " + beschreibe(el));
      if (r.bottom > innerHeight + 0.5) befunde.push("ragt unten hinaus: " + beschreibe(el));
    }
    const gewollt = ".rh-display-titel, .rh-puffer > span";
    for (const el of k.querySelectorAll(".knopf, .auswahl-knopf, .auswahl-text, .rh-display-zeile > span, .ak-etikett, .rh-vu, .ak-dreh-wert, " + gewollt)) {
      if (el.scrollWidth > el.clientWidth + 1) (el.matches(gewollt) ? hinweise : befunde).push("abgeschnitten: " + beschreibe(el));
    }
    const module = [...k.querySelectorAll(".rh-modul")].map((m) => [m.className, m.getBoundingClientRect()]);
    for (let i = 0; i < module.length; i++) for (let j = i + 1; j < module.length; j++) {
      const [na, ra] = module[i], [nb, rb] = module[j];
      if (ra.left < rb.right - 1 && rb.left < ra.right - 1 && ra.top < rb.bottom - 1 && rb.top < ra.bottom - 1) befunde.push("Module überlappen: " + na + " / " + nb);
    }
    // Tasten der Steuerung und Tasten der Bitrate: je Reihe eine Grundlinie, alle exakt gleich hoch (die Leiste darf in
    // schmalen Fenstern in eine zweite Reihe gehen)
    const tasten = [...k.querySelectorAll(".rh-transport ak-taster .ak-taster-knopf")].map((b) => b.getBoundingClientRect());
    const leiste = [...k.querySelectorAll(".rh-betrieb-tasten ak-taster .ak-taster-knopf")].map((b) => b.getBoundingClientRect());
    // Transport: eine Reihe, alle gleich hoch auf einer Linie; die kleinen Taster daneben untereinander gleich groß
    const hoehen = [...new Set(tasten.map((r) => r.height.toFixed(2)))], oben = [...new Set(tasten.map((r) => r.top.toFixed(2)))];
    const klein = [...new Set(leiste.map((r) => r.height.toFixed(2) + "x" + r.width.toFixed(2)))];
    if (hoehen.length !== 1 || oben.length !== 1) befunde.push("Transporttasten ungleich: Höhen " + hoehen.join("/") + ", oben " + oben.join("/"));
    if (klein.length !== 1) befunde.push("kleine Taster ungleich: " + klein.join("/"));
    const reihen = k.querySelector(".rh-betrieb").getBoundingClientRect().top > tasten[0].bottom ? 2 : 1;
    const knoepfe = [...k.querySelectorAll(".rh-puffer-zeile .knopf")].map((b) => b.getBoundingClientRect().height.toFixed(2));
    if (new Set(knoepfe).size > 1) befunde.push("Knöpfe der Zeile ungleich: " + knoepfe.join("/"));
    const laut = k.querySelector(".rh-laut").getBoundingClientRect();
    // Liste: ganz nach unten gerollt darf ihre letzte Zeile nicht unter dem Gehäuse liegen
    const rollfeld = [...document.querySelectorAll(".rh-mitte *")].find((e) => { const s = getComputedStyle(e); return /(auto|scroll)/.test(s.overflowY) && e.scrollHeight > e.clientHeight + 4 && e.querySelector(".station-wrapper"); });
    let verdeckt = null;
    if (rollfeld) {
      rollfeld.scrollTop = rollfeld.scrollHeight;
      const zeilen = rollfeld.querySelectorAll(".station-wrapper"), letzte = zeilen[zeilen.length - 1]?.getBoundingClientRect();
      if (letzte && letzte.bottom > laut.top + 1 && letzte.right > laut.left && letzte.left < laut.right) verdeckt = Math.round(letzte.bottom - laut.top);
      rollfeld.scrollTop = 0;
    }
    if (verdeckt) befunde.push("letzte Zeile der Liste unter dem Gehäuse: " + verdeckt + " px");
    const glyph = (sel) => { const e = k.querySelector(sel); const svg = e?.querySelector("svg"); return e ? { stellen: e.getAttribute("stellen"), breite: Math.round(e.getBoundingClientRect().width), zeichen: svg ? Math.round(svg.getBoundingClientRect().height * 10) / 10 : 0 } : null; };
    const raster = { matrix: glyph(".rh-display-quelle ak-segmente"), quelle: glyph(".rh-zeit-quelle"), zeit: glyph(".rh-zeit-uhr") };
    for (const [n, g] of Object.entries(raster)) if (g && g.zeichen < 14) befunde.push("Rasteranzeige winzig: " + n + " " + g.zeichen + " px");
    const ziel = parseFloat(getComputedStyle(k.querySelector(".rh-display-quelle")).getPropertyValue("--rh-matrix-zeichen"));
    if (raster.matrix && raster.matrix.zeichen < ziel * 0.85) befunde.push("Punktmatrix kleiner als ihre Zeichenhöhe: " + raster.matrix.zeichen + " statt " + ziel + " px");
    return { raster, reihen, kanzel: { top: Math.round(kr.top), hoehe: Math.round(kr.height) }, ueberstand: Math.round(kr.top - laut.top), tastenHoehe: hoehen[0],
      flaechen: getComputedStyle(k.querySelector(".rh-kanzel-voll")).gridTemplateAreas, audios: document.querySelectorAll("audio").length, befunde, hinweise };
  }
  window.__rad8 = { zustand, messen, a, engine, api, audio, aufnahmeSpielen, podcastSpielen };
  return 1;
})()`;

async function foto(datei, ueber = 70) {
  const r = await werte(`(() => { const r = document.querySelector(".rh-kanzel").getBoundingClientRect(); return { y: r.top, h: r.height, w: innerWidth }; })()`);
  const y = Math.max(0, r.y - ueber);
  const bild = await seite.rufe("Page.captureScreenshot", { format: "png", clip: { x: 0, y, width: r.w, height: r.y + r.h - y, scale: 1 } });
  fs.writeFileSync(path.join(AUS, datei), Buffer.from(bild.result.data, "base64"));
}
async function ganzFoto(datei) {
  const bild = await seite.rufe("Page.captureScreenshot", { format: "png" });
  fs.writeFileSync(path.join(AUS, datei), Buffer.from(bild.result.data, "base64"));
}

const ZUSTAENDE = ["leer", "laedt", "direkt", "live", "versatz", "pause", "podcast", "wiedergabe", "aufnahme", "fehler"];
const FOTOS = {
  "1920|mittel|dunkel|hifi": ZUSTAENDE,
  "1280|mittel|hell|hifi": ["live", "versatz", "aufnahme", "podcast", "fehler"],
  "1280|mittel|dunkel|hifi": ["versatz"],
  "1920|mittel|hell|hifi": ["versatz"],
  "1024|sehr-gross|dunkel|hifi": ["live", "versatz", "podcast", "aufnahme"],
  "1532|gross|hell|klassisch": ["live", "podcast"],
  "900|sehr-gross|hell|hifi": ["versatz"],
};

try {
  if (art === "matrix") {
    const zeilen = [];
    let anzahl = 0, mitBefund = 0;
    for (const vorlage of ["hifi", "klassisch"]) for (const thema of ["dunkel", "hell"]) for (const schrift of ["mittel", "gross", "sehr-gross"])
      for (const breite of [900, 1024, 1280, 1532, 1920]) {
        const schluessel = `${breite}|${schrift}|${thema}|${vorlage}`;
        if (process.env.NUR && !process.env.NUR.split(",").includes(schluessel)) continue;
        await laden(breite, breite >= 1440 ? 1000 : 800, { thema, schrift, vorlage });
        for (const z of ZUSTAENDE) {
          const ist = await werte(`window.__rad8.zustand("${z}")`);
          const m = await werte(`window.__rad8.messen()`);
          anzahl++;
          const erwartet = z === "direkt" ? "live" : z;
          if (ist !== erwartet) m.befunde.push(`Zustand ${ist} statt ${erwartet}`);
          if (m.audios !== 1) m.befunde.push(`${m.audios} Audio-Elemente`);
          if (m.befunde.length) mitBefund++;
          zeilen.push({ schluessel, z, ...m });
          if (FOTOS[schluessel]?.includes(z)) await foto(`kanzel-${breite}-${thema}-${schrift}-${vorlage}-${z}.png`);
        }
        if (schluessel === "1920|mittel|dunkel|hifi") { await werte(`window.__rad8.zustand("live")`); await ganzFoto("rechner-1920-dunkel-live.png"); }
        process.stdout.write(`${schluessel} `);
      }
    fs.writeFileSync(path.join(AUS, "matrix.json"), JSON.stringify(zeilen, null, 1));
    console.log(`\n${anzahl} Ansichten, ${mitBefund} mit Befund`);
    for (const z of zeilen.filter((x) => x.befunde.length)) console.log(z.schluessel, z.z, z.befunde.join("; "));
    const hin = zeilen.filter((x) => x.hinweise.length);
    console.log(`${hin.length} Ansichten mit gewollter Kürzung (Titel, Angabe)`);
    console.log("Überstand je Stufe:", [...new Set(zeilen.map((x) => `${x.schluessel.split("|")[0]}/${x.schluessel.split("|")[1]}: ${x.ueberstand}`))].join(", "));
  }

  if (art === "ablauf") {
    const erg = [];
    const pruefe = async (id, was, ausdruck) => {
      let ok = false, info = "";
      try { const r = await werte(ausdruck); ok = r === true || (r && r.ok === true); info = r && typeof r === "object" ? JSON.stringify(r) : String(r); }
      catch (f) { info = String(f.message).slice(0, 200); }
      erg.push({ id, was, ok, info }); console.log(ok ? "OK  " : "FEHL", id, was, ok ? "" : info.slice(0, 300));
    };
    const K = (sel) => `document.querySelector(".rh-kanzel ${sel}")`;
    const taste = (n) => `document.querySelectorAll(".rh-steuerung ak-taster")[${n}]`;
    const druecke = (n) => `${taste(n)}.querySelector("button").click()`;
    const R = "window.__rad8";
    await laden(1920, 1000, { thema: "dunkel", schrift: "mittel", vorlage: "hifi" });
    // Sender suchen, der spielt
    const sender = await werte(`(async () => { const a = ${R}.a; for (let i = 0; i < Math.min(12, a.stations.length); i++) {
      await ${R}.engine.playStation(a.stations[i]); const ende = Date.now() + 9000;
      while (Date.now() < ende) { if (document.querySelector(".rh-kanzel").dataset.zustand === "live") return { i, name: a.stations[i].name }; await new Promise((r) => setTimeout(r, 200)); } }
      return null; })()`);
    console.log("Sender:", sender);
    await pruefe("F25", "ein Audio-Element (Schnittansicht greift darauf zu)", `document.querySelectorAll("audio").length === 1`);
    await pruefe("F26", "Lautstärke am Element", `Math.abs(${R}.audio().volume - ${R}.a.volume / 100) < 0.001`);
    await pruefe("F01", "Matrix zeigt den Sender", `${K(".rh-display-quelle ak-segmente")}.getAttribute("text") === ${R}.a.currentStation.name`);
    await pruefe("F02", "Quelle im Originalstrom DIREKT", `${K(".rh-zeit-quelle")}.getAttribute("text") === "DIREKT"`);
    await pruefe("F03", "Pegel laufen beim Spielen (ohne festen Wert)", `[...document.querySelectorAll(".rh-kanzel ak-pegel")].every((p) => !p.hasAttribute("wert")) && ${R}.a.volume > 0`);
    await pruefe("F27", "Spielen-Taste leuchtet, Symbol Stopp im Originalstrom", `${taste(2)}.hasAttribute("an") && !!${taste(2)}.querySelector("i.fa-stop")`);
    await pruefe("F11", "Zurück nennt den Nachbarn im Hinweis", `(() => { const a = ${R}.a, i = a.stations.findIndex((s) => s.uuid === a.currentStation.uuid), n = a.stations.length;
      return ${taste(0)}.title.startsWith(a.stations[(i - 1 + n) % n].name); })()`);
    await pruefe("F17", "Weiter nennt den Nachbarn im Hinweis", `(() => { const a = ${R}.a, i = a.stations.findIndex((s) => s.uuid === a.currentStation.uuid), n = a.stations.length;
      return ${taste(4)}.title.startsWith(a.stations[(i + 1) % n].name); })()`);
    { const icy = await werte(`!!${R}.a.currentStation.icy`); const n = anfragen.filter((u) => u.includes("/now-playing")).length;
      erg.push({ id: "F23", was: "Titelabfrage des Senders (now-playing)", ok: !icy || n > 0, info: `icy ${icy}, Abfragen ${n}` }); console.log(!icy || n > 0 ? "OK  " : "FEHL", "F23", icy, n); }
    await pruefe("F21a", "Drehwahl der Bitrate im Originalstrom sichtbar, gesperrt; im Glas keine Bedienung",
      `${K(".rh-bitrate-wahl")}.getAttribute("aria-disabled") === "true" && !document.querySelector(".rh-display button:not(.rh-display-quelle), .rh-display .knopf, .rh-display .auswahl")`);
    // Zeitversatz: auf HLS warten, Modus-Taste
    await werte(`(async () => { const e = Date.now() + 25000; while (Date.now() < e && ${R}.a.canPlayHLS !== true) await new Promise((r) => setTimeout(r, 300)); })()`);
    await pruefe("F19", "Taste Original oder Zeitversatz wechselt in den Zeitversatz", `(async () => { ${druecke(5)}; const e = Date.now() + 25000;
      while (Date.now() < e && ${R}.a.playerMode !== "hls") await new Promise((r) => setTimeout(r, 300)); return ${R}.a.playerMode === "hls"; })()`);
    await werte(`new Promise((r) => setTimeout(r, 4000))`);
    await pruefe("F02b", "Quelle im Zeitversatz LIVE, Zeile Zeitversatz da", `${K(".rh-zeit-quelle")}.getAttribute("text") === "LIVE" && !!${K(".rh-puffer-zeile")}`);
    await pruefe("F12", "30 s zurück: hinter live", `(async () => { ${K(".rh-puffer-zeile .knopf")}.click(); await new Promise((r) => setTimeout(r, 1500));
      return { ok: ${R}.a.isLive === false && document.querySelector(".rh-kanzel").dataset.zustand === "versatz", zeit: ${K(".rh-zeit-uhr")}.getAttribute("text") }; })()`);
    await pruefe("F06", "Zeit zeigt den Abstand zu live", `${K(".rh-zeit-uhr")}.getAttribute("text").startsWith("-")`);
    await pruefe("F16", "30 s vor im Zeitversatz", `(async () => { const vor = ${R}.a.currentSegment; ${K(".rh-puffer-rechts .knopf")}.click(); await new Promise((r) => setTimeout(r, 1200));
      return { ok: ${R}.a.currentSegment > vor || ${R}.a.isLive, vor, nach: ${R}.a.currentSegment }; })()`);
    await pruefe("F10", "Spulbahn im Zeitversatz springt", `(async () => { const r = ${K(".rh-spulregler")}; r.dispatchEvent(new PointerEvent("pointerdown"));
      r.value = "20"; r.dispatchEvent(new Event("input", { bubbles: true })); r.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((x) => setTimeout(x, 1500)); return { ok: ${R}.a.isLive === false, lage: r.value }; })()`);
    await pruefe("F18", "Live springt zur Live-Kante", `(async () => { document.querySelectorAll(".rh-puffer-rechts .knopf")[1].click(); await new Promise((r) => setTimeout(r, 1200)); return ${R}.a.isLive === true; })()`);
    await pruefe("F21", "Drehwahl der Bitrate: wählbar im Zeitversatz, gemerkt, Wert darunter und im Glas; zurück auf wie gesendet", `(async () => {
      const d = ${K(".rh-bitrate-wahl")};
      const frei = async () => { const e = Date.now() + 25000; while (Date.now() < e && !(${R}.a.hlsActive && d.getAttribute("aria-disabled") === "false")) await new Promise((r) => setTimeout(r, 300)); };
      await frei(); const taste = (k) => d.dispatchEvent(new KeyboardEvent("keydown", { key: k, bubbles: true }));
      for (let i = 0; i < 5; i++) taste("ArrowUp");
      await new Promise((r) => setTimeout(r, 1500)); const gemerkt = localStorage.getItem("radiohub_bitrate_override");
      await frei(); const wert = d.querySelector(".ak-dreh-wert").textContent, glas = ${K(".rh-display-hinweis")}?.textContent;
      taste("Home"); await new Promise((r) => setTimeout(r, 1500)); const zurueck = localStorage.getItem("radiohub_bitrate_override"); await frei();
      return { ok: gemerkt === "128" && wert === "128" && /128/.test(glas) && zurueck === null && ${R}.a.hlsActive, gemerkt, wert, glas, zurueck }; })()`);
    await pruefe("F14", "Anhalten und Fortsetzen im Zeitversatz", `(async () => { ${druecke(2)}; await new Promise((r) => setTimeout(r, 500)); const pause = ${R}.a.isPaused;
      ${druecke(2)}; await new Promise((r) => setTimeout(r, 800)); return { ok: pause && !${R}.a.isPaused && ${R}.a.isPlaying }; })()`);
    await pruefe("F09", "Klick auf die Matrix springt zum Sender", `(async () => { history.pushState(null, "", "/podcasts"); ${K(".rh-display-quelle")}.click(); await new Promise((r) => setTimeout(r, 300));
      return location.pathname === "/radio/" + ${R}.a.currentStation.uuid; })()`);
    // Aufnahme
    await pruefe("F15", "Aufnahme startet, Taste leuchtet rot und blinkt, Wechsel gesperrt", `(async () => { ${druecke(3)}; const e = Date.now() + 15000;
      while (Date.now() < e && !${R}.a.isRecording) await new Promise((r) => setTimeout(r, 300)); await new Promise((r) => setTimeout(r, 2500));
      const t = ${taste(3)}; return { ok: ${R}.a.isRecording && t.hasAttribute("an") && t.querySelector("ak-led[art=schlitz]").getAttribute("zustand") === "blinkt"
        && ${taste(0)}.querySelector("button").disabled && ${taste(4)}.querySelector("button").disabled && ${taste(2)}.querySelector("button").disabled
        && document.querySelector(".rh-kanzel").dataset.zustand === "aufnahme", zeit: ${K(".rh-zeit-uhr")}.getAttribute("text") }; })()`);
    await pruefe("F07", "Statuszeile während der Aufnahme: Dauer, Bitrate", `(() => { const z = ${K(".rh-display-zeile")}.textContent; return { ok: /AUFNAHME [0-9]{2}:[0-9]{2}:[0-9]{2}/.test(z), z }; })()`);
    await pruefe("F09b", "Matrix-Hinweis während der Aufnahme: zum Sender", `${K(".rh-display-quelle")}.title === "Zum aufnehmenden Sender springen"`);
    // Wiederherstellen nach Neuladen
    await seite.rufe("Page.reload");
    await bis(`!!document.querySelector(".rh-kanzel ak-taster .ak-taster-knopf")`, 30000);
    await werte(HILFEN);
    await pruefe("F24", "laufende Aufnahme nach Neuladen wiederhergestellt", `(async () => { const e = Date.now() + 10000; while (Date.now() < e && !${R}.a.isRecording) await new Promise((r) => setTimeout(r, 300)); return ${R}.a.isRecording; })()`);
    await pruefe("F13", "Stopp beendet Aufnahme und Hören", `(async () => { ${druecke(1)}; const e = Date.now() + 15000;
      while (Date.now() < e && (${R}.a.isRecording || ${R}.a.isPlaying)) await new Promise((r) => setTimeout(r, 300)); return !${R}.a.isRecording && !${R}.a.isPlaying; })()`);
    // Senderwechsel
    await werte(`(async () => { await ${R}.engine.playStation(${R}.a.stations[${sender?.i ?? 0}]); await new Promise((r) => setTimeout(r, 1500)); })()`);
    await pruefe("F11b", "Zurück wechselt den Sender", `(async () => { const e = Date.now() + 10000; while (Date.now() < e && ${taste(0)}.querySelector("button").disabled) await new Promise((r) => setTimeout(r, 200));
      const vor = ${R}.a.currentStation.uuid; ${taste(0)}.querySelector("button").dispatchEvent(new PointerEvent("pointerdown"));
      ${druecke(0)}; await new Promise((r) => setTimeout(r, 1500)); return ${R}.a.currentStation.uuid !== vor; })()`);
    await pruefe("F17b", "Weiter wechselt den Sender", `(async () => { const vor = ${R}.a.currentStation.uuid; ${druecke(4)}; await new Promise((r) => setTimeout(r, 1500)); return ${R}.a.currentStation.uuid !== vor; })()`);
    await pruefe("F14b", "Spielen-Taste im Originalstrom beendet", `(async () => { await new Promise((r) => setTimeout(r, 1500)); ${druecke(2)}; await new Promise((r) => setTimeout(r, 800)); return !${R}.a.isPlaying; })()`);
    // Tastatur (App.svelte) und Lautstärke
    await pruefe("F05", "Pfeil hoch hebt die Lautstärke, der Regler folgt", `(async () => { const vor = ${R}.a.volume; document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowUp", bubbles: true }));
      await new Promise((r) => setTimeout(r, 200)); const d = document.querySelector(".rh-kanzel ak-dreh"); return { ok: ${R}.a.volume === Math.min(100, vor + 5) && d.wert === ${R}.a.volume, vor, nach: ${R}.a.volume, dreh: d.wert }; })()`);
    await pruefe("F04", "Drehregler stellt die Lautstärke (Pfeiltaste am Regler)", `(async () => { const d = document.querySelector(".rh-kanzel ak-dreh"); const vor = ${R}.a.volume; d.focus();
      d.dispatchEvent(new KeyboardEvent("keydown", { key: "ArrowDown", bubbles: false })); await new Promise((r) => setTimeout(r, 200));
      return { ok: ${R}.a.volume < vor && localStorage.getItem("radiohub_volume") === String(${R}.a.volume), vor, nach: ${R}.a.volume }; })()`);
    await werte(`(${R}.engine.setVolume(1), 1)`);
    await pruefe("F28", "Leertaste spielt und hält an, S beendet (Tastatur der App)", `(async () => { await ${R}.engine.playPodcast(${R}.folgen0 ?? (await ${R}.api.getEpisodes(21, 3)).episodes[0], { id: 21, title: "P" });
      await new Promise((r) => setTimeout(r, 3000)); document.activeElement?.blur(); document.body.dispatchEvent(new KeyboardEvent("keydown", { key: " ", bubbles: true }));
      await new Promise((r) => setTimeout(r, 300)); const pause = ${R}.a.isPaused; document.body.dispatchEvent(new KeyboardEvent("keydown", { key: "s", bubbles: true }));
      await new Promise((r) => setTimeout(r, 800)); return { ok: pause && !${R}.a.isPlaying, pause }; })()`);
    // Podcast: Position, Spulen, Reihenfolge
    await werte(`${R}.zustand("podcast")`);
    await pruefe("F08", "Positionszeile: Zeit von Dauer", `(() => { const z = ${K(".rh-puffer > span")}.textContent; return { ok: /[0-9]+:[0-9]{2} von [0-9]+:[0-9]{2}/.test(z), z }; })()`);
    await pruefe("F16b", "10 s vor in der Folge", `(async () => { const vor = ${R}.audio().currentTime; document.querySelectorAll(".rh-puffer-zeile .knopf")[1].click(); await new Promise((r) => setTimeout(r, 600));
      return { ok: ${R}.audio().currentTime - vor > 8, vor, nach: ${R}.audio().currentTime }; })()`);
    await pruefe("F12b", "10 s zurück in der Folge", `(async () => { const vor = ${R}.audio().currentTime; document.querySelectorAll(".rh-puffer-zeile .knopf")[0].click(); await new Promise((r) => setTimeout(r, 600));
      return { ok: vor - ${R}.audio().currentTime > 8, vor, nach: ${R}.audio().currentTime }; })()`);
    await pruefe("F10b", "Spulbahn springt in der Folge", `(async () => { const r = ${K(".rh-spulregler")}; r.dispatchEvent(new PointerEvent("pointerdown"));
      r.value = "70"; r.dispatchEvent(new Event("input", { bubbles: true })); r.dispatchEvent(new Event("change", { bubbles: true }));
      await new Promise((x) => setTimeout(x, 1500)); const a = ${R}.audio(); return { ok: Math.abs(a.currentTime / a.duration * 100 - 70) < 3, lage: a.currentTime / a.duration * 100 }; })()`);
    await pruefe("F20", "Reihenfolge schaltet weiter, Weiter gespiegelt bei rückwärts", `(async () => { ${R}.a.playMode = "linear"; await new Promise((r) => setTimeout(r, 100)); ${druecke(6)};
      await new Promise((r) => setTimeout(r, 200)); return { ok: ${R}.a.playMode === "reverse" && !!${taste(4)}.querySelector("i.rh-gespiegelt"), modus: ${R}.a.playMode }; })()`);
    await werte(`${R}.a.playMode = "linear"`);
    await pruefe("F09c", "Klick auf die Matrix springt zum Podcast", `(async () => { ${R}.a.podcastPlaylistPodcast = { id: 21 }; ${K(".rh-display-quelle")}.click(); await new Promise((r) => setTimeout(r, 300)); return location.pathname === "/podcasts/21"; })()`);
    // Fehler
    await werte(`${R}.zustand("fehler")`);
    await pruefe("F29", "Fehler: Spielen-Taste wird Neu verbinden (außerhalb des Glases) und lädt neu", `(async () => { const ok1 = document.querySelector(".rh-kanzel").dataset.zustand === "fehler";
      const symbol = !!${taste(2)}.querySelector("i.fa-rotate-right"); ${druecke(2)}; await new Promise((r) => setTimeout(r, 150));
      const z = document.querySelector(".rh-kanzel").dataset.zustand;
      return { ok: ok1 && symbol && (z === "laedt" || z === "fehler") && ${R}.a.isPlaying, z }; })()`);
    await werte(`${R}.engine.stop()`);
    await pruefe("F03b", "Pegel stehen ohne Ton unten", `[...document.querySelectorAll(".rh-kanzel ak-pegel")].every((p) => p.getAttribute("wert") === "-60")`);
    fs.writeFileSync(path.join(AUS, "ablauf.json"), JSON.stringify(erg, null, 1));
    console.log(`${erg.filter((e) => e.ok).length} von ${erg.length} bestanden`);
  }
  console.log("Konsolenfehler:", fehler.length ? fehler.slice(0, 20) : "keine");
} finally {
  await seite.schliesse();
}
