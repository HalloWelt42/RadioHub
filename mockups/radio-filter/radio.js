// Gemeinsame Bausteine des Entwurfs RAD-3 (Rechner und Telefon): Zahlen, Logo, Qualitätsleiste, Sterne,
// Aufklapplisten und Darstellungstafel. Eine Stelle je Form, die Seiten setzen sie nur ein.

(() => {
  "use strict";
  const D = window.RHDaten;
  const zahl = (n) => n.toLocaleString("de-DE");
  const esc = (t) => String(t).replace(/[&<>"]/g, (z) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[z]);

  // Logo: Kürzel aus dem Namen, Lackfarbe aus einer festen Reihe (gleicher Name, gleiche Farbe)
  const LACKE = 10;   // Lackfarben --rh-lack-1 bis --rh-lack-10 stehen in radio-marken.css
  function kuerzel(name) {
    const teile = name.replace(/[.\-]/g, " ").split(/\s+/).filter(Boolean);
    if (/^\d/.test(teile[0])) return teile[0].slice(0, 3);
    const zahlTeil = teile.find((t) => /^\d+$/.test(t));
    if (zahlTeil) return (teile[0][0] + zahlTeil).toUpperCase().slice(0, 3);
    return teile.slice(0, 2).map((t) => t[0]).join("").toUpperCase();
  }
  function lack(name) { let h = 0; for (const z of name) h = (h * 31 + z.charCodeAt(0)) >>> 0; return `var(--rh-lack-${(h % LACKE) + 1})`; }
  const logo = (s, klasse = "") => `<span class="rh-logo-bild ${klasse}" style="--lack:${lack(s.name)}" aria-hidden="true">${esc(kuerzel(s.name))}</span>`;

  function guete(stufe) {
    const g = D.GUETE[stufe];
    return `<span class="rh-guete" data-guete="${stufe}" style="--farbe:var(--led-${g.farbe})" title="${esc(g.hilfe)}" role="img" aria-label="Qualität ${esc(g.name)}">${[0, 1, 2, 3].map((i) => `<i class="${i < g.lichter ? "an" : ""}"></i>`).join("")}</span>`;
  }
  const bitrate = (s) => (s.kbps ? `${s.codec} ${zahl(s.kbps)} kbit/s` : `${s.codec}, noch nicht gemessen`);
  const sterne = (n) => `<span class="rh-sterne" aria-label="${n} von 3 Sternen">${[1, 2, 3].map((i) => `<i class="fa-solid fa-star ${i <= n ? "" : "aus"}"></i>`).join("")}</span>`;

  // Aufklappliste des Appkerns (.auswahl): öffnet, wählt, schließt bei Klick daneben und mit Escape
  function auswahl(wurzel, beiWahl) {
    const knopf = wurzel.querySelector(".auswahl-knopf"), liste = wurzel.querySelector(".auswahl-liste");
    const zu = () => { liste.hidden = true; knopf.setAttribute("aria-expanded", "false"); };
    zu();
    knopf.addEventListener("click", (e) => { e.stopPropagation(); const auf = liste.hidden; schliesseAlle(); if (auf) { liste.hidden = false; knopf.setAttribute("aria-expanded", "true"); } });
    liste.addEventListener("click", (e) => {
      const b = e.target.closest("button"); if (!b) return;
      liste.querySelectorAll("button").forEach((x) => x.classList.toggle("aktiv", x === b));
      if (b.dataset.titel) knopf.querySelector(".auswahl-text").textContent = b.dataset.titel;
      zu(); beiWahl?.(b.dataset.wert, b);
    });
    offene.add(zu);
  }
  const offene = new Set();
  function schliesseAlle() { offene.forEach((f) => f()); }
  document.addEventListener("click", schliesseAlle);
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") schliesseAlle(); });

  // Darstellungstafel im Kopf: Thema und Schrift (darstellung.js bindet die Knöpfe)
  function darstellungTafel(knopf) {
    const tafel = document.getElementById(knopf.getAttribute("aria-controls"));
    const zu = () => { tafel.hidden = true; knopf.setAttribute("aria-expanded", "false"); };
    knopf.addEventListener("click", (e) => { e.stopPropagation(); const auf = tafel.hidden; schliesseAlle(); if (auf) { tafel.hidden = false; knopf.setAttribute("aria-expanded", "true"); } });
    tafel.addEventListener("click", (e) => e.stopPropagation());
    offene.add(zu);
  }

  // Tastenlicht: die Leuchte einer Taste sitzt als Lichtschlitz in ihrer oberen Kante (ein Baustein für alle Tasten mit
  // Leuchte). Der Taster des Appkerns stellt sie über die Taste; hier wandert sie hinein, die Taste bleibt so hoch wie ohne.
  function tastenlicht(wurzel = document) {
    wurzel.querySelectorAll("ak-taster[led]").forEach((t) => {
      const licht = t.querySelector(":scope > ak-led"), knopf = t.querySelector(".ak-taster-knopf");
      if (licht && knopf) { licht.classList.add("rh-tastenlicht"); knopf.append(licht); }
    });
  }

  window.RH = { zahl, esc, kuerzel, lack, logo, guete, bitrate, sterne, auswahl, schliesseAlle, darstellungTafel, tastenlicht };
  customElements.whenDefined("ak-taster").then(() => tastenlicht());
  document.addEventListener("DOMContentLoaded", () => document.querySelectorAll("[data-darstellung-knopf]").forEach(darstellungTafel));
})();
