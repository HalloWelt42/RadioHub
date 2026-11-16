// Darstellung im Entwurf RAD-3: Vorlage (HiFi, Ruhig), Thema (Hell, Dunkel, System) und Schriftstufe, gemerkt je Browser und gültig für alle
// Seiten des Entwurfs. Läuft im Kopf jeder Seite vor dem ersten Bild, damit nichts aufblitzt. Bedienelemente melden sich
// über Merkmale an: data-vorlage-wahl="hifi|ruhig", data-thema-wahl="hell|dunkel|system", data-schrift-schritt="-1|1", data-schrift-anzeige.
// In der App wird daraus die Darstellung des Appkerns (lib/anzeige.svelte.ts) mit Schriftstufen.

(() => {
  "use strict";
  const SCHLUESSEL = { thema: "radiohub-entwurf-thema", schrift: "radiohub-entwurf-schrift", vorlage: "radiohub-entwurf-vorlage" };
  // Stufen ab mittel: Grundschrift 17, klein 15 Pixel; sehr-gross ist ein Vorschlag für den Appkern (radio-marken.css)
  const STUFEN = [["mittel", "Normal"], ["gross", "Groß"], ["sehr-gross", "Sehr groß"]];
  const THEMEN = [["hell", "Hell", "fa-sun"], ["dunkel", "Dunkel", "fa-moon"], ["system", "System", "fa-circle-half-stroke"]];
  // Vorlagen: je eine Marken-Datei unter vorlagen/<name>/ (siehe radio-marken.css); HiFi ist die Vorgabe
  const VORLAGEN = [["hifi", "HiFi"], ["ruhig", "Ruhig"]];
  const adresse = new URLSearchParams(location.search);
  const lesen = (k) => { try { return localStorage.getItem(k); } catch { return null; } };
  const merken = (k, v) => { try { localStorage.setItem(k, v); } catch { /* gilt dann bis zum Neuladen */ } };
  const systemDunkel = matchMedia("(prefers-color-scheme: dark)");

  const stand = {
    thema: adresse.get("thema") || lesen(SCHLUESSEL.thema) || "system",
    schrift: adresse.get("schrift") || lesen(SCHLUESSEL.schrift) || "mittel",
    vorlage: adresse.get("vorlage") || lesen(SCHLUESSEL.vorlage) || "hifi",
  };
  if (!THEMEN.some(([t]) => t === stand.thema)) stand.thema = "system";
  if (!STUFEN.some(([s]) => s === stand.schrift)) stand.schrift = "mittel";
  if (!VORLAGEN.some(([v]) => v === stand.vorlage)) stand.vorlage = "hifi";

  const wurzel = document.documentElement;
  function anwenden() {
    wurzel.dataset.theme = stand.thema === "dunkel" || (stand.thema === "system" && systemDunkel.matches) ? "dunkel" : "hell";
    wurzel.dataset.schrift = stand.schrift;
    wurzel.dataset.vorlage = stand.vorlage;
    document.querySelectorAll("[data-vorlage-wahl]").forEach((k) => { const an = k.dataset.vorlageWahl === stand.vorlage; k.classList.toggle("aktiv", an); k.setAttribute("aria-pressed", String(an)); });
    document.querySelectorAll("[data-thema-wahl]").forEach((k) => {
      const an = k.dataset.themaWahl === stand.thema;
      k.classList.toggle("aktiv", an);
      k.setAttribute("aria-pressed", String(an));
    });
    const i = STUFEN.findIndex(([s]) => s === stand.schrift);
    document.querySelectorAll("[data-schrift-anzeige]").forEach((el) => { el.textContent = STUFEN[i][1]; });
    document.querySelectorAll("[data-schrift-schritt]").forEach((k) => {
      const ziel = i + Number(k.dataset.schriftSchritt);
      k.disabled = ziel < 0 || ziel >= STUFEN.length;
    });
  }
  function setzen(art, wert) {
    stand[art] = wert;
    merken(SCHLUESSEL[art], wert);
    anwenden();
    document.dispatchEvent(new CustomEvent("rh-darstellung", { detail: { ...stand } }));
  }
  function binden(wurzelEl = document) {
    wurzelEl.querySelectorAll("[data-thema-wahl]").forEach((k) => k.addEventListener("click", () => setzen("thema", k.dataset.themaWahl)));
    wurzelEl.querySelectorAll("[data-vorlage-wahl]").forEach((k) => k.addEventListener("click", () => setzen("vorlage", k.dataset.vorlageWahl)));
    wurzelEl.querySelectorAll("[data-schrift-schritt]").forEach((k) => k.addEventListener("click", () => {
      const i = STUFEN.findIndex(([s]) => s === stand.schrift) + Number(k.dataset.schriftSchritt);
      if (i >= 0 && i < STUFEN.length) setzen("schrift", STUFEN[i][0]);
    }));
    anwenden();
  }
  systemDunkel.addEventListener("change", anwenden);
  anwenden();
  document.addEventListener("DOMContentLoaded", () => binden());
  window.RHDarstellung = { STUFEN, THEMEN, VORLAGEN, stand, setzen, binden };
})();
