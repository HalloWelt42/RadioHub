// Breitenprüfung für den Entwurf RAD-3: jede Seite in 375, 768, 1280, 1920, hell und dunkel, Schrift Normal und
// Sehr groß. Misst seitliches Rollen, Überlauf in Rollfeldern, abgeschnittene Bedienelemente, umbrechende Knöpfe,
// Konsolenfehler und fehlende Dateien. Aufruf: node pruefen.mjs [--gegentest] [--bilder]
import fs from "node:fs";
import { oeffneSeite } from "/Users/alpha/Entwicklung/Werkzeuge/Appkern/oberflaeche/werkzeuge/browser.mjs";

const BASIS = "http://localhost:9150/mockups/radio-filter/";
const SEITEN = process.env.SEITEN ? process.env.SEITEN.split(" ") : ["index.html", "rechner.html", "regeln.html?reiter=regeln&sprache=chin", "regeln.html?reiter=ausgeblendet", "regeln.html?reiter=laender", "telefon.html"];
const BREITEN = [[375, 812], [768, 1024], [1280, 800], [1920, 1080]];
const THEMEN = ["hell", "dunkel"];
const SCHRIFTEN = ["mittel", "sehr-gross"];
const VORLAGEN = (process.env.VORLAGEN || "hifi,ruhig").split(",");
const gegentest = process.argv.includes("--gegentest");
const nurBilder = process.argv.includes("--bilder");
const BILDER = new URL("../bilder/", import.meta.url).pathname;

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
const fehler = [];
seite.beiEreignis((m) => {
  if (m.method === "Runtime.exceptionThrown") fehler.push("Ausnahme: " + (m.params.exceptionDetails.exception?.description || m.params.exceptionDetails.text));
  if (m.method === "Runtime.consoleAPICalled" && ["error", "warning"].includes(m.params.type)) fehler.push("Konsole: " + m.params.args.map((a) => a.value ?? a.description).join(" "));
  if (m.method === "Log.entryAdded" && m.params.entry.level === "error") fehler.push("Log: " + m.params.entry.text + " " + (m.params.entry.url || ""));
  if (m.method === "Network.responseReceived" && m.params.response.status >= 400) fehler.push("Netz " + m.params.response.status + ": " + m.params.response.url);
});
for (const d of ["Runtime.enable", "Log.enable", "Network.enable", "Page.enable"]) await seite.rufe(d);
const warte = (ms) => new Promise((r) => setTimeout(r, ms));
async function laden(url, [b, h]) {
  await seite.rufe("Emulation.setDeviceMetricsOverride", { width: b, height: h, deviceScaleFactor: b <= 768 ? 2 : 1, mobile: b < 768 });
  await seite.rufe("Page.navigate", { url });
  await warte(1400);
}
async function bild(datei, clip) {
  const r = await seite.rufe("Page.captureScreenshot", { format: "png", ...(clip ? { clip: { ...clip, scale: 1 } } : {}) });
  fs.writeFileSync(BILDER + datei, Buffer.from(r.result.data, "base64"));
  console.log("Bild", BILDER + datei);
}
const werte = async (ausdruck) => (await seite.rufe("Runtime.evaluate", { expression: ausdruck, returnByValue: true, awaitPromise: true })).result.result.value;

if (gegentest) {
  await laden(BASIS + "rechner.html?thema=dunkel", [1280, 800]);
  await werte(`document.querySelector('.rh-werkzeug-zeile').insertAdjacentHTML('beforeend', '<button class="knopf" style="min-width:1600px">Ueberlang</button>'); document.querySelector('#zeilen').insertAdjacentHTML('afterbegin','<div style="width:3000px;height:4px"></div>'); 1`);
  console.log("Gegentest:", JSON.stringify(await werte(MESSEN), null, 1));
  await seite.schliesse(); process.exit(0);
}

if (nurBilder) {
  const zustand = (n) => `(() => { for (let i = 0; i < ${n}; i++) document.querySelector('#entwurf-vor').click(); return 1; })()`;
  await laden(BASIS + "rechner.html?thema=dunkel", [1920, 1080]); await bild("rechner-1920-dunkel.png");
  const k = await werte("(() => { const r = document.querySelector('#kanzel').getBoundingClientRect(); return { x: 0, y: Math.max(0, r.top - 60), width: innerWidth, height: r.height + 60 }; })()");
  await bild("kanzel-1920-dunkel-tasten.png", k);
  await laden(BASIS + "rechner.html?thema=hell", [1280, 800]); await werte(zustand(2)); await warte(600); await bild("rechner-1280-hell-aufnahme.png");
  await laden(BASIS + "rechner.html?thema=dunkel&schrift=sehr-gross", [375, 812]); await bild("rechner-375-dunkel-sehr-gross.png");
  await laden(BASIS + "regeln.html?reiter=regeln&sprache=chin&thema=dunkel", [1280, 900]); await werte("document.querySelector('#neu').scrollIntoView(); 1"); await warte(400); await bild("regeln-1280-dunkel-vorschau.png");
  await laden(BASIS + "regeln.html?reiter=ausgeblendet&thema=hell", [768, 1024]); await bild("regeln-768-hell-ausgeblendet.png");
  await laden(BASIS + "telefon.html?thema=dunkel", [1700, 1040]); await werte("document.querySelector('.rh-buehne').scrollIntoView(); 1"); await warte(400); await bild("telefon-vier-rahmen-dunkel.png");
  await laden(BASIS + "telefon.html?thema=hell", [1700, 1040]); await werte("document.querySelector('.rh-buehne').scrollIntoView(); 1"); await warte(400); await bild("telefon-vier-rahmen-hell.png");
  await laden(BASIS + "index.html?thema=dunkel", [1280, 900]); await bild("uebersicht-1280-dunkel.png");
  await laden(BASIS + "rechner.html?thema=dunkel&vorlage=hifi&zustand=web", [1440, 900]); await bild("rechner-1440-dunkel-webversion.png");
  await laden(BASIS + "rechner.html?thema=hell&vorlage=ruhig", [1440, 900]); await bild("rechner-1440-hell-vorlage-ruhig.png");
  await laden(BASIS + "telefon.html?thema=dunkel&vorlage=ruhig", [1700, 1040]); await werte("document.querySelector('.rh-buehne').scrollIntoView(); 1"); await warte(400); await bild("telefon-vier-rahmen-dunkel-ruhig.png");
  await seite.schliesse(); process.exit(0);
}

