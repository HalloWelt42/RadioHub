// Telefon im Entwurf RAD-3: vier Rahmen mit derselben Oberfläche in verschiedenen Lagen (Liste, Filterblatt offen,
// Spieler groß, anderes Gerät spielt). Jeder Rahmen ist für sich bedienbar: Filter öffnen und wählen, Spieler öffnen,
// Ton holen. Ein Baustein baut alle Rahmen, damit sie gleich aussehen.

(() => {
  "use strict";
  const D = window.RHDaten, R = window.RH;
  const $ = (s, w) => w.querySelector(s), $$ = (s, w) => [...w.querySelectorAll(s)];
  const liste = D.SENDER.filter((s) => s.land === "DE" && s.stimmen >= 10).sort((a, b) => b.stimmen - a.stimmen);

  const zeile = (s, spielt) => `<div class="t-zeile${spielt ? " spielt" : ""}" data-id="${s.id}">${R.logo(s)}
    <div><b>${R.esc(s.name)}</b><div class="t-meta"><span class="rh-kennung">${s.land}</span>${R.guete(s.guete)}<span>${s.kbps ? `${s.codec} ${s.kbps}` : `${s.codec} ?`}</span>${s.varianten.length ? `<span class="t-var"><i class="fa-solid fa-layer-group"></i>${s.varianten.length} Varianten</span>` : ""}</div>
    <div class="t-titel"><i class="fa-solid ${spielt ? "fa-volume-high" : "fa-music"}"></i>${R.esc(s.titel)}</div></div>
    <button class="rund${s.favorit ? " favorit" : ""}" type="button" aria-label="Favorit" aria-pressed="${s.favorit}" title="Favorit"><i class="fa-${s.favorit ? "solid" : "regular"} fa-star"></i></button></div>`;

  const chips = (gruppe, werte, an, fmt = (w) => w) => `<div class="t-chipwahl">${werte.map(([w, n]) => `<button type="button" class="chip wahl${an.includes(w) ? " an" : ""}" data-gruppe="${gruppe}">${fmt(w)}<span class="rh-zahl">${R.zahl(n)}</span></button>`).join("")}</div>`;

  function blatt() {
    return `<button class="t-schleier" type="button" data-t="zu" aria-label="Filter schließen" hidden></button>
    <div class="t-blatt" role="dialog" aria-label="Filter" hidden>
      <div class="t-blatt-kopf"><h2>Filter</h2><button class="knopf still" type="button" data-t="zurueck">Zurücksetzen</button><button class="rund" type="button" data-t="zu" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button></div>
      <div class="t-blatt-rollt">
        <div class="ak-geraet rh-schnellwahl" data-bauform="inspektor">
          <span class="ak-schraube lo" style="--dreh:22deg"></span><span class="ak-schraube ro" style="--dreh:64deg"></span><span class="ak-schraube lu" style="--dreh:-18deg"></span><span class="ak-schraube ru" style="--dreh:41deg"></span>
          <div class="rh-schnellwahl-oben"><ak-taster art="flach" beschriftung="Nur Favoriten" farbe="gelb" hilfe="Nur Favoriten zeigen"></ak-taster>
            <ak-dreh name="Stimmen" hilfe="Mindestzahl der Stimmen" raster="alle|ab 10|ab 100|ab 1.000|ab 10.000" wert="1" vorgabe="0"></ak-dreh></div>
          <ak-schieber art="balken" leuchte="gruen" segmente="5" name="Mindestbitrate" hilfe="Mindestbitrate aus der eigenen Messung" raster="alle|64|128|192|256|320" wert="0"></ak-schieber>
        </div>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Länder</h3></div>${chips("land", D.FACETTEN.land.werte, ["DE"], (w) => D.LAENDER[w])}</section>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Genres</h3></div>${chips("genre", D.FACETTEN.genre.werte, [])}</section>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Qualität</h3><span class="rh-still">gemessen</span></div>${chips("guete", D.FACETTEN.guete.werte, [], (w) => `${R.guete(w)}${w}`)}</section>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Codec</h3></div>${chips("codec", D.FACETTEN.codec.werte, [])}</section>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Eigene Bewertung</h3></div>${chips("bewertung", D.FACETTEN.bewertung.werte, [], (w) => (w === "werbung" ? `<i class="fa-solid fa-rectangle-ad"></i>Werbung` : `${R.sterne(Number(w))}${D.BEWERTUNG_NAMEN[w]}`))}</section>
        <section class="rh-gruppe"><div class="rh-gruppe-kopf"><h3>Eigene Kategorien</h3></div>${chips("kategorie", D.FACETTEN.kategorie.werte, [])}</section>
      </div>
      <div class="t-blatt-fuss"><button class="knopf primaer" type="button" data-t="zu"><i class="fa-solid fa-check"></i><span data-t-treffer>2.493</span> Sender zeigen</button></div>
    </div>`;
  }

  function gross(s, fern) {
    const geraete = [[true, "fa-mobile-screen", "Telefon", "dieses Gerät", fern ? "Holen" : ""], [true, "fa-desktop", "Rechner im Arbeitszimmer", fern ? "spielt gerade" : "bereit", fern ? "" : "Abspielen"],
      [true, "fa-microchip", "Pi in der Küche", "bereit", "Abspielen"], [false, "fa-tv", "Wohnzimmer", "nicht erreichbar", ""]];
    return `<div class="t-gross" role="dialog" aria-label="Spieler" hidden>
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div><div class="t-luft"></div>
      <div class="t-gross-kopf"><button class="rund" type="button" data-t="klein" aria-label="Spieler verkleinern" title="Verkleinern"><i class="fa-solid fa-chevron-down"></i></button><span class="ak-etikett">Radio</span><span></span></div>
      <div class="t-gross-rollt">
        <div class="ak-glas rh-display"${fern ? ` data-ton="fern"` : ""}>
          <div class="rh-display-zeile"><span>${fern ? "SPIELT AUF RECHNER" : "LIVE"}</span><span class="rh-display-format">${R.guete(s.guete)}<span>${R.bitrate(s)}</span></span></div>
          <ak-segmente art="punkt" stellen="14" lauf="300" farbe="${fern ? "blau" : "gruen"}" text="${R.esc(s.name.toUpperCase())}"></ak-segmente>
          <div class="rh-display-titel">${R.esc(s.titel)}</div>
        </div>
        <div class="ak-geraet t-gross-laut" data-bauform="inspektor"><span class="ak-schraube lo" style="--dreh:12deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span>
          <span class="rh-vu">VU<ak-pegel richtung="senkrecht" kanaele="1" segmente="16" skala="" beschriftung="Pegel links"${fern ? ` wert="-60"` : ""}></ak-pegel>L</span>
          <ak-dreh name="Lautstärke" hilfe="Lautstärke${fern ? " des Rechners (Fernbedienung)" : ""}" wert="${fern ? 55 : 70}" vorgabe="50" einheit="%" grenzen="Leise|Laut"></ak-dreh>
          <span class="rh-vu">VU<ak-pegel richtung="senkrecht" kanaele="1" segmente="16" skala="" beschriftung="Pegel rechts"${fern ? ` wert="-60"` : ""}></ak-pegel>R</span></div>
        <div class="t-transport">
          <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="Vorheriger Sender der sichtbaren Liste"></ak-taster>
          <ak-taster art="glas" symbol="fa-stop" farbe="weiss" led="weiss" modus="tasten" hilfe="Stopp"></ak-taster>
          <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="Hören oder anhalten" an></ak-taster>
          <ak-taster art="glas" symbol="fa-circle" farbe="rot" led="rot" hilfe="Aufnahme starten"></ak-taster>
          <ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="Nächster Sender der sichtbaren Liste"></ak-taster>
        </div>
        <div class="t-versatz"><ak-schieber art="leuchte" leuchte="bernstein" segmente="30" name="Zeitversatz" hilfe="Zurückspulen im Puffer, höchstens 30 Minuten" min="-30" max="0" schritt="0.5" wert="0" einheit="min" grenzen="-30 min|live"></ak-schieber>
          <button class="knopf" type="button" disabled title="Schon live"><i class="fa-solid fa-tower-broadcast"></i>Live</button></div>
        <div class="t-geraete"><span class="ak-etikett">Hausempfang: abspielen auf</span>
          ${geraete.map(([erreichbar, sym, n, st, k]) => `<div class="t-geraet${erreichbar ? "" : " aus"}"><i class="fa-solid ${sym}"></i><span><b>${n}</b><span>${st}</span></span>${k ? `<button class="knopf${k === "Holen" ? " primaer" : ""}" type="button" data-t="${k === "Holen" ? "holen" : "geben"}">${k === "Holen" ? `<i class="fa-solid fa-hand-holding"></i>` : `<i class="fa-solid fa-tower-broadcast"></i>`}${k}</button>` : "<span></span>"}</div>`).join("")}
        </div>
      </div>
    </div>`;
  }

  function telefon(ziel, { fern = false } = {}) {
    const s = D.SENDER.find((x) => x.id === (fern ? "wdr3" : "dlfk"));
    ziel.innerHTML = `<div class="t-app">
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div>
      <div class="t-luft" aria-hidden="true"></div>
      <div class="t-kopf"><span class="rh-logo">RadioHub</span><button class="rh-herz" type="button" aria-label="Unterstützen" title="Unterstützen"><i class="fa-solid fa-heart"></i></button>
        <div class="t-kopf-rechts"><span class="t-haus-mini" title="${fern ? "Hausempfang: spielt auf dem Rechner im Arbeitszimmer" : "Hausempfang: spielt auf diesem Telefon"}"><i class="fa-solid ${fern ? "fa-desktop" : "fa-mobile-screen"}"></i></span>
          <button class="rund" type="button" title="Darstellung" aria-label="Darstellung" data-t="darstellung"><i class="fa-solid fa-circle-half-stroke"></i></button></div></div>
      <div class="t-suche"><label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input type="search" placeholder="Sender suchen" aria-label="Sender suchen"></label>
        <button class="knopf" type="button" data-t="filter"><i class="fa-solid fa-sliders"></i>Filter<span class="pille">2</span></button></div>
      <div class="t-chips"><span class="t-treffer" title="Treffer gesamt"><ak-segmente art="7" stellen="5" farbe="gruen" text="2.493"></ak-segmente>Treffer</span>
        <span class="chip">Deutschland<button type="button" aria-label="Filter entfernen"><i class="fa-solid fa-xmark"></i></button></span><span class="chip">Stimmen ab 10<button type="button" aria-label="Filter entfernen"><i class="fa-solid fa-xmark"></i></button></span></div>
      <div class="t-liste">
        <p class="rh-hinweis t-hinweis"><span><b>8.249</b> durch Regeln aus</span><a href="regeln.html">Regeln<i class="fa-solid fa-arrow-right"></i></a></p>
        ${liste.map((x) => zeile(x, x.id === s.id)).join("")}
      </div>
      <div class="t-spieler" data-t="gross" role="button" aria-label="Spieler öffnen">
        <div class="ak-glas${fern ? " fern" : ""}"><b>${fern ? "Spielt auf Rechner" : R.esc(s.name)}</b><span>${fern ? `${R.esc(s.name)}: ${R.esc(s.titel)}` : R.esc(s.titel)}</span></div>
        <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="${fern ? "Am Rechner anhalten" : "Anhalten"}" an></ak-taster>
        ${fern ? `<button class="knopf primaer" type="button" data-t="holen" title="Ton auf dieses Telefon holen"><i class="fa-solid fa-hand-holding"></i>Holen</button>` : `<button class="rund" type="button" data-t="gross" aria-label="Spieler öffnen" title="Spieler öffnen"><i class="fa-solid fa-chevron-up"></i></button>`}
      </div>
      <nav class="t-reiter" aria-label="Bereiche"><span class="aktiv"><i class="fa-solid fa-radio"></i>Radio</span><span><i class="fa-solid fa-circle-dot"></i>Aufnahmen</span><span><i class="fa-solid fa-podcast"></i>Podcasts</span><span><i class="fa-solid fa-ellipsis"></i>Mehr</span></nav>
      ${blatt()}
      ${gross(s, fern)}
      <div class="rh-tafel" data-t-tafel hidden role="dialog" aria-label="Darstellung">
        <div><h3>Vorlage</h3><div class="segment" role="group" aria-label="Vorlage"><button type="button" data-vorlage-wahl="hifi"><i class="fa-solid fa-compact-disc"></i>HiFi</button><button type="button" data-vorlage-wahl="ruhig"><i class="fa-solid fa-feather"></i>Ruhig</button></div></div><div><h3>Thema</h3><div class="segment" role="group" aria-label="Thema"><button type="button" data-thema-wahl="hell"><i class="fa-solid fa-sun"></i>Hell</button><button type="button" data-thema-wahl="dunkel"><i class="fa-solid fa-moon"></i>Dunkel</button><button type="button" data-thema-wahl="system"><i class="fa-solid fa-display"></i>System</button></div></div>
        <div><h3>Schrift</h3><div class="rh-schrift-wahl"><button class="knopf" type="button" data-schrift-schritt="-1" aria-label="Schrift kleiner"><i class="fa-solid fa-minus"></i></button><output data-schrift-anzeige>Normal</output><button class="knopf" type="button" data-schrift-schritt="1" aria-label="Schrift größer"><i class="fa-solid fa-plus"></i></button></div></div>
      </div>
      <div class="rh-band" data-t-band hidden></div>
    </div>`;
    window.RHDarstellung.binden(ziel);
    R.tastenlicht(ziel);
    const auf = (sel, an) => { $(sel, ziel).hidden = !an; };
    ziel.onclick = (e) => {
      const k = e.target.closest("[data-t]");
      const chip = e.target.closest(".t-chipwahl .chip.wahl");
      if (chip) { chip.classList.toggle("an"); const n = $$(".t-blatt .chip.wahl.an", ziel).length; $("[data-t-treffer]", ziel).textContent = R.zahl(Math.max(12, Math.round(2493 / (1 + n * 1.7)))); return; }
      if (!k) return;
      const t = k.dataset.t;
      if (t === "filter") { auf(".t-blatt", true); auf(".t-schleier", true); }
      if (t === "zu") { auf(".t-blatt", false); auf(".t-schleier", false); }
      if (t === "zurueck") { $$(".t-blatt .chip.wahl.an", ziel).forEach((c) => c.classList.remove("an")); $("[data-t-treffer]", ziel).textContent = "49.081"; }
      if (t === "gross" && !e.target.closest("ak-taster, [data-t='holen']")) auf(".t-gross", true);
      if (t === "klein") auf(".t-gross", false);
      if (t === "darstellung") { e.stopPropagation(); const tf = $("[data-t-tafel]", ziel); tf.hidden = !tf.hidden; return; }
      if (t === "holen") { e.stopPropagation(); telefon(ziel, { fern: false }); const b = $("[data-t-band]", ziel); b.innerHTML = `<i class="fa-solid fa-hand-holding" style="color:var(--led-blau)"></i><span>Ton geholt: spielt jetzt auf diesem Telefon</span>`; b.hidden = false; setTimeout(() => { b.hidden = true; }, 5000); return; }
      if (t === "geben") { e.stopPropagation(); telefon(ziel, { fern: true }); return; }
    };
  }

  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-telefon]").forEach((el) => {
      const lage = el.dataset.telefon;
      telefon(el, { fern: lage === "fern" });
      if (lage === "blatt") { el.querySelector(".t-blatt").hidden = false; el.querySelector(".t-schleier").hidden = false; }
      if (lage === "gross") el.querySelector(".t-gross").hidden = false;
    });
  });
})();
