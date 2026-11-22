// Puffer und Aufnahme (Entwurf RAD-46). Der Zeitversatz kennt seine Abschnitte (Titel, Werbung, Einschübe) mit Grenzen
// nach der Regel des Feinschnitts; der Balken zeigt sie als Striche und violette Flächen, darunter steht der Titel, den
// man hört. Die Großansicht zeigt den ganzen Puffer als Zeitleiste mit Zoom und als Liste; dort springt man hin, nimmt
// ab einem Titel auf oder sichert einen Bereich. Eine Aufnahme beginnt am Anfang des laufenden Titels (rot im Balken).
// Daten: 90s90s Hits am 22.11.2026 ab 01:08:30, Titel und Zeiten aus den Sendedaten (Protokoll des Pi).
(() => {
  "use strict";
  const R = window.RH, esc = R.esc;
  const S = { name: "90s90s Hits", guete: "mittel", codec: "MP3", kbps: 192 };
  const BEGINN = "01:08:30", PUFFER_MAX = 7200, JETZT = 4790;          // Sekunden im Puffer; 4790 = 02:28:20
  // Angaben der Sendedaten (Sekunde im Ton); die Grenze liegt an der Pause davor (hier 0,8 s früher)
  const ANGABEN = [[0.3, "90s90s - DIGITAL WEB"], [10.2, "OMC - How Bizarre"], [289.1, "Shaggy - Boombastic"], [525.7, "Cut 'n' Move - Give It Up"],
    [845.8, "Bloodhound Gang - The Bad Touch"], [1094.0, "Robbie Williams - Millennium"], [1292.6, "Toni Braxton - Un-Break My Heart (Zuccare Remix)"],
    [1554.8, "Duran Duran - Ordinary World"], [1828.2, "Seal - Crazy"], [2120.0, "Sixpence None the Richer - Kiss Me"], [2323.5, "Fettes Brot - Jein"],
    [2590.7, "Madonna - Deeper and Deeper"], [2883.6, "Christina Aguilera - Genie in a Bottle"], [3104.8, "The KLF - 3 A.M. Eternal (live)"],
    [3428.4, "No Mercy - Where Do You Go"], [3699.0, "Spice Girls - Wannabe"], [3860.8, "Snap! - Rhythm Is a Dancer"], [4114.1, "Ace of Base - Wheel of Fortune"],
    [4328.4, "Destiny's Child - Say My Name"], [4586.5, "Prince Ital Joe & Marky Mark - United"]];
  // Abschnitte wie GET /api/hls/abschnitte: von, bis, titel, art; der Vorlauf beim Verbinden ist Werbung
  const abschnitte = (jetzt = JETZT) => ANGABEN.filter(([t]) => t < jetzt).map(([t, titel], i, a) => {
    const von = i === 0 ? 0 : t - 0.8, bis = i + 1 < a.length ? a[i + 1][0] - 0.8 : jetzt;
    return i === 0 ? { von, bis, titel: "Werbung beim Verbinden", art: "werbung", nr: i + 1 } : { von, bis, titel, art: "titel", nr: i + 1, laufend: i + 1 === a.length };
  });
  const A = abschnitte();
  const zeit = (s, mitStunde = false) => {
    s = Math.max(0, Math.round(s)); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = String(s % 60).padStart(2, "0");
    return h || mitStunde ? `${h}:${String(m).padStart(2, "0")}:${x}` : `${m}:${x}`;
  };
  const uhr = (s) => { const [h, m, x] = BEGINN.split(":").map(Number), t = h * 3600 + m * 60 + x + Math.round(s); return `${String(Math.floor(t / 3600) % 24).padStart(2, "0")}:${String(Math.floor((t % 3600) / 60)).padStart(2, "0")}`; };
  const bei = (t) => A.find((a) => t >= a.von && t < a.bis) ?? A[A.length - 1];
  const pz = (t, von = 0, bis = JETZT) => ((t - von) / (bis - von)) * 100;

  // Balken: Fortschritt bis zur Stelle (gelb wie in der App), Striche an den Titelgrenzen, Werbung violett, eine Aufnahme
  // rot hinterlegt, ein Bereich umrandet; `tipp` zeigt den Titel einer Marke wie beim Überfahren
  function balken({ stelle = JETZT, aufnahme = null, bereich = null, tipp = null, von = 0, bis = JETZT, klasse = "" } = {}) {
    const sicht = A.filter((a) => a.bis > von && a.von < bis);
    return `<div class="pz-bahn ${klasse}">
      <div class="balken pz-balken"><span style="width:${pz(stelle, von, bis)}%"></span>
        ${aufnahme ? `<i class="pz-aufnahme" style="left:${pz(aufnahme, von, bis)}%;width:${100 - pz(aufnahme, von, bis)}%"></i>` : ""}
        ${sicht.filter((a) => a.art === "werbung").map((a) => `<i class="rh-werbemarke" style="left:${Math.max(0, pz(a.von, von, bis))}%;width:${Math.max(0.6, pz(a.bis, von, bis) - pz(a.von, von, bis))}%"></i>`).join("")}</div>
      <div class="pz-striche" aria-hidden="true">${sicht.filter((a) => a.von > von).map((a) => `<i style="left:${pz(a.von, von, bis)}%"></i>`).join("")}</div>
      ${bereich ? `<i class="pz-bereich" style="left:${pz(bereich[0], von, bis)}%;width:${pz(bereich[1], von, bis) - pz(bereich[0], von, bis)}%"></i>` : ""}
      ${tipp ? `<span class="pz-tipp${pz(tipp.von, von, bis) > 60 ? " rechts" : ""}" style="left:${pz(tipp.von, von, bis)}%"><b>${esc(tipp.titel)}</b><span>${uhr(tipp.von)} · ${zeit(tipp.bis - tipp.von)} · Klick springt hin</span></span>` : ""}
    </div>`;
  }

  // Anzeige der Kanzel (wie radio-werbung.js)
  const anzeige = ({ art, led, titel, ton = "" }) => `<section class="rh-modul rh-m-anzeige" aria-label="Anzeige"><span class="ak-etikett">Anzeige</span>
      <div class="ak-glas rh-display"${ton ? ` data-ton="${ton}"` : ""}>
        <div class="rh-display-zeile"><ak-led farbe="${led[0]}" zustand="${led[1]}" groesse="klein"></ak-led><span>${art}</span><span class="rh-display-format">${R.guete(S.guete)}<span>${R.bitrate(S)}</span></span></div>
        <ak-segmente art="punkt" stellen="16" lauf="280" farbe="gruen" text="${esc(S.name.toUpperCase())}" hilfe="Sender"></ak-segmente>
        <div class="rh-display-titel">${esc(titel)}</div>
      </div></section>`;
  // Titelzeile unter dem Balken: der Titel an der Stelle, Vorheriger und Nächster Titel, Großansicht
  const titelzeile = (stelle) => {
    const a = bei(stelle);
    return `<div class="pz-titelzeile">
      <button class="knopf" type="button" title="An den Anfang dieses Titels, zweimal: vorheriger Titel"><i class="fa-solid fa-backward-step"></i>Titel</button>
      <span class="pz-jetzt"><b>${esc(a.titel)}</b><span class="rh-zahl">${zeit(stelle - a.von)} von ${zeit(a.bis - a.von)}${a.laufend ? " · läuft" : ""}</span></span>
      <button class="knopf" type="button" title="Zum Anfang des nächsten Titels"${a.laufend ? " disabled" : ""}>Titel<i class="fa-solid fa-forward-step"></i></button>
      <button class="knopf" type="button" title="Großansicht des Puffers: alle Titel, Aufnahme ab hier, Bereich sichern"><i class="fa-solid fa-list-ul"></i>Puffer</button></div>`;
  };
  const quelle = ({ text, farbe, uhrtext, stelle, aufnahme = null, tipp = null }) => `<section class="rh-modul rh-m-zeit pz-zeit" aria-label="Quelle und Zeit"><span class="ak-etikett">Quelle und Zeit</span>
      <div class="rh-zeit"><div class="ak-glas rh-zeit-glas">
        <ak-segmente art="14" stellen="7" farbe="${farbe}" text="${text}" hilfe="Quelle der Wiedergabe"></ak-segmente>
        <ak-segmente art="7" stellen="7" farbe="${aufnahme ? "rot" : "gruen"}" text="${uhrtext}" hilfe="${aufnahme ? "Länge der Aufnahme" : "Abstand zu live"}"></ak-segmente></div>
        <div class="rh-puffer-zeile">
          <button class="knopf" type="button" title="30 Sekunden zurück"><i class="fa-solid fa-rotate-left"></i>30 s</button>
          <div class="rh-puffer pz-puffer" title="Zeitversatz: Striche sind Titelgrenzen, violett ist Werbung">${balken({ stelle, aufnahme, tipp })}
            <span>${zeit(JETZT, true)} von 2:00:00 · ${A.length - 1} Titel</span></div>
          <button class="knopf" type="button" title="Zurück zu live"${stelle < JETZT ? "" : " disabled"}><i class="fa-solid fa-tower-broadcast"></i>Live</button></div>
        ${titelzeile(stelle)}</div></section>`;
  const band = (inhalt) => `<div class="rh-band rp-band pz-band" role="status">${inhalt}</div>`;

  // 1: Zeitversatz, 9:30 hinter live; der Zeiger steht auf der Marke von "Say My Name"
  function versatz(el) {
    const stelle = JETZT - 570;
    el.innerHTML = `<div class="rp-kanzel rw-kanzel">
      ${anzeige({ art: "9:30 HINTER LIVE", led: ["bernstein", "an"], titel: bei(stelle).titel })}
      ${quelle({ text: "VERSATZ", farbe: "bernstein", uhrtext: "-09:30", stelle, tipp: A.find((a) => a.titel.startsWith("Destiny")) })}
    </div>`;
  }

  // 2: live, Aufnahme gestartet: beginnt am Anfang von "United" (3:24 aus dem Puffer), rot bis live
  function aufnahme(el) {
    const u = A[A.length - 1];
    el.innerHTML = `<div class="rp-kanzel rw-kanzel">
      ${anzeige({ art: "LIVE · AUFNAHME", led: ["rot", "atmet"], titel: u.titel })}
      ${quelle({ text: "LIVE", farbe: "blau", uhrtext: "03:24", stelle: JETZT, aufnahme: u.von })}
      ${band(`<i class="fa-solid fa-circle pz-rot"></i><span><b>Aufnahme ab dem Anfang von "${esc(u.titel)}"</b>: 3:24 kamen aus dem Puffer. Sie läuft weiter, auch wenn du das Radio ausschaltest oder den Sender wechselst.</span>
        <button class="knopf" type="button" title="Großansicht: anderen Beginn wählen"><i class="fa-solid fa-list-ul"></i>Beginn ändern</button>
        <button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`)}
    </div>`;
  }

  // Großansicht: Kopf, Zeitleiste (Übersicht und Ausschnitt mit Zoom), Liste
  const ZOOM = [["alles", "Alles"], ["30", "30 min"], ["10", "10 min"]];
  function zeitleiste({ stelle, fenster, bereich = null, zoom = "30" }) {
    const [von, bis] = fenster;
    const sicht = A.filter((a) => a.bis > von && a.von < bis);
    const skala = []; for (let t = Math.ceil(von / 300) * 300; t <= bis; t += 300) skala.push(t);
    return `<div class="pz-leiste-gross">
      <div class="pz-leiste-kopf"><span class="ak-etikett">Zeitleiste</span>
        <div class="rh-segmente" role="group" aria-label="Zoom">${ZOOM.map(([w, n]) => `<button class="knopf${w === zoom ? " aktiv" : ""}" type="button" aria-pressed="${w === zoom}"><ak-led farbe="gelb" zustand="${w === zoom ? "an" : "aus"}" groesse="klein"></ak-led>${n}</button>`).join("")}</div>
        <span class="rh-still">Rad oder Ziehen verschiebt, Doppelklick springt hin</span></div>
      <div class="pz-uebersicht">${balken({ stelle, bereich, klasse: "pz-schmal" })}
        <i class="pz-fenster" style="left:${pz(von)}%;width:${pz(bis) - pz(von)}%" title="Ausschnitt"></i></div>
      <div class="pz-ausschnitt">
        ${sicht.map((a) => { const l = Math.max(0, pz(a.von, von, bis)), r = Math.min(100, pz(a.bis, von, bis));
          return `<div class="pz-block ${a.art}${a.nr % 2 ? "" : " zweit"}${bereich && a.von >= bereich[0] - 1 && a.bis <= bereich[1] + 1 ? " gewaehlt" : ""}" style="left:${l}%;width:${r - l}%" title="${esc(a.titel)}, ${zeit(a.bis - a.von)}">
            <b>${esc(a.titel)}</b><span class="rh-zahl">${uhr(a.von)} · ${zeit(a.bis - a.von)}</span></div>`; }).join("")}
        <i class="pz-kopf" style="left:${pz(stelle, von, bis)}%"></i>
        ${bis >= JETZT ? `<span class="pz-live" style="left:${pz(JETZT, von, bis)}%">live</span>` : ""}
      </div>
      <div class="pz-skala">${skala.filter((t) => pz(t, von, bis) > 4 && pz(t, von, bis) < 96).map((t) => `<span style="left:${pz(t, von, bis)}%">${uhr(t)}</span>`).join("")}</div>
    </div>`;
  }
  const zeile = (a, { stelle, bereich, offen }) => {
    const hoert = stelle >= a.von && stelle < a.bis, gewaehlt = bereich && a.von >= bereich[0] - 1 && a.bis <= bereich[1] + 1;
    return `<li class="pz-zeile ${a.art}${hoert ? " hoert" : ""}${gewaehlt ? " gewaehlt" : ""}${offen === a.nr ? " offen" : ""}">
      <span class="led"><ak-led farbe="${a.laufend ? "rot" : hoert ? "blau" : "gelb"}" zustand="${a.laufend ? "atmet" : hoert ? "an" : "aus"}" groesse="klein"></ak-led></span>
      <span class="rh-zahl pz-ab">${uhr(a.von)}</span>
      <span class="pz-name">${a.art === "werbung" ? `<i class="fa-solid fa-rectangle-ad"></i>` : ""}<b>${esc(a.titel)}</b>${a.laufend ? `<span class="pz-marke-live">läuft</span>` : ""}</span>
      <span class="rh-zahl pz-laenge">${zeit(a.bis - a.von)}</span>
      <span class="pz-aktionen">
        <button class="rund" type="button" title="Hier hören" aria-label="Hier hören"><i class="fa-solid fa-play"></i></button>
        <button class="rund pz-rec" type="button" title="Aufnahme ab dem Anfang dieses Titels, läuft bis Stopp" aria-label="Aufnahme ab hier"${a.art === "werbung" ? " disabled" : ""}><i class="fa-solid fa-circle"></i></button>
        <button class="rund pz-wahl" type="button" title="In den Bereich nehmen (Anfang und Ende wählen)" aria-label="Bereich" aria-pressed="${!!gewaehlt}"${a.art === "werbung" || a.laufend ? " disabled" : ""}><i class="${gewaehlt ? "fa-solid fa-square-check" : "fa-regular fa-square"}"></i></button>
      </span></li>`;
  };
  function grossansicht({ stelle, fenster, bereich = null, zoom = "30", liste = A, fuss = "" }) {
    const werbung = liste.filter((a) => a.art === "werbung").reduce((s, a) => s + a.bis - a.von, 0);
    return `<div class="pz-gross">
      <div class="pz-gross-kopf">${R.logo(S)}
        <div class="pz-gross-titel"><h2>Puffer: ${esc(S.name)}</h2><span class="rh-still">seit ${BEGINN.slice(0, 5)} · ${zeit(JETZT, true)} von 2:00:00 · ${liste.length - 1} Titel · Werbung ${zeit(werbung)}</span></div>
        <div class="pz-gross-knoepfe">
          <button class="knopf" type="button" title="Vorheriger Titel"><i class="fa-solid fa-backward-step"></i>Titel</button>
          <button class="knopf" type="button" title="Nächster Titel">Titel<i class="fa-solid fa-forward-step"></i></button>
          <button class="knopf" type="button" title="Zurück zu live"><i class="fa-solid fa-tower-broadcast"></i>Live</button>
          <button class="rund" type="button" aria-label="Schließen" title="Zurück zum Radio"><i class="fa-solid fa-xmark"></i></button></div></div>
      ${zeitleiste({ stelle, fenster, bereich, zoom })}
      <div class="pz-liste-kopf"><span></span><span>ab</span><span>Titel</span><span>Länge</span><span></span></div>
      <ol class="pz-liste">${[...liste].reverse().map((a) => zeile(a, { stelle, bereich })).join("")}</ol>
      ${fuss}
    </div>`;
  }

  // 3: Großansicht, 30-Minuten-Ausschnitt um die Stelle, die man hört
  function gross(el) {
    const stelle = JETZT - 570;
    el.innerHTML = `<div class="rp-rechner">${grossansicht({ stelle, fenster: [JETZT - 1800, JETZT] })}</div>`;
  }

  // 4: Bereich gewählt: Seal bis Jein, unten der Fuß zum Sichern
  function bereich(el) {
    const von = A.find((a) => a.titel.startsWith("Seal")), bis = A.find((a) => a.titel.startsWith("Fettes"));
    const b = [von.von, bis.bis];
    el.innerHTML = `<div class="rp-rechner">${grossansicht({ stelle: JETZT, fenster: [b[0] - 300, b[1] + 600], bereich: b, zoom: "30",
      fuss: `<div class="pz-fuss"><i class="fa-solid fa-square-check"></i><span><b>Bereich: 3 Titel</b>, ${uhr(b[0])} bis ${uhr(b[1])}, ${zeit(b[1] - b[0])} lang. Wird fertig geschnitten wie jede Aufnahme (Grenzen an den Pausen).</span>
        <button class="knopf primaer pz-sichern" type="button"><i class="fa-solid fa-circle"></i>Als Aufnahme sichern</button>
        <button class="knopf" type="button">Abbrechen</button></div>` })}</div>`;
  }

  // 5: gerade verbunden: Werbung beim Verbinden, erster Titel läuft
  function jung(el) {
    const jetzt = 48, liste = abschnitte(jetzt);
    el.innerHTML = `<div class="rp-rechner"><div class="pz-gross">
      <div class="pz-gross-kopf">${R.logo(S)}<div class="pz-gross-titel"><h2>Puffer: ${esc(S.name)}</h2><span class="rh-still">seit ${BEGINN.slice(0, 5)} · 0:48 von 2:00:00 · 1 Titel · Werbung 0:09</span></div>
        <div class="pz-gross-knoepfe"><button class="knopf" type="button" disabled><i class="fa-solid fa-tower-broadcast"></i>Live</button><button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button></div></div>
      <div class="pz-leiste-gross"><div class="pz-ausschnitt">${liste.map((a) => `<div class="pz-block ${a.art}" style="left:${(a.von / jetzt) * 100}%;width:${((a.bis - a.von) / jetzt) * 100}%"><b>${esc(a.titel)}</b><span class="rh-zahl">${zeit(a.bis - a.von)}</span></div>`).join("")}
        <i class="pz-kopf" style="left:100%"></i><span class="pz-live" style="left:100%">live</span></div></div>
      <p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>Der Puffer beginnt mit dem Verbinden; was davor lief, gibt es nicht. Die Werbung beim Verbinden hat RadioHub nicht gespielt. Titel kommen dazu, sobald der Sender sie meldet; die Grenze sitzt an der Pause davor.</span></p>
      <ol class="pz-liste">${[...liste].reverse().map((a) => zeile(a, { stelle: jetzt })).join("")}</ol></div></div>`;
  }

  // 6 bis 8: Telefon
  const status = `<div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div><div class="t-luft"></div>`;
  function tSpieler(el) {
    const stelle = JETZT - 570, a = bei(stelle);
    el.innerHTML = `<div class="t-gross pz-t-gross">${status}
      <div class="t-gross-kopf"><button class="rund" type="button" aria-label="Spieler verkleinern"><i class="fa-solid fa-chevron-down"></i></button><span class="ak-etikett">Radio</span><span></span></div>
      <div class="t-gross-rollt">
        <div class="ak-glas rh-display"><div class="rh-display-zeile"><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led><span>9:30 HINTER LIVE</span><span class="rh-display-format">${R.guete(S.guete)}<span>${R.bitrate(S)}</span></span></div>
          <ak-segmente art="punkt" stellen="14" lauf="300" farbe="gruen" text="${esc(S.name.toUpperCase())}"></ak-segmente><div class="rh-display-titel">${esc(a.titel)}</div></div>
        <div class="t-transport">
          <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="Vorheriger Sender"></ak-taster>
          <ak-taster art="glas" symbol="fa-stop" farbe="weiss" led="weiss" modus="tasten" hilfe="Stopp"></ak-taster>
          <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="Hören oder anhalten" an></ak-taster>
          <ak-taster art="glas" symbol="fa-circle" farbe="rot" led="rot" hilfe="Aufnahme ab dem Anfang des laufenden Titels"></ak-taster>
          <ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="Nächster Sender"></ak-taster></div>
        <div class="pz-t-versatz"><span class="ak-etikett">Zeitversatz</span>
          ${balken({ stelle, klasse: "pz-dick" })}
          <div class="pz-t-zahlen rh-zahl"><span>-9:30</span><span>${zeit(JETZT, true)} von 2:00:00</span><span>live</span></div>
          <div class="pz-t-titel"><b>${esc(a.titel)}</b><span class="rh-zahl">${zeit(stelle - a.von)} von ${zeit(a.bis - a.von)}</span></div>
          <div class="pz-t-knoepfe">
            <button class="knopf" type="button" aria-label="Vorheriger Titel"><i class="fa-solid fa-backward-step"></i>Titel</button>
            <button class="knopf" type="button" aria-label="Nächster Titel">Titel<i class="fa-solid fa-forward-step"></i></button>
            <button class="knopf" type="button" aria-label="Zurück zu live"><i class="fa-solid fa-tower-broadcast"></i>Live</button>
            <button class="knopf primaer" type="button"><i class="fa-solid fa-list-ul"></i>Puffer</button></div></div>
      </div></div>`;
  }
  const tZeile = (a, { stelle, bereich = null, offen = null }) => {
    const hoert = stelle >= a.von && stelle < a.bis, gewaehlt = bereich && a.von >= bereich[0] - 1 && a.bis <= bereich[1] + 1;
    return `<li class="pz-t-zeile ${a.art}${hoert ? " hoert" : ""}${gewaehlt ? " gewaehlt" : ""}${offen === a.nr ? " offen" : ""}">
      <div class="pz-t-kern">${bereich ? `<i class="${gewaehlt ? "fa-solid fa-square-check" : "fa-regular fa-square"} pz-t-wahl"></i>` : `<ak-led farbe="${a.laufend ? "rot" : hoert ? "blau" : "gelb"}" zustand="${a.laufend ? "atmet" : hoert ? "an" : "aus"}" groesse="klein"></ak-led>`}
        <div><b>${a.art === "werbung" ? `<i class="fa-solid fa-rectangle-ad"></i>` : ""}${esc(a.titel)}</b><div class="t-meta"><span class="rh-zahl">${uhr(a.von)}</span><span class="rh-zahl">${zeit(a.bis - a.von)}</span>${a.laufend ? `<span class="pz-marke-live">läuft</span>` : ""}</div></div></div>
      ${offen === a.nr ? `<div class="pz-t-tat"><button class="knopf" type="button"><i class="fa-solid fa-play"></i>Hören</button><button class="knopf pz-rec-knopf" type="button" title="Aufnahme ab dem Anfang dieses Titels, läuft bis Stopp"><i class="fa-solid fa-circle"></i>Aufnehmen</button><button class="knopf" type="button"><i class="fa-solid fa-square-check"></i>Bereich</button></div>` : ""}</li>`;
  };
  function tPuffer(el, { bereich = null, offen = null } = {}) {
    const stelle = JETZT - 570;
    el.innerHTML = `<div class="t-gross pz-t-gross">${status}
      <div class="t-gross-kopf"><button class="rund" type="button" aria-label="Zurück zum Spieler"><i class="fa-solid fa-chevron-left"></i></button><span class="ak-etikett">Puffer · ${zeit(JETZT, true)}</span><span></span></div>
      <div class="pz-t-oben">${balken({ stelle, bereich, klasse: "pz-dick" })}<div class="pz-t-zahlen rh-zahl"><span>${BEGINN.slice(0, 5)}</span><span>${A.length - 1} Titel</span><span>live</span></div></div>
      <ol class="pz-t-liste">${[...A].reverse().map((a) => tZeile(a, { stelle, bereich, offen })).join("")}</ol>
      ${bereich ? `<div class="pz-t-fuss"><span><b>3 Titel</b>, ${zeit(bereich[1] - bereich[0])}</span><button class="knopf" type="button">Abbrechen</button><button class="knopf primaer pz-sichern" type="button"><i class="fa-solid fa-circle"></i>Sichern</button></div>` : ""}
    </div>`;
  }
  const tListe = (el) => tPuffer(el, { offen: A.find((a) => a.titel.startsWith("Ace")).nr });
  const tBereich = (el) => { const v = A.find((a) => a.titel.startsWith("Seal")), b = A.find((a) => a.titel.startsWith("Fettes")); tPuffer(el, { bereich: [v.von, b.bis] }); };

  // 9 und 10 (RAD-60): die ganze Kanzel ohne Titelzeile. Der Titel steht in der Matrixanzeige; Vor und Zurück der
  // Steuerung springen im Zeitversatz kurz gedrückt durch die Titel, lang gedrückt wechseln sie den Sender; Puffer links,
  // Live rechts neben der Segmentanzeige, die so breit ist wie ihre Segmente.
  const laut = `<section class="rh-modul rh-m-laut"><div class="ak-geraet rh-laut" data-bauform="inspektor">
      <span class="ak-schraube lo" style="--dreh:12deg"></span><span class="ak-schraube ro" style="--dreh:58deg"></span><span class="ak-etikett">Lautstärke</span>
      <div class="rh-laut-reihe"><span class="rh-vu"><ak-pegel richtung="senkrecht" kanaele="1" segmente="12" skala="" beschriftung="Pegel links"></ak-pegel>L</span>
        <ak-dreh name="Lautstärke" wert="70" vorgabe="50" einheit="%"></ak-dreh>
        <span class="rh-vu"><ak-pegel richtung="senkrecht" kanaele="1" segmente="12" skala="" beschriftung="Pegel rechts"></ak-pegel>R</span></div></div></section>`;
  const steuerung = ({ titel, aufnahme: rec = false, tipp = "" }) => `<section class="rh-modul rh-m-steuerung pz60-steuerung" aria-label="Steuerung"><span class="ak-etikett">Steuerung</span>
      <div class="rh-steuerung"><div class="rh-transport">
        <ak-taster art="glas" symbol="fa-backward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="${titel ? "Kurz: Anfang dieses Titels, gleich danach vorheriger Titel · lang: vorheriger Sender" : "Vorheriger Sender"}"></ak-taster>
        <ak-taster art="glas" symbol="fa-stop" farbe="weiss" led="weiss" modus="tasten" hilfe="Stopp"></ak-taster>
        <ak-taster art="glas" symbol="fa-play" farbe="gruen" led="gruen" hilfe="Hören oder anhalten" an></ak-taster>
        <ak-taster art="glas" symbol="fa-circle" farbe="rot" led="rot" hilfe="Aufnahme ab dem Anfang des laufenden Titels"${rec ? " an" : ""}></ak-taster>
        <span class="pz60-vor"><ak-taster art="glas" symbol="fa-forward-step" farbe="weiss" led="bernstein" modus="tasten" hilfe="${titel ? "Kurz: nächster Titel · lang: nächster Sender" : "Nächster Sender"}"></ak-taster>
          ${tipp ? `<span class="pz-tipp rechts pz60-tipp"><b>${esc(tipp)}</b><span>lang drücken: nächster Sender</span></span>` : ""}</span></div>
        <div class="rh-betrieb"><div class="rh-betrieb-tasten">
          <ak-taster art="glas" symbol="fa-location-crosshairs" farbe="weiss" led="blau" hilfe="Fokus: die Liste folgt dem laufenden Sender" an></ak-taster>
          <ak-taster art="glas" symbol="fa-wave-square" farbe="weiss" led="weiss" hilfe="Bitrate"></ak-taster></div></div></div></section>`;
  const quelle60 = ({ text, farbe, uhrtext, stelle, aufnahme: rec = null }) => {
    const zeile = `${zeit(JETZT, true)} von 2:00:00 · ${A.length - 1} Titel`;
    return `<section class="rh-modul rh-m-zeit pz60-zeit" aria-label="Quelle und Zeit"><span class="ak-etikett">Quelle und Zeit</span>
      <div class="pz60-raster">
        <button class="knopf pz60-spalte" type="button" title="Großansicht des Puffers: alle Titel, Aufnahme ab hier, Bereich sichern"><i class="fa-solid fa-list-ul"></i>Puffer</button>
        <div class="ak-glas rh-zeit-glas pz60-glas">
          <ak-segmente art="14" stellen="7" farbe="${farbe}" text="${text}" hilfe="Quelle der Wiedergabe"></ak-segmente>
          <ak-segmente art="7" stellen="7" farbe="${rec ? "rot" : "gruen"}" text="${uhrtext}" hilfe="${rec ? "Länge der Aufnahme" : "Abstand zu live"}"></ak-segmente></div>
        <button class="knopf pz60-spalte" type="button" title="Zurück zu live"${stelle < JETZT ? "" : " disabled"}><i class="fa-solid fa-tower-broadcast"></i>Live</button>
        <button class="knopf" type="button" title="30 Sekunden zurück"><i class="fa-solid fa-rotate-left"></i>30</button>
        <div class="rh-puffer pz-puffer" title="Zeitversatz: Striche sind Titelgrenzen, violett ist Werbung">${balken({ stelle, aufnahme: rec })}<span>${zeile}</span></div>
        <button class="knopf" type="button" title="30 Sekunden vor"${stelle < JETZT ? "" : " disabled"}><i class="fa-solid fa-rotate-right"></i>30</button>
      </div></section>`;
  };
  function ohneTitelzeile(el) {
    const stelle = JETZT - 570, a = bei(stelle);
    el.innerHTML = `<div class="pz60-kanzel">
      ${anzeige({ art: "9:30 HINTER LIVE", led: ["bernstein", "an"], titel: a.titel })}
      ${quelle60({ text: "VERSATZ", farbe: "bernstein", uhrtext: "-09:30", stelle })}
      ${laut}${steuerung({ titel: true, tipp: "Nächster Titel: Destiny's Child - Say My Name" })}</div>`;
  }
  function ohneTitelzeileAufnahme(el) {
    const u = A[A.length - 1];
    el.innerHTML = `<div class="pz60-kanzel">
      ${anzeige({ art: "LIVE · AUFNAHME", led: ["rot", "atmet"], titel: u.titel })}
      ${quelle60({ text: "LIVE", farbe: "blau", uhrtext: "03:24", stelle: JETZT, aufnahme: u.von })}
      ${laut}${steuerung({ titel: false, aufnahme: true })}</div>`;
  }

  const ZUSTAENDE = { versatz, aufnahme, gross, bereich, jung, "t-spieler": tSpieler, "t-liste": tListe, "t-bereich": tBereich,
    "ohne-titelzeile": ohneTitelzeile, "ohne-titelzeile-aufnahme": ohneTitelzeileAufnahme };
  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-zustand]").forEach((el) => { ZUSTAENDE[el.dataset.zustand](el); R.tastenlicht?.(el); });
    // Listen zeigen die gewählten Titel oder den angetippten (wie die App beim Öffnen: die Stelle, um die es geht)
    document.querySelectorAll(".pz-liste, .pz-t-liste").forEach((liste) => {
      const ziel = liste.querySelector(".gewaehlt, .offen");
      if (ziel) liste.scrollTop = ziel.offsetTop - liste.offsetTop - 60;
    });
  });
})();