if (process.argv.includes("--zustaende")) {
  const AKTIONEN = {
    "rechner.html": [
      ["Filtertafel", "document.querySelector('#filter-auf').click()"],
      ["Kanzel offen", "document.querySelector('#kanzel-auf').click()"],
      ["Darstellung", "document.querySelector('[data-darstellung-knopf]').click()"],
      ["Geräteliste", "document.querySelector('#haus-wahl .auswahl-knopf').click()"],
      ["Details und Varianten", "document.querySelectorAll('[data-aktion=details]')[2].click(); document.querySelectorAll('[data-aktion=varianten]')[0]?.click()"],
      ...[1, 2, 3, 4, 5, 6, 7, 8].map((n) => ["Zustand " + n, "document.querySelector('#entwurf-vor').click()"]),
      ["Webversion mit Kanzel offen", "document.querySelector('#entwurf-zurueck').click(); document.querySelector('#kanzel-auf').click()"],
      ["Ausblenden mit Band", "document.querySelector('.auge-zelle [data-aktion=ausblenden]').click()"],
    ],
    "regeln.html?reiter=regeln": [
      ["Rückfrage Entfernen", "document.querySelector('.rh-regel [data-aktion=fragen]').click()"],
      ...["tag", "stimmen", "werbung", "bewertung", "einzeln", "sprache"].map((a) => ["Art " + a, `document.querySelector('[data-art=${a}]').click()`]),
      ["Anlegen", "const i=document.querySelector('#neu-suche'); i.value='deutsch'; i.dispatchEvent(new Event('input')); document.querySelector('#v-anlegen').click()"],
    ],
    "telefon.html": [["Holen", "document.querySelector('[data-telefon=fern] [data-t=holen]').click()"], ["Darstellung", "document.querySelector('[data-telefon=liste] [data-t=darstellung]').click()"]],
  };
  for (const v of VORLAGEN) for (const [s, liste] of Object.entries(AKTIONEN)) for (const groesse of BREITEN) for (const sch of SCHRIFTEN) {
    fehler.length = 0;
    await laden(`${BASIS}${s}${s.includes("?") ? "&" : "?"}thema=${v === "ruhig" ? "hell" : "dunkel"}&schrift=${sch}&vorlage=${v}`, groesse);
    for (const [name, js] of liste) {
      await werte(js + "; 1"); await warte(350);
      const befunde = [...(await werte(MESSEN)), ...fehler]; fehler.length = 0;
      console.log((befunde.length ? "FEHLER " : "ok     ") + `${v} ${s.split("?")[0]} ${groesse[0]} ${sch} nach ${name}` + (befunde.length ? "\n   " + [...new Set(befunde)].slice(0, 8).join("\n   ") : ""));
    }
  }
  await seite.schliesse(); process.exit(0);
}

const ergebnis = {};
for (const v of VORLAGEN) for (const s of SEITEN) for (const groesse of BREITEN) for (const t of THEMEN) for (const sch of SCHRIFTEN) {
  fehler.length = 0;
  const url = `${BASIS}${s}${s.includes("?") ? "&" : "?"}thema=${t}&schrift=${sch}&vorlage=${v}`;
  await laden(url, groesse);
  const befunde = [...(await werte(MESSEN)), ...fehler];
  const k = `${v} ${s.split("?")[0]}${s.includes("reiter=") ? "#" + s.match(/reiter=(\w+)/)[1] : ""} ${groesse[0]} ${t} ${sch}`;
  ergebnis[k] = befunde;
  console.log((befunde.length ? "FEHLER " : "ok     ") + k + (befunde.length ? "\n   " + [...new Set(befunde)].slice(0, 12).join("\n   ") : ""));
}
fs.writeFileSync(new URL("./ergebnis.json", import.meta.url), JSON.stringify(ergebnis, null, 1));
await seite.schliesse();
