// Werbung im Radio (Entwurf RAD-33): Werbung aus den Sendedaten. Der Spot beim Verbinden wird nicht gespielt (die
// Wiedergabe beginnt nach ihm), im Zeitversatz wird Werbung übersprungen (mit Zurück und anhören), live schaltet die
// Wiedergabe stumm und zeigt die Restzeit. Sender, die Werbung ankündigen, tragen eine Marke; im Steckbrief stehen die
// bekannten Spots und der Schalter je Sender, in den Einstellungen der Schalter für alle. Nur Entwurf, Musterdaten
// (Werbende erfunden).
(() => {
  "use strict";
  const D = window.RHDaten, R = window.RH, esc = R.esc;
  const S = D.SENDER.find((x) => x.id === "80s");                  // ein Sender, der Werbung ankündigt
  const zeit = (s) => `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`;
  const SPOTS = [
    { werbender: "moebelhaus-am-see.de", titel: "Herbstaktion Sofas", laenge: 15.05, mal: 9, zuletzt: "heute 10:42", art: "beim Verbinden" },
    { werbender: "werkzeugladen.de", titel: "Akkuschrauber Woche", laenge: 20.09, mal: 6, zuletzt: "heute 10:31", art: "im Programm" },
    { werbender: "bäckerei-sonnenkorn.de", titel: "Frühstück zum Mitnehmen", laenge: 25.55, mal: 3, zuletzt: "gestern 18:05", art: "im Programm" },
  ];
  // Werbestellen im Puffer (Minuten zurück): der Zeitversatz zeigt sie in der Spulzeile
  const PUFFER = 30, STELLEN = [{ von: 3.2, bis: 3.6 }, { von: 11.0, bis: 12.4 }, { von: 21.5, bis: 22.1 }];

  const schalter = (an, text, hilfe = "") => `<button class="knopf rh-schalter" type="button" aria-pressed="${an}" title="${esc(hilfe)}">
      <ak-led farbe="bernstein" zustand="${an ? "an" : "aus"}" groesse="klein"></ak-led>${text}</button>`;

  // Anzeige und Quelle/Zeit der Kanzel; `ton` färbt die Anzeige (werbung: bernstein)
  const anzeige = ({ art, led, titel, ton = "werbung", lauf = S.name }) => `<section class="rh-modul rh-m-anzeige" aria-label="Anzeige"><span class="ak-etikett">Anzeige</span>
      <div class="ak-glas rh-display" data-ton="${ton}">
        <div class="rh-display-zeile"><ak-led farbe="${led[0]}" zustand="${led[1]}" groesse="klein"></ak-led><span>${art}</span><span class="rh-display-format">${R.guete(S.guete)}<span>${R.bitrate(S)}</span></span></div>
        <ak-segmente art="punkt" stellen="16" lauf="280" farbe="gruen" text="${esc(lauf.toUpperCase())}" hilfe="Sender"></ak-segmente>
        <div class="rh-display-titel">${titel}</div>
      </div></section>`;
  // Spulzeile: `gefuellt` Minuten im Puffer (rechts ist live), Werbestellen in Minuten ab Beginn des Puffers
  const spulzeile = ({ gefuellt = PUFFER, stellen = STELLEN, versatz = 0 }) => {
    const pz = (m) => (m / PUFFER) * 100, kopf = gefuellt - versatz;
    return `<div class="rh-puffer-zeile">
      <button class="knopf" type="button" title="30 Sekunden zurück"${gefuellt < 0.5 ? " disabled" : ""}><i class="fa-solid fa-rotate-left"></i>30 s</button>
      <div class="rh-puffer rp-puffer" title="Zeitversatz, Werbung bernstein">
        <div class="rp-leiste" role="img" aria-label="Puffer mit ${stellen.length} Werbestellen">
          <span class="rp-gehoert" style="width:${pz(kopf)}%"></span>
          ${stellen.map((x) => `<span class="rp-werbung" style="left:${pz(x.von)}%;width:${Math.max(0.8, pz(x.bis - x.von))}%"></span>`).join("")}
          <span class="rp-kopf" style="left:${pz(kopf)}%"></span></div>
        <span>${versatz ? `${zeit(versatz * 60)} hinter live · ` : ""}${zeit(gefuellt * 60)} von 30:00${stellen.length ? ` · <span class="rp-ohne">${stellen.length} × Werbung</span>` : ""}</span></div>
      <button class="knopf" type="button" title="Zurück zu live"${versatz ? "" : " disabled"}><i class="fa-solid fa-tower-broadcast"></i>Live</button></div>`;
  };
  const quelle = ({ text, farbe, uhr, puffer = {} }) => `<section class="rh-modul rh-m-zeit" aria-label="Quelle und Zeit"><span class="ak-etikett">Quelle und Zeit</span>
      <div class="rh-zeit"><div class="ak-glas rh-zeit-glas">
        <ak-segmente art="14" stellen="7" farbe="${farbe}" text="${text}" hilfe="Quelle der Wiedergabe"></ak-segmente>
        <ak-segmente art="7" stellen="7" farbe="gruen" text="${uhr}" hilfe="Hördauer, im Zeitversatz der Abstand zu live"></ak-segmente></div>
        ${spulzeile(puffer)}</div></section>`;
  const band = (inhalt) => `<div class="rh-band rp-band" role="status">${inhalt}</div>`;

  // 1: Spot beim Verbinden: nicht spielen, die Wiedergabe beginnt nach ihm
  function verbinden(el) {
    el.innerHTML = `<div class="rp-kanzel rw-kanzel">
      ${anzeige({ art: "WERBUNG BEIM VERBINDEN", led: ["bernstein", "atmet"], titel: "Wiedergabe beginnt nach dem Spot, noch 0:12" })}
      ${quelle({ text: "WERBUNG", farbe: "bernstein", uhr: "-00:00:12", puffer: { gefuellt: 0.05, stellen: [{ von: 0, bis: 0.25 }] } })}
      ${band(`<i class="fa-solid fa-rectangle-ad"></i><span><b>Werbung beim Verbinden</b> (0:15, moebelhaus-am-see.de): RadioHub spielt sie nicht, noch <b class="rh-zahl">0:12</b></span>
        <button class="knopf" type="button" title="Den Spot doch hören"><i class="fa-solid fa-volume-high"></i>Trotzdem hören</button>`)}
    </div>`;
  }

  // 2: Zeitversatz: übersprungen
  function versatz(el) {
    el.innerHTML = `<div class="rp-kanzel rw-kanzel">
      ${anzeige({ art: "4:12 HINTER LIVE", led: ["bernstein", "an"], titel: "Neonwelle: Herz aus Glas", ton: "" })}
      ${quelle({ text: "VERSATZ", farbe: "bernstein", uhr: "-00:04:12", puffer: { versatz: 4.2 } })}
      ${band(`<i class="fa-solid fa-forward"></i><span><b>Werbung übersprungen</b> (0:20, werkzeugladen.de)</span>
        <button class="knopf" type="button"><i class="fa-solid fa-rotate-left"></i>Zurück und anhören</button>
        <button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`)}
    </div>`;
  }

  // 3: Live: der Puffer reicht nicht zum Springen; stumm bis zum Ende, Ton an auf Wunsch
  function stumm(el) {
    el.innerHTML = `<div class="rp-kanzel rw-kanzel">
      ${anzeige({ art: "WERBUNG, STUMM", led: ["bernstein", "atmet"], titel: "Werbung läuft, stumm noch 0:14" })}
      ${quelle({ text: "LIVE", farbe: "blau", uhr: "00:42:17", puffer: { stellen: [...STELLEN, { von: 29.85, bis: 30 }] } })}
      ${band(`<i class="fa-solid fa-volume-xmark"></i><span><b>Werbung läuft</b> (werkzeugladen.de): stumm noch <b class="rh-zahl">0:14</b>, dann wieder mit Ton</span>
        <button class="knopf" type="button" title="Den Spot doch hören"><i class="fa-solid fa-volume-high"></i>Ton an</button>`)}
    </div>`;
  }

  // 4: Senderliste: Marke an Sendern, die Werbung ankündigen
  const marke = (n) => `<span class="rp-marke" title="Kündigt Werbung in den Sendedaten an, ${n} Spots bekannt; wird übersprungen"><i class="fa-solid fa-rectangle-ad"></i>Werbung</span>`;
  function zeile(s, mitMarke, spielt = false) {
    return `<article class="rh-sender${spielt ? " spielt" : ""}"><div class="rh-sender-kern">
      <span class="led"><ak-led farbe="${spielt ? "blau" : "gelb"}" zustand="${spielt ? "an" : "aus"}" groesse="klein"></ak-led></span>${R.logo(s)}
      <div class="name"><b>${esc(s.name)}</b><div class="meta"><span class="rh-kennung">${s.land}</span><span>${esc(s.ort)}</span>${mitMarke ? marke(18) : ""}</div></div>
      <div class="genres">${s.genres.map((g) => `<span class="rh-genre">${g}</span>`).join("")}</div>
      <div class="guete-zelle">${R.guete(s.guete)}<b>${D.GUETE[s.guete].name}</b><span>${s.codec} ${R.zahl(s.kbps)}</span></div>
      <div class="stimmen"><span><i class="fa-solid fa-thumbs-up"></i>${R.zahl(s.stimmen)}</span></div>
      <div class="rh-aktionen"><span class="rh-platz"></span><button class="rund" type="button" aria-label="Favorit"><i class="fa-regular fa-star"></i></button>
        <span class="auge-zelle"><button class="rund" type="button" aria-label="Ausblenden"><i class="fa-solid fa-eye-slash"></i></button></span>
        <button class="rund" type="button" aria-label="Details"><i class="fa-solid fa-chevron-down"></i></button></div>
    </div></article>`;
  }
  function liste(el) {
    const ids = [["80s", true, true], ["sl", true], ["dlfk", false], ["rp", false]];
    el.innerHTML = `<div class="rp-rechner rh-liste">${ids.map(([id, m, sp]) => zeile(D.SENDER.find((x) => x.id === id), m, sp)).join("")}</div>`;
  }

  // 5: Steckbrief: bekannte Spots und der Schalter je Sender
  function steckbrief(el) {
    el.innerHTML = `<div class="rp-rechner"><div class="rh-detail rw-detail">
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-circle-info"></i>Steckbrief</h4>
        <dl class="rh-werte"><dt>Codec</dt><dd>${R.bitrate(S)} gemessen</dd>
          <dt>Werbung</dt><dd><span class="rp-marke"><i class="fa-solid fa-rectangle-ad"></i>kündigt Werbung an</span>, 18 Spots seit 21. Nov., zuletzt heute 10:42</dd></dl>
        <div class="rh-detail-knoepfe">${schalter(true, "Werbung überspringen", "Angekündigte Werbung dieses Senders überspringen (Zeitversatz) oder stumm schalten (live)")}</div></section>
      <section class="rh-tafel-detail rw-spots"><h4><i class="fa-solid fa-rectangle-ad"></i>Bekannte Spots</h4>
        <ol class="rp-stellen">${SPOTS.map((x, i) => `<li><span class="rh-a-nr">${String(i + 1).padStart(2, "0")}</span>
          <span class="rp-zeit"><b>${zeit(x.laenge)}</b><span>${x.mal} ×</span></span>
          <span class="rp-herkunft"><span><i class="fa-solid ${x.art === "beim Verbinden" ? "fa-plug" : "fa-tower-broadcast"}"></i>${esc(x.werbender)}</span><span class="rh-still">${esc(x.titel)} · ${x.art} · zuletzt ${x.zuletzt}</span></span></li>`).join("")}</ol>
        <span class="rh-still">aus den Sendedaten: Werbender, Kennung und Länge, wie der Sender sie angibt</span></section>
    </div></div>`;
  }

  // 6: Einstellungen, Bereich Werbeerkennung: eine Zeile mehr
  function einstellungen(el) {
    el.innerHTML = `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-rectangle-ad"></i>Werbung in den Sendedaten</h2></div>
      <p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>Viele Sender kündigen Werbung in ihren Sendedaten an. RadioHub spielt den Spot beim Verbinden nicht, überspringt Werbung im Zeitversatz und schaltet live stumm, bis sie vorbei ist. Je Sender abschaltbar im Steckbrief.</span></p>
      <div class="rh-e-zeilen"><div class="rh-e-zeile"><div class="rh-e-beschreibung"><div class="rh-e-name"><b>Angekündigte Werbung überspringen</b>
          <span class="rh-geltung alle" title="Gilt für alle Geräte"><i class="fa-solid fa-house"></i>Alle Geräte</span></div>
          <p>Gilt für alle Sender; aus heißt: Werbung wird gespielt wie gesendet, die Marken bleiben sichtbar.</p></div>
        <div class="rh-e-wert"><ak-taster art="flach" beschriftung="An" farbe="gruen" an hilfe="Angekündigte Werbung überspringen"></ak-taster></div></div>
        <div class="rh-e-zeile"><div class="rh-e-beschreibung"><div class="rh-e-name"><b>Sender mit Werbung</b>
          <span class="rh-geltung alle"><i class="fa-solid fa-house"></i>Alle Geräte</span></div>
          <p>5 Sender kündigen Werbung an, 41 Spots bekannt; 1 Sender ist ausgenommen.</p></div>
        <div class="rh-e-wert"><a class="knopf" href="#" onclick="return false"><i class="fa-solid fa-list"></i>Liste</a></div></div></div></div>`;
  }

  // 7 und 8: Telefon
  const rahmen = (spieler, zusatz = "") => `<div class="t-app rw-t-app">
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div>
      <div class="t-luft" aria-hidden="true"></div>
      <div class="t-kopf"><span class="rh-logo">RadioHub</span></div>
      <div class="t-liste">${["80s", "sl", "dlfk"].map((id) => { const s = D.SENDER.find((x) => x.id === id); return `<div class="t-zeile${id === "80s" ? " spielt" : ""}">${R.logo(s)}
        <div><b>${esc(s.name)}</b><div class="t-meta"><span>${esc(s.genres.join(", "))}</span>${id !== "dlfk" ? `<span class="rp-marke"><i class="fa-solid fa-rectangle-ad"></i>Werbung</span>` : ""}</div></div>
        <button class="rund" type="button" aria-label="Hören"><i class="fa-solid fa-${id === "80s" ? "volume-high" : "play"}"></i></button></div>`; }).join("")}</div>
      ${spieler}
      <nav class="t-reiter" aria-label="Bereiche"><span class="aktiv"><i class="fa-solid fa-radio"></i>Radio</span><span><i class="fa-solid fa-circle-dot"></i>Aufnahmen</span><span><i class="fa-solid fa-podcast"></i>Podcasts</span><span><i class="fa-solid fa-ellipsis"></i>Mehr</span></nav>
      ${zusatz}</div>`;
  const spieler = (zeile2, symbol) => `<div class="t-spieler rw-t-spieler"><div class="ak-glas"><b><ak-led farbe="bernstein" zustand="atmet" groesse="klein"></ak-led>${esc(S.name)}</b><span>${zeile2}</span></div>
      <ak-taster art="glas" symbol="${symbol}" farbe="blau" led="blau" hilfe="Anhalten" an></ak-taster>
      <button class="rund" type="button" aria-label="Spieler öffnen"><i class="fa-solid fa-chevron-up"></i></button></div>`;
  function telefonVerbinden(el) {
    el.innerHTML = rahmen(spieler("Werbung, noch 0:12", "fa-pause"),
      `<div class="rh-band rp-band rp-band-telefon" role="status"><i class="fa-solid fa-rectangle-ad"></i><span><b>Werbung beim Verbinden</b>: noch <b class="rh-zahl">0:12</b></span>
        <button class="knopf" type="button"><i class="fa-solid fa-volume-high"></i>Hören</button></div>`);
  }
  function telefonStumm(el) {
    el.innerHTML = rahmen(spieler("Werbung, stumm 0:14", "fa-pause"),
      `<div class="rh-band rp-band rp-band-telefon" role="status"><i class="fa-solid fa-volume-xmark"></i><span><b>Werbung läuft</b>: stumm noch <b class="rh-zahl">0:14</b></span>
        <button class="knopf" type="button"><i class="fa-solid fa-volume-high"></i>Ton an</button></div>`);
  }

  const ZUSTAENDE = { verbinden, versatz, stumm, liste, steckbrief, einstellungen, "telefon-verbinden": telefonVerbinden, "telefon-stumm": telefonStumm };
  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-zustand]").forEach((el) => { ZUSTAENDE[el.dataset.zustand](el); R.tastenlicht?.(el); });
  });
})();
