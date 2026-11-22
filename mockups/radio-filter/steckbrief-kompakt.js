// Entwurf RAD-35: aufgeklappter Sender kompakter. "Heute" ist der Aufbau der App (übernommen aus der Probe, 0.16);
// A, B und C ordnen dieselben Angaben neu. Musterdaten: Rock Antenne mit 18 Spots von 7 Werbenden (erfunden), zwei
// Sterne, eine Markierung und eine Kategorie gewählt.
(() => {
  "use strict";
  const $ = (s, w = document) => w.querySelector(s);
  const $$ = (s, w = document) => [...w.querySelectorAll(s)];

  // ─── Daten ───
  const SPOTS = [
    ["autoglas-schnell.de", "Steinschlag Reparatur", 26, 11, "verbinden", "heute 12:38"],
    ["autoglas-schnell.de", "Winterreifen Aktion", 20, 4, "programm", "heute 11:02"],
    ["autoglas-schnell.de", "Kasko Hinweis", 15, 3, "programm", "gestern 18:20"],
    ["autoglas-schnell.de", "Filialen", 10, 2, "programm", "19. Nov."],
    ["moebelhaus-am-see.de", "Herbstaktion Sofas", 15, 9, "verbinden", "heute 10:42"],
    ["moebelhaus-am-see.de", "Küchenwochen", 20, 3, "programm", "gestern 09:15"],
    ["moebelhaus-am-see.de", "Eröffnung Süd", 30, 1, "programm", "18. Nov."],
    ["versicherung-anker.de", "Kfz-Wechsel", 25, 7, "programm", "heute 12:01"],
    ["versicherung-anker.de", "Hausrat", 20, 2, "programm", "gestern 17:40"],
    ["versicherung-anker.de", "Rechtsschutz", 15, 1, "programm", "17. Nov."],
    ["werkzeugladen.de", "Akkuschrauber Woche", 20, 6, "programm", "heute 10:31"],
    ["werkzeugladen.de", "Gartensaison Ende", 15, 2, "programm", "16. Nov."],
    ["reisewelt-blau.de", "Winter Sonne", 30, 3, "verbinden", "heute 09:12"],
    ["reisewelt-blau.de", "Kreuzfahrt", 25, 1, "programm", "gestern 20:05"],
    ["reisewelt-blau.de", "Frühbucher", 20, 1, "programm", "15. Nov."],
    ["stromtarif-sonne.de", "Wechselbonus", 20, 4, "programm", "heute 08:30"],
    ["stromtarif-sonne.de", "Wärmepumpe", 25, 1, "programm", "14. Nov."],
    ["baeckerei-sonnenkorn.de", "Frühstück zum Mitnehmen", 25, 3, "programm", "gestern 07:45"],
  ].map(([werbender, titel, laenge, mal, art, zuletzt]) => ({ werbender, titel, laenge, mal, art, zuletzt }));
  const WERBENDE = Object.values(SPOTS.reduce((g, s) => {
    (g[s.werbender] ??= { name: s.werbender, spots: [], mal: 0 }).spots.push(s);
    g[s.werbender].mal += s.mal;
    return g;
  }, {})).sort((a, b) => b.mal - a.mal);
  const MAL = SPOTS.reduce((n, s) => n + s.mal, 0);
  const MARKEN = ["Werbung", "Religiös", "Politisch extrem", "Populistisch", "Nicht jugendfrei", "Schlechte Qualität",
    "Schwankende Qualität", "Häufig nicht erreichbar", "Hoher Sprachanteil"];
  const KATEGORIEN = ["Klassik", "Rock/Metal", "Elektro/Darkwave", "80er", "Jazz, Soul, Soft", "Dance", "Ausland", "Sonstige"];
  const z = { sterne: 2, marken: new Set(["Hoher Sprachanteil"]), kategorien: new Set(["Rock/Metal"]), keinVerdacht: false };
  const zeit = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  const STROM = "http://mp3channels.webradio.rockantenne.de/rockantenne";

  // ─── Kopf der Zeile: wie in der App (Probe, 0.16), Logo ohne Bild ───
  const kern = `<div class="rh-sender-kern">
    <span aria-hidden="true" class="rh-logo-bild" style="--lack: var(--rh-lack-9);">RA</span>
    <div class="name"><b title="Rock Antenne">Rock Antenne</b><div class="meta"><span class="rh-kennung">DE</span><span>Deutschland</span>
      <span class="rh-titel"><i class="fa-solid fa-volume-high"></i>Golden Earring - Radar love</span>
      <span class="rh-werbemarke-text" title="Kündigt Werbung in den Sendedaten an (bekannte Spots: 18); wird übersprungen"><i class="fa-solid fa-rectangle-ad"></i>Werbung</span></div></div>
    <div class="genres"><span class="rh-genre">Rock</span></div>
    <div class="guete-zelle"><span class="rh-guete" role="img" data-guete="mittel" style="--farbe: var(--led-gelb);"><i class="an"></i><i class="an"></i><i></i><i></i></span><b>mittel</b><span>MP3 128</span></div>
    <div class="stimmen"><span><i class="fa-solid fa-thumbs-up"></i>24.902</span></div>
    <div class="rh-aktionen"><span class="rh-varianten-zelle"><button type="button" class="knopf rh-varianten-knopf"><i class="fa-solid fa-layer-group"></i><span><span class="rh-zahl">8</span> Varianten</span></button></span>
      <button type="button" class="rund" aria-label="Favorit"><i class="fa-regular fa-star"></i></button>
      <span class="auge-zelle"><button type="button" class="rund" aria-label="Ausblenden"><i class="fa-solid fa-minus"></i></button></span>
      <button class="rund" type="button" aria-expanded="true" aria-label="Details"><i class="fa-solid fa-chevron-down"></i></button></div></div>`;
  const eintrag = (detail) => `<article class="rh-sender spielt offen">${kern}${detail}</article>`;
  const schalter = (an, text, hilfe) => `<button class="knopf rh-schalter" type="button" aria-pressed="${an}" title="${hilfe}"><ak-led class="rh-tastenlicht" farbe="gruen" zustand="${an ? "an" : "aus"}"></ak-led>${text}</button>`;
  const info = (text) => `<i class="fa-solid fa-circle-info sk-info" title="${text}" aria-label="${text}"></i>`;

  // ─── 0: heute (Aufbau der App, mit 18 Spots) ───
  function heute() {
    return eintrag(`<div class="rh-detail">
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-circle-info"></i>Steckbrief</h4>
        <dl class="rh-werte"><dt>Läuft</dt><dd>Golden Earring - Radar love</dd>
          <dt>Homepage</dt><dd><a href="#">www.rockantenne.de</a></dd>
          <dt>Stream</dt><dd class="rh-strom"><code>${STROM}</code> <button class="rund" type="button" aria-label="Adresse kopieren"><i class="fa-regular fa-copy"></i></button> <button class="rund" type="button" aria-label="Eigene Adresse setzen"><i class="fa-solid fa-pen"></i></button></dd>
          <dt>Codec</dt><dd>MP3 128 kbit/s, laut Verzeichnis · Qualität mittel</dd><dt>Sprache</dt><dd>Deutsch</dd><dt>Genres</dt><dd>Rock</dd><dt>Ort</dt><dd>Deutschland</dd>
          <dt>Geprüft</dt><dd>Stream war bei der letzten Prüfung erreichbar</dd>
          <dt>Varianten</dt><dd><button class="knopf still" type="button"><i class="fa-solid fa-layer-group"></i>8 Varianten</button></dd>
          <dt>Titelangaben im Stream</dt><dd><span class="rh-titelguete"><button type="button" class="chip wahl">Titelwechsel pünktlich</button> <button type="button" class="chip wahl">Titelwechsel ungenau</button></span></dd>
          <dt>Werbung</dt><dd>Kein Verdacht<span class="rh-werbe-angekuendigt"><span class="rh-werbemarke-text"><i class="fa-solid fa-rectangle-ad"></i>kündigt Werbung an</span>, bekannte Spots: 18, zuletzt heute 12:38</span></dd></dl>
        <div class="rh-detail-knoepfe">${schalter(true, "Werbung überspringen", "")}</div></section>
      <section class="rh-tafel-detail rh-werbespots"><h4><i class="fa-solid fa-rectangle-ad"></i>Bekannte Spots</h4>
        <ol class="rh-werbestellen">${SPOTS.map((s, i) => `<li><span class="rh-a-nr">${String(i + 1).padStart(2, "0")}</span>
          <span class="zeit"><b>${zeit(s.laenge)}</b><span>${s.mal} ×</span></span>
          <span class="herkunft"><span><i class="fa-solid ${s.art === "verbinden" ? "fa-plug" : "fa-tower-broadcast"}"></i>${s.werbender}</span><span class="rh-still">${s.titel} · ${s.art === "verbinden" ? "beim Verbinden" : "im Programm"} · zuletzt ${s.zuletzt}</span></span></li>`).join("")}</ol>
        <span class="rh-still">aus den Sendedaten: Werbender, Kennung und Länge, wie der Sender sie angibt</span></section>
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-star"></i>Meine Einschätzung<span class="rh-still rh-h4-hinweis">nur für mich, wirkt in Filtern und Regeln</span></h4>
        <div class="rh-bewerten">${[1, 2, 3].map((i) => `<button type="button" class="rh-stern${i <= z.sterne ? " an" : ""}"><i class="fa-solid fa-star"></i></button>`).join("")}
          ${MARKEN.map((m) => `<button type="button" class="chip wahl${z.marken.has(m) ? " an" : ""}">${m === "Werbung" ? `<i class="fa-solid fa-rectangle-ad"></i>` : ""}${m}</button>`).join("")}
          <button type="button" class="chip wahl"><i class="fa-solid fa-ban"></i>Kein Werbeverdacht</button></div>
        <h4><i class="fa-solid fa-folder"></i>Eigene Kategorien</h4>
        <div class="rh-bewerten">${KATEGORIEN.map((k) => `<button type="button" class="chip wahl${z.kategorien.has(k) ? " an" : ""}">${k}</button>`).join("")}</div></section></div>`);
  }

  // ─── Bausteine der Vorschläge ───
  // Gewählte Einschätzung als kleine Marken; das Plus öffnet die ganze Auswahl als Tafel
  function einschaetzung(id, { titel = true } = {}) {
    const gewaehlt = [
      ...(z.sterne ? [`<span class="sk-gewaehlt sk-sterne" title="Eigene Bewertung">${"<i class=\"fa-solid fa-star\"></i>".repeat(z.sterne)}</span>`] : []),
      ...[...z.marken].map((m) => `<button type="button" class="chip wahl an sk-klein" data-marke="${m}" title="Abwählen">${m}<i class="fa-solid fa-xmark"></i></button>`),
      ...[...z.kategorien].map((k) => `<button type="button" class="chip wahl an sk-klein sk-kategorie" data-kategorie="${k}" title="Abwählen"><i class="fa-solid fa-folder"></i>${k}<i class="fa-solid fa-xmark"></i></button>`),
    ];
    return `<div class="sk-einschaetzung">${titel ? `<span class="sk-marke-titel">Einschätzung${info("Nur für dich; wirkt in Filtern und Regeln")}</span>` : ""}
      ${gewaehlt.join("") || `<span class="rh-still">keine</span>`}
      <span class="sk-auf"><button type="button" class="rund sk-plus" data-tafel="${id}" aria-expanded="false" title="Einschätzung ändern" aria-label="Einschätzung ändern"><i class="fa-solid fa-plus"></i></button>
        <div class="sk-tafel" data-tafel-fuer="${id}" hidden role="dialog" aria-label="Einschätzung">
          <div class="sk-tafel-zeile"><span class="ak-etikett">Bewertung</span><span class="rh-bewerten">${[1, 2, 3].map((i) => `<button type="button" class="rh-stern${i <= z.sterne ? " an" : ""}" data-stern="${i}"><i class="fa-solid fa-star"></i></button>`).join("")}</span></div>
          <div class="sk-tafel-zeile"><span class="ak-etikett">Markierungen</span><span class="rh-bewerten">${MARKEN.map((m) => `<button type="button" class="chip wahl sk-klein${z.marken.has(m) ? " an" : ""}" data-marke="${m}">${m}</button>`).join("")}
            <button type="button" class="chip wahl sk-klein${z.keinVerdacht ? " an" : ""}" title="Widerspruch zur Werbeerkennung"><i class="fa-solid fa-ban"></i>Kein Werbeverdacht</button></span></div>
          <div class="sk-tafel-zeile"><span class="ak-etikett">Kategorien</span><span class="rh-bewerten">${KATEGORIEN.map((k) => `<button type="button" class="chip wahl sk-klein${z.kategorien.has(k) ? " an" : ""}" data-kategorie="${k}">${k}</button>`).join("")}</span></div>
        </div></span></div>`;
  }

  // Werbende zusammengefasst: Name, wie oft, wie viele Spots; aufklappbar bis zu den Spots
  function werbende(sichtbar = 3, id = "") {
    const zeile = (w, i) => `<details class="sk-werbender"${i >= sichtbar ? ` data-mehr="${id}" hidden` : ""}>
      <summary><i class="fa-solid fa-chevron-right sk-pfeil"></i><b>${w.name}</b><span class="rh-zahl">${w.mal} ×</span><span class="rh-still">${w.spots.length} ${w.spots.length === 1 ? "Spot" : "Spots"}</span>
        ${w.spots.some((s) => s.art === "verbinden") ? `<i class="fa-solid fa-plug sk-verbinden" title="auch beim Verbinden"></i>` : `<span></span>`}<span class="rh-still sk-zuletzt">${w.spots[0].zuletzt}</span></summary>
      <ul>${w.spots.map((s) => `<li><span class="rh-zahl">${zeit(s.laenge)}</span><span>${s.titel}</span><span class="rh-zahl">${s.mal} ×</span><span class="rh-still">${s.art === "verbinden" ? "beim Verbinden" : "im Programm"} · ${s.zuletzt}</span></li>`).join("")}</ul></details>`;
    const rest = WERBENDE.length - sichtbar;
    return `<div class="sk-werbende">${WERBENDE.map(zeile).join("")}
      ${rest > 0 ? `<button type="button" class="knopf still sk-alle" data-alle="${id}"><i class="fa-solid fa-chevron-down"></i>alle ${WERBENDE.length} Werbenden</button>` : ""}</div>`;
  }

  const strom = `<span class="sk-strom"><code title="${STROM}">${STROM}</code><button class="rund sk-mini" type="button" title="Adresse kopieren" aria-label="Adresse kopieren"><i class="fa-regular fa-copy"></i></button><button class="rund sk-mini" type="button" title="Eigene Adresse setzen" aria-label="Eigene Adresse setzen"><i class="fa-solid fa-pen"></i></button></span>`;
  const titelWahl = `<span class="segment sk-segment" role="group" aria-label="Titelangaben"><button type="button" title="Die Titelangaben kommen pünktlich; Aufnahmen werden an den richtigen Stellen geteilt">pünktlich</button><button type="button" title="Die Titelangaben kommen zu früh oder zu spät; Aufnahmen werden ungenau geteilt">ungenau</button></span>`;

  // ─── A: Dicht ───
  function a() {
    return eintrag(`<div class="rh-detail sk-a">
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-circle-info"></i>Steckbrief</h4>
        <dl class="sk-werte"><dt>Stream</dt><dd>${strom}</dd>
          <dt>Codec</dt><dd>MP3 128 kbit/s ${info("laut Verzeichnis; Qualität mittel")}</dd><dt>Homepage</dt><dd><a href="#">rockantenne.de</a></dd>
          <dt>Sprache</dt><dd>Deutsch</dd><dt>Ort</dt><dd>Deutschland</dd>
          <dt>Geprüft</dt><dd><i class="fa-solid fa-check sk-gut"></i>erreichbar</dd><dt>Titel</dt><dd>${titelWahl}</dd></dl></section>
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-rectangle-ad"></i>Werbung <span class="sk-h4-zahl">18 Spots · 7 Werbende · ${MAL} ×</span>${info("aus den Sendedaten: Werbender, Kennung und Länge, wie der Sender sie angibt")}</h4>
        ${werbende(3, "a")}
        <div class="sk-reihe">${schalter(true, "Überspringen", "Angekündigte Werbung dieses Senders überspringen (Zeitversatz) oder stumm schalten (live)")}<span class="rh-still">Werbeverdacht: keiner</span></div></section>
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-star"></i>Meine Einschätzung${info("Nur für dich; wirkt in Filtern und Regeln")}</h4>${einschaetzung("a", { titel: false })}</section></div>`);
  }

  // ─── B: Reiter ───
  const REITER = [["steckbrief", "fa-circle-info", "Steckbrief", ""], ["werbung", "fa-rectangle-ad", "Werbung", "18"], ["einschaetzung", "fa-star", "Einschätzung", "3"]];
  let reiterB = "werbung";
  function b() {
    const inhalt = {
      steckbrief: `<dl class="sk-werte sk-werte-breit"><dt>Stream</dt><dd>${strom}</dd><dt>Codec</dt><dd>MP3 128 kbit/s · mittel</dd><dt>Homepage</dt><dd><a href="#">rockantenne.de</a></dd>
        <dt>Sprache</dt><dd>Deutsch</dd><dt>Ort</dt><dd>Deutschland</dd><dt>Geprüft</dt><dd><i class="fa-solid fa-check sk-gut"></i>erreichbar</dd><dt>Titel</dt><dd>${titelWahl}</dd><dt>Varianten</dt><dd><button class="knopf still sk-klein" type="button"><i class="fa-solid fa-layer-group"></i>8</button></dd></dl>`,
      werbung: `<div class="sk-reihe sk-reihe-kopf"><span class="rh-still">18 Spots von 7 Werbenden, zusammen ${MAL} × gehört</span>${schalter(true, "Überspringen", "Angekündigte Werbung dieses Senders überspringen")}</div>${werbende(4, "b")}`,
      einschaetzung: einschaetzung("b-voll", { titel: false }),
    }[reiterB];
    return eintrag(`<div class="sk-b">
      <div class="sk-reiterzeile"><div class="segment" role="tablist">${REITER.map(([id, sym, text, n]) => `<button type="button" role="tab" data-reiter="${id}" class="${reiterB === id ? "aktiv" : ""}" aria-selected="${reiterB === id}"><i class="fa-solid ${sym}"></i>${text}${n ? `<span class="pille">${n}</span>` : ""}</button>`).join("")}</div>
        ${reiterB === "einschaetzung" ? "" : einschaetzung("b", { titel: false })}</div>
      <div class="sk-b-inhalt">${inhalt}</div></div>`);
  }

  // ─── C: eine Zeile, Rest auf Klick ───
  function c() {
    const klappe = (id, sym, text, zusatz, inhalt, offen = false) => `<details class="sk-klappe"${offen ? " open" : ""}><summary><i class="fa-solid fa-chevron-right sk-pfeil"></i><i class="fa-solid ${sym}"></i>${text}${zusatz}</summary><div>${inhalt}</div></details>`;
    return eintrag(`<div class="sk-c">
      <div class="sk-angaben"><span><i class="fa-solid fa-music"></i>MP3 128 · mittel</span><span><i class="fa-solid fa-language"></i>Deutsch</span><span><i class="fa-solid fa-location-dot"></i>Deutschland</span>
        <span><i class="fa-solid fa-check sk-gut"></i>erreichbar</span><span><i class="fa-solid fa-clock"></i>Titel pünktlich</span><a href="#"><i class="fa-solid fa-house"></i>rockantenne.de</a>
        <span class="sk-trenner"></span>${einschaetzung("c", { titel: false })}</div>
      <div class="sk-klappen">
        ${klappe("strom", "fa-link", "Stream", "", `${strom} <span class="sk-reihe">Titelangaben ${titelWahl}</span>`)}
        ${klappe("werbung", "fa-rectangle-ad", "Werbung", `<span class="sk-h4-zahl">18 Spots · 7 Werbende</span><span class="sk-schalter-mini">${schalter(true, "Überspringen", "Angekündigte Werbung dieses Senders überspringen")}</span>`, werbende(5, "c"), true)}
      </div></div>`);
  }

  // ─── Zeichnen und Bedienung ───
  const VARIANTEN = { heute, a, b, c };
  function zeichnen() {
    $$("[data-variante]").forEach((el) => { el.innerHTML = VARIANTEN[el.dataset.variante](); });
    requestAnimationFrame(zeichnenHoehen);
  }
  document.addEventListener("click", (e) => {
    const t = e.target.closest("button, summary");
    if (!t) return;
    if (t.dataset.reiter) { reiterB = t.dataset.reiter; return zeichnen(); }
    if (t.dataset.tafel) {
      const tafel = $(`[data-tafel-fuer="${t.dataset.tafel}"]`);
      const auf = tafel.hidden;
      $$(".sk-tafel").forEach((x) => { x.hidden = true; });
      $$(".sk-plus").forEach((x) => x.setAttribute("aria-expanded", "false"));
      tafel.hidden = !auf;
      t.setAttribute("aria-expanded", String(auf));
      return;
    }
    if (t.dataset.alle) {
      $$(`[data-mehr="${t.dataset.alle}"]`).forEach((x) => { x.hidden = !x.hidden; });
      t.innerHTML = t.innerHTML.includes("alle") ? `<i class="fa-solid fa-chevron-up"></i>weniger` : `<i class="fa-solid fa-chevron-down"></i>alle ${WERBENDE.length} Werbenden`;
      return;
    }
    if (t.dataset.stern) { const n = Number(t.dataset.stern); z.sterne = z.sterne === n ? 0 : n; return zeichnenOffen(t); }
    if (t.dataset.marke && !t.closest("[data-variante='heute']")) { z.marken.has(t.dataset.marke) ? z.marken.delete(t.dataset.marke) : z.marken.add(t.dataset.marke); return zeichnenOffen(t); }
    if (t.dataset.kategorie && !t.closest("[data-variante='heute']")) { z.kategorien.has(t.dataset.kategorie) ? z.kategorien.delete(t.dataset.kategorie) : z.kategorien.add(t.dataset.kategorie); return zeichnenOffen(t); }
    if (t.dataset.thema) { document.documentElement.dataset.theme = t.dataset.thema; $$(".sk-wahl button").forEach((x) => x.classList.toggle("aktiv", x === t)); return zeichnen(); }
    if (t.dataset.zeige) return zeigen(t.dataset.zeige);
  });

  // Vergleichen: eine Fassung an derselben Stelle zeigen (oder alle untereinander); der Bildlauf bleibt, wo er ist
  function zeigen(welche) {
    document.body.dataset.zeige = welche;
    $$(".sk-sprung [data-zeige]").forEach((x) => x.classList.toggle("aktiv", x.dataset.zeige === welche));
    $$("[data-block]").forEach((b) => b.classList.toggle("sk-gezeigt", welche === "alle" || b.dataset.block === welche));
    zeichnenHoehen();
  }
  // nach einer Änderung in der Tafel bleibt sie offen
  function zeichnenOffen(t) {
    const offen = t.closest(".sk-tafel")?.dataset.tafelFuer;
    zeichnen();
    if (offen) { $(`[data-tafel-fuer="${offen}"]`).hidden = false; $(`[data-tafel="${offen}"]`)?.setAttribute("aria-expanded", "true"); }
  }
  document.addEventListener("toggle", () => zeichnenHoehen(), true);
  // Höhen: nur sichtbare Fassungen lassen sich messen; die übrigen behalten ihren letzten Wert
  const hoehen = {};
  function zeichnenHoehen() {
    $$("[data-variante]").forEach((v) => {
      const art = $("article", v);
      const h = art ? Math.round(art.getBoundingClientRect().height) : 0;
      if (h) hoehen[v.dataset.variante] = h;
    });
    $$("[data-fuer]").forEach((x) => { x.textContent = hoehen[x.dataset.fuer] ? `${hoehen[x.dataset.fuer]} px` : ""; });
  }
  // einmal alle zeigen, um jede Höhe zu kennen, dann die gewählte Fassung
  function anfangen() {
    const welche = document.body.dataset.zeige || "a";
    zeichnen();
    zeigen("alle");
    requestAnimationFrame(() => { zeichnenHoehen(); zeigen(welche); });
  }
  customElements.whenDefined("ak-led").then(anfangen);
  document.fonts?.ready.then(() => setTimeout(anfangen, 50));
})();
