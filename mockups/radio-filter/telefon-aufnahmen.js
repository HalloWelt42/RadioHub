// Aufnahmen am Telefon im Entwurf RAD-17: nur hören. Rahmen 1 die Liste mit Ordnern als Chips, Rahmen 2 eine geöffnete
// Aufnahme mit ihren Titeln. Dieselben Bausteine wie beim Radio am Telefon (Statuszeile, Kopf, Zeilen, Spielerleiste,
// Reiter unten).
(() => {
  "use strict";
  const A = window.RHAufnahmen, R = window.RH, esc = R.esc;
  const zeit = (s) => { s = Math.round(s); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`; };
  const datum = (d) => d.toLocaleDateString("de-DE", { day: "numeric", month: "short" }) + ", " + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  const ordnerName = (id) => A.ORDNER.find((o) => o.id === id)?.name ?? "Ohne Ordner";
  const rahmen = (inhalt, kopf) => `<div class="t-app t-app-aufnahmen">
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div>
      <div class="t-luft" aria-hidden="true"></div>
      ${kopf}
      <div class="t-liste">${inhalt}</div>
      <div class="t-spieler" role="button" aria-label="Spieler öffnen">
        <div class="ak-glas"><b><ak-led farbe="blau" zustand="an" groesse="klein"></ak-led>Jazzkeller FM</b><span>Blaue Stunde am Hafen · 3:12 von 6:52</span></div>
        <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="Anhalten" an></ak-taster>
        <button class="rund" type="button" aria-label="Spieler öffnen" title="Spieler öffnen"><i class="fa-solid fa-chevron-up"></i></button>
      </div>
      <nav class="t-reiter" aria-label="Bereiche"><span><i class="fa-solid fa-radio"></i>Radio</span><span class="aktiv"><i class="fa-solid fa-circle-dot"></i>Aufnahmen</span><span><i class="fa-solid fa-podcast"></i>Podcasts</span><span><i class="fa-solid fa-ellipsis"></i>Mehr</span></nav>
    </div>`;
  function liste(el) {
    const kopf = `<div class="t-kopf"><span class="rh-logo">RadioHub</span><div class="t-kopf-rechts"><span class="rh-still">Aufnahmen</span></div></div>
      <div class="t-suche"><label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input type="search" placeholder="Sender oder Titel suchen" aria-label="Aufnahmen suchen"></label></div>
      <div class="t-chips"><span class="t-treffer"><ak-segmente art="7" stellen="3" farbe="rot" text="${A.SITZUNGEN.length}"></ak-segmente>Aufnahmen</span>
        ${["Alle", ...A.ORDNER.map((o) => o.name), "Ohne Ordner"].map((n, i) => `<button type="button" class="chip wahl${i === 0 ? " an" : ""}">${esc(n)}</button>`).join("")}</div>`;
    const zeilen = A.SITZUNGEN.map((s, i) => `<div class="t-zeile${i === 0 ? " spielt" : ""}"><span class="rh-logo-bild" style="--lack:${R.lack(s.sender)}">${esc(R.kuerzel(s.sender))}</span>
      <div><b>${esc(s.sender)}</b><div class="t-meta"><span>${datum(s.datum)}</span><span>${esc(ordnerName(s.ordner))}</span>${s.abgebrochen ? `<span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>abgebrochen</span>` : ""}</div>
      <div class="t-titel"><i class="fa-solid fa-list"></i>${s.titel.length} Titel · ${zeit(s.dauer)}</div></div>
      <button class="rund" type="button" aria-label="Hören" title="Hören"><i class="fa-solid fa-play"></i></button></div>`).join("");
    el.innerHTML = rahmen(zeilen, kopf);
  }
  function aufnahme(el) {
    const s = A.SITZUNGEN[0];
    const kopf = `<div class="t-kopf t-kopf-zurueck"><button class="rund" type="button" aria-label="Zurück zur Liste" title="Zurück"><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>${esc(s.sender)}</b><span class="rh-still">${datum(s.datum)} · ${s.titel.length} Titel · ${zeit(s.dauer)}</span></div></div>
      <div class="t-chips"><button class="knopf primaer" type="button"><i class="fa-solid fa-play"></i>Alles hören</button><span class="rh-still">${esc(ordnerName(s.ordner))}</span></div>`;
    const zeilen = s.titel.map((t) => `<div class="t-zeile${t.nr === 2 ? " spielt" : ""}"><span class="rh-a-nr">${String(t.nr).padStart(2, "0")}</span>
      <div><b>${esc(t.titel)}</b><div class="t-meta"><span>ab ${zeit(t.start)}</span><span>${zeit(t.dauer)}</span></div></div>
      <button class="rund" type="button" aria-label="Ab hier hören" title="Ab hier hören"><i class="fa-solid ${t.nr === 2 ? "fa-volume-high" : "fa-play"}"></i></button></div>`).join("");
    el.innerHTML = rahmen(zeilen, kopf);
  }
  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-telefon]").forEach((el) => {
      (el.dataset.telefon === "liste" ? liste : aufnahme)(el);
      R.tastenlicht(el);
      el.addEventListener("click", (e) => { const c = e.target.closest(".chip.wahl"); if (!c) return; el.querySelectorAll(".chip.wahl").forEach((x) => x.classList.toggle("an", x === c)); });
    });
  });
})();
