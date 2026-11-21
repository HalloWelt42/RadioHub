// Verhalten des Entwurfs Aufnahmen und Schnitt am Rechner (RAD-17). Wie Radio und Podcasts: Seitenleiste mit Quelle
// (eigene Aufnahmen oder die ganze Kellerwolke) und Ordnern, Werkzeugleiste mit Zähler und Suche, Liste mit Kopf der
// gewählten Aufnahme. Der Schnitt ist ein Arbeitsplatz über die ganze Breite für eine Aufnahme, einen Titel oder eine
// Datei der Kellerwolke: Wellenform, Übersicht, Marker, Stücke zum Behalten oder Verwerfen, Normalisieren, Umwandeln,
// Schritte mit Rückgängig (Versionen der Kellerwolke). Löschen fragt immer mit Folgen. Nur Entwurf, Musterdaten.
(() => {
  "use strict";
  const A = window.RHAufnahmen, R = window.RH, $ = (s, w = document) => w.querySelector(s), $$ = (s, w = document) => [...w.querySelectorAll(s)];
  const esc = R.esc;
  const z = {
    quelle: "aufnahmen", ordner: "", suche: "", sort: ["datum", true], gewaehlt: null, laeuft: false, frage: null, spielt: "s1",
    pfad: "Interviews", schnitt: null, ordnerListe: A.ORDNER.map((o) => ({ ...o })), sitzungen: A.SITZUNGEN.map((s) => ({ ...s, titel: s.titel.map((t) => ({ ...t })) })),
  };

  const zeit = (s) => { s = Math.round(s); const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), x = s % 60; return h ? `${h}:${String(m).padStart(2, "0")}:${String(x).padStart(2, "0")}` : `${m}:${String(x).padStart(2, "0")}`; };
  const dauer = (s) => (s >= 3600 ? `${Math.floor(s / 3600)} h ${Math.round((s % 3600) / 60)} min` : `${Math.max(1, Math.round(s / 60))} min`);
  const datum = (d) => d.toLocaleDateString("de-DE", { day: "numeric", month: "short" }) + ", " + d.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" });
  const mb = (x) => `${String(x).replace(".", ",")} MB`;
  const sitzung = (id) => z.sitzungen.find((s) => s.id === id);
  const ordnerName = (id) => z.ordnerListe.find((o) => o.id === id)?.name ?? "Ohne Ordner";
  const ziel = () => z.ordnerListe.find((o) => o.ziel);
  const rueckfrage = (frage, knopf, art, id, symbol = "fa-trash") => `<div class="rueckfrage" role="alertdialog" aria-label="${esc(knopf)}?"><span class="frage">${frage}</span><span class="aktionen">
    <button class="knopf" type="button" data-aktion="abbrechen">Abbrechen</button><button class="knopf gefahr" type="button" data-aktion="ja" data-art="${art}" data-id="${id}"><i class="fa-solid ${symbol}"></i>${esc(knopf)}</button></span></div>`;
  const gefragt = (art, id) => z.frage && z.frage[0] === art && String(z.frage[1]) === String(id);

  // ─── Seitenleiste ───
  function leiste() {
    $$("#quelle [data-quelle]").forEach((b) => { const an = b.dataset.quelle === z.quelle; b.classList.toggle("aktiv", an); b.setAttribute("aria-pressed", String(an)); });
    if (z.quelle === "wolke") { wolkenleiste(); return; }
    const zahl = (id) => z.sitzungen.filter((s) => (id === null ? !s.ordner : s.ordner === id)).length;
    const zeile = (id, name, symbol, n, o) => `<div class="rh-facette rh-aordner${z.ordner === id ? " an" : ""}" role="button" tabindex="0" data-ordner="${id}">
      ${o ? `<ak-led farbe="rot" zustand="${o.ziel ? "an" : "aus"}" groesse="klein" hilfe="${o.ziel ? "neue Aufnahmen landen hier" : "kein Aufnahmeziel"}"></ak-led>` : `<span></span>`}
      <i class="fa-solid ${symbol} rh-ordner-symbol"></i><span class="rh-abo-name">${esc(name)}</span>
      <span class="rh-abo-ende"><span class="rh-zahl">${n}</span>
      ${o ? `<button class="rh-nadel${o.ziel ? " an" : ""}" type="button" data-aktion="ziel" data-id="${o.id}" title="${o.ziel ? "Ist das Aufnahmeziel" : "Neue Aufnahmen hierhin"}" aria-label="Aufnahmeziel: ${esc(name)}"><i class="fa-solid fa-circle-dot"></i></button>
        <button class="rh-nadel" type="button" title="Umbenennen" aria-label="${esc(name)} umbenennen"><i class="fa-solid fa-pen"></i></button>
        <button class="rh-nadel" type="button" data-aktion="fragen" data-art="ordner" data-id="${o.id}" title="Ordner löschen" aria-label="${esc(name)} löschen"><i class="fa-solid fa-trash-can"></i></button>` : ""}</span></div>
      ${o && gefragt("ordner", o.id) ? (n ? `<p class="hinweis-band rh-leiste-hinweis"><i class="fa-solid fa-lock"></i><span>"${esc(name)}" enthält ${n} Aufnahmen und lässt sich erst löschen, wenn er leer ist.</span><button class="knopf" type="button" data-aktion="abbrechen">Verstanden</button></p>`
        : rueckfrage(`Ordner "${esc(name)}" löschen? Er ist leer.`, "Löschen", "ordner", o.id)) : ""}`;
    $("#leiste").innerHTML = `<section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>Ordner</h3><button type="button" title="Neuen Ordner anlegen">Ordner anlegen</button></div>
      <div class="rh-facetten rh-abos">
        <button class="rh-facette rh-alle-abos${z.ordner === "" ? " an" : ""}" type="button" data-ordner=""><ak-led farbe="gelb" zustand="${z.ordner === "" ? "an" : "aus"}" groesse="klein"></ak-led>
          <span class="rh-abo-name">Alle Aufnahmen</span><span class="rh-zahl">${z.sitzungen.length}</span></button>
        ${z.ordnerListe.map((o) => zeile(o.id, o.name, "fa-folder", zahl(o.id), o)).join("")}
        ${zeile("ohne", "Ohne Ordner", "fa-house", zahl(null), null)}
      </div>
      <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-circle-dot"></i>Rotes Licht: dort landen neue Aufnahmen. Aufnahmen per Ziehen in einen Ordner.</p>
    </section>`;
    $("#leiste-fuss").innerHTML = `<span><b>${R.zahl(A.DATEIEN)}</b> Dateien</span><span><b>${String(z.sitzungen.reduce((s, x) => s + x.mb, 0).toFixed(0))}</b> MB</span><span><b>${A.FREI_GB}</b> GB frei</span>`;
  }
  function wolkenleiste() {
    const teile = z.pfad ? z.pfad.split("/") : [];
    const ort = A.WOLKE[z.pfad] ?? { ordner: [], dateien: [] };
    $("#leiste").innerHTML = `<section class="rh-gruppe">
      <div class="rh-gruppe-kopf"><h3>Kellerwolke</h3></div>
      <nav class="rh-wolke-pfad" aria-label="Pfad"><button type="button" data-pfad=""><i class="fa-solid fa-cloud"></i>Wurzel</button>
        ${teile.map((t, i) => `<i class="fa-solid fa-chevron-right"></i><button type="button" data-pfad="${esc(teile.slice(0, i + 1).join("/"))}"${i === teile.length - 1 ? ' aria-current="page"' : ""}>${esc(t)}</button>`).join("")}</nav>
      <div class="rh-facetten rh-abos">
        ${z.pfad ? `<div class="rh-facette rh-aordner" role="button" tabindex="0" data-pfad="${esc(teile.slice(0, -1).join("/"))}"><span></span><i class="fa-solid fa-turn-up rh-ordner-symbol"></i><span class="rh-abo-name">Eine Ebene höher</span><span></span></div>` : ""}
        ${ort.ordner.map((o) => { const p = z.pfad ? `${z.pfad}/${o}` : o; const n = A.WOLKE[p]?.dateien.length; return `<div class="rh-facette rh-aordner" role="button" tabindex="0" data-pfad="${esc(p)}">
          <span></span><i class="fa-solid fa-folder rh-ordner-symbol"></i><span class="rh-abo-name">${esc(o)}</span><span class="rh-zahl">${n ?? ""}</span></div>`; }).join("")}
      </div>
      <p class="rh-still rh-abos-hinweis"><i class="fa-solid fa-circle-info"></i>Gezeigt werden nur Audiodateien. Schnitt legt das Ergebnis als neue Datei daneben, das Original bleibt.</p>
    </section>`;
    $("#leiste-fuss").innerHTML = `<span><i class="fa-solid fa-lock-open"></i> RadioHub darf alle Ordner lesen</span>`;
  }
  $("#quelle").addEventListener("click", (e) => { const b = e.target.closest("[data-quelle]"); if (!b) return; z.quelle = b.dataset.quelle; z.gewaehlt = null; z.schnitt = null; neu(); });
  $("#leiste").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]");
    if (k) {
      e.stopPropagation();
      if (k.dataset.aktion === "ziel") { z.ordnerListe.forEach((o) => (o.ziel = o.id === k.dataset.id)); band(`<i class="fa-solid fa-circle-dot"></i><span>Neue Aufnahmen landen jetzt in <b>${esc(ordnerName(k.dataset.id))}</b></span>`); }
      if (k.dataset.aktion === "fragen") z.frage = ["ordner", k.dataset.id];
      if (k.dataset.aktion === "abbrechen") z.frage = null;
      if (k.dataset.aktion === "ja") { z.ordnerListe = z.ordnerListe.filter((o) => o.id !== k.dataset.id); z.frage = null; }
      neu(); return;
    }
    const o = e.target.closest("[data-ordner]"); if (o) { z.ordner = o.dataset.ordner; z.gewaehlt = null; neu(); return; }
    const p = e.target.closest("[data-pfad]"); if (p) { z.pfad = p.dataset.pfad; neu(); }
  });

  // ─── Werkzeugleiste ───
  function passend() {
    const q = z.suche.trim().toLowerCase();
    return z.sitzungen.filter((s) => (z.ordner === "" || (z.ordner === "ohne" ? !s.ordner : s.ordner === z.ordner))
      && (!q || `${s.sender} ${s.titel.map((t) => t.titel).join(" ")}`.toLowerCase().includes(q)));
  }
  function werkzeug() {
    const wolke = z.quelle === "wolke";
    const anzahl = wolke ? (A.WOLKE[z.pfad]?.dateien.length ?? 0) : passend().length;
    $("#zaehler").setAttribute("text", String(anzahl));
    $("#zaehler-art").textContent = wolke ? "Dateien" : "Aufnahmen";
    $("#zaehler-zusatz").textContent = wolke ? z.pfad || "Wurzel" : dauer(passend().reduce((s, x) => s + x.dauer, 0));
    $("#suche").placeholder = wolke ? "Dateien in der Kellerwolke suchen" : "Sender oder Titel suchen";
    const c = [];
    if (!wolke && z.ordner) c.push(["ordner", "Ordner", z.ordner === "ohne" ? "ohne Ordner" : ordnerName(z.ordner)]);
    if (z.gewaehlt) c.push(["aufnahme", "Aufnahme", `${sitzung(z.gewaehlt).sender}, ${datum(sitzung(z.gewaehlt).datum)}`]);
    if (z.suche) c.push(["suche", "Suche", z.suche]);
    $("#aktiv-chips").innerHTML = c.map(([art, name, wert]) => `<span class="chip">${name}: <b>${esc(wert)}</b><button type="button" data-art="${art}" aria-label="Filter entfernen" title="Entfernen"><i class="fa-solid fa-xmark"></i></button></span>`).join("")
      || `<span class="rh-leer-chips">${wolke ? "Alle Audiodateien dieses Ordners" : "Alle Aufnahmen"}</span>`;
    const zz = ziel();
    $("#ziel-hinweis").innerHTML = wolke ? `<i class="fa-solid fa-scissors"></i><span>Schneiden legt <b>eine neue Datei daneben</b>, das Original bleibt</span>`
      : `<ak-led farbe="rot" zustand="${z.laeuft ? "blinkt" : "an"}" groesse="klein"></ak-led><span>Neue Aufnahmen landen in <b>${esc(zz ? zz.name : "Ohne Ordner")}</b></span>`;
  }
  $("#aktiv-chips").addEventListener("click", (e) => {
    const k = e.target.closest("button[data-art]"); if (!k) return;
    ({ ordner: () => (z.ordner = ""), aufnahme: () => (z.gewaehlt = null), suche: () => (z.suche = $("#suche").value = "") })[k.dataset.art](); neu();
  });
  $("#suche").addEventListener("input", (e) => { z.suche = e.target.value; neu(); });
  $("#suche-leeren").addEventListener("click", () => { z.suche = $("#suche").value = ""; neu(); });

  // ─── Kopf: laufende Aufnahme oder gewählte Aufnahme ───
  function kopf() {
    const el = $("#kopf");
    if (z.schnitt || z.quelle === "wolke") { el.innerHTML = ""; return; }
    if (z.laeuft && !z.gewaehlt) {
      const L = A.LAEUFT;
      el.innerHTML = `<section class="rh-abo-kopf rh-a-kopf rh-a-laeuft">
        <span class="rh-logo-bild gross" style="--lack:${R.lack(L.sender)}" aria-hidden="true">${esc(R.kuerzel(L.sender))}</span>
        <div class="rh-abo-text"><h2><ak-led farbe="rot" zustand="blinkt" groesse="klein"></ak-led>Aufnahme läuft: ${esc(L.sender)}</h2>
          <p class="rh-still">seit ${L.start} · aus dem Puffer mit ${L.rueckblick} min Rückblick · ${L.codec} ${L.kbit} kbit/s · nach ${esc(ziel()?.name ?? "Ohne Ordner")}</p>
          <ol class="rh-live-titel">${L.titel.map(([t, x, gesperrt]) => `<li class="${gesperrt ? "gesperrt" : ""}"><span class="rh-zahl">${t}</span>${esc(x)}${gesperrt ? `<span class="rh-geltung fest" title="Muster der Sperrliste: teilt die Aufnahme nicht">gesperrt</span>` : ""}</li>`).join("")}</ol></div>
        <div class="ak-geraet rh-a-uhr" data-bauform="inspektor"><span class="ak-schraube lo" style="--dreh:20deg"></span><span class="ak-schraube ro" style="--dreh:-30deg"></span>
          <ak-segmente art="7" stellen="7" farbe="rot" text="${zeit(L.sekunden).padStart(7, "0")}"></ak-segmente><span class="ak-etikett">Aufnahme</span></div>
        <div class="rh-detail-knoepfe rh-abo-knoepfe">
          <button class="knopf gefahr" type="button" data-aktion="stopp"><i class="fa-solid fa-stop"></i>Aufnahme beenden</button>
          <span class="rh-still"><i class="fa-solid fa-lock"></i> Senderwechsel, Pause und Spulen sind gesperrt, solange aufgenommen wird.</span>
        </div></section>`;
      return;
    }
    if (!z.gewaehlt) { el.innerHTML = ""; return; }
    const s = sitzung(z.gewaehlt), geteilt = s.titel.length > 1;
    el.innerHTML = `<section class="rh-abo-kopf rh-a-kopf">
      <span class="rh-logo-bild gross" style="--lack:${R.lack(s.sender)}" aria-hidden="true">${esc(R.kuerzel(s.sender))}</span>
      <div class="rh-abo-text"><h2>${esc(s.sender)}</h2><p class="rh-still">${datum(s.datum)} · ${s.art === "puffer" ? "aus dem Puffer" : "direkt"} · ${esc(ordnerName(s.ordner))}</p>
        <div class="rh-abo-zahlen"><span><b>${s.titel.length}</b> ${s.titel.length === 1 ? "Titel" : "Titel"}</span><span><b>${dauer(s.dauer)}</b> lang</span><span><b>${mb(s.mb)}</b></span><span><b>${s.codec} ${s.kbit}</b> kbit/s</span>
          <span class="rh-a-guete ${s.abgebrochen ? "rot" : s.luecken ? "gelb" : "gruen"}"><ak-led farbe="${s.abgebrochen ? "rot" : s.luecken ? "gelb" : "gruen"}" zustand="an" groesse="klein"></ak-led>${s.abgebrochen ? "abgebrochen" : s.luecken ? `${s.luecken} Lücken` : "ohne Lücken"}</span></div></div>
      <div class="rh-detail-knoepfe rh-abo-knoepfe">
        <button class="knopf primaer" type="button" data-aktion="hoeren"><i class="fa-solid fa-play"></i>Hören</button>
        <button class="knopf" type="button" data-aktion="schneiden"><i class="fa-solid fa-scissors"></i>Schneiden</button>
        ${!geteilt && s.titelwechsel ? `<button class="knopf" type="button" data-aktion="teilen" title="An den beim Aufnehmen erkannten Titelwechseln teilen"><i class="fa-solid fa-wand-magic-sparkles"></i>Nach Titeln teilen (${s.titelwechsel})</button>` : ""}
        <button class="knopf" type="button" title="Alle Titel als ZIP mit Titelliste"><i class="fa-solid fa-file-zipper"></i>Titel laden</button>
        <button class="knopf" type="button" title="Die ganze Aufnahme als eine Datei"><i class="fa-solid fa-download"></i>Als eine Datei</button>
        <span class="auswahl"><button class="auswahl-knopf" type="button" title="In einen Ordner verschieben"><i class="fa-solid fa-folder-tree"></i><span class="auswahl-text">${esc(ordnerName(s.ordner))}</span><i class="fa-solid fa-chevron-down auswahl-pfeil"></i></button></span>
        <button class="knopf gefahr" type="button" data-aktion="fragen" data-art="sitzung" data-id="${s.id}"><i class="fa-solid fa-trash-can"></i>Löschen</button>
      </div>
      ${gefragt("sitzung", s.id) ? rueckfrage(`Aufnahme "${esc(s.sender)}, ${datum(s.datum)}" löschen? ${s.titel.length} Titel, ${mb(s.mb)}, gehen in den Papierkorb der Kellerwolke (Ordner Aufnahmen/${esc(s.sender)}).`, "Löschen", "sitzung", s.id) : ""}
    </section>`;
  }

  // ─── Liste ───
  const sortspalte = (feld, titel, abwaerts) => {
    const aktiv = z.sort[0] === feld;
    return `<button class="rh-sortspalte${aktiv ? " aktiv" : ""}" type="button" data-sort="${feld}" aria-pressed="${aktiv}">${titel}<i class="fa-solid ${(aktiv ? z.sort[1] : abwaerts) ? "fa-arrow-down-long" : "fa-arrow-up-long"}"></i></button>`;
  };
  function zeilen() {
    const el = $("#zeilen");
    if (z.schnitt) { el.innerHTML = schnitt(); wellenform(); return; }
    if (z.quelle === "wolke") { el.innerHTML = wolkenliste(); return; }
    if (z.gewaehlt) { el.innerHTML = titelliste(sitzung(z.gewaehlt)); return; }
    const SORT = { datum: (a, b) => a.datum - b.datum, sender: (a, b) => a.sender.localeCompare(b.sender, "de"), dauer: (a, b) => a.dauer - b.dauer, mb: (a, b) => a.mb - b.mb };
    const liste = passend().sort((a, b) => SORT[z.sort[0]](a, b) * (z.sort[1] ? -1 : 1));
    el.innerHTML = `<div class="rh-spalten rh-a-spalten" role="group" aria-label="Sortierung">
        <span>${sortspalte("sender", "Aufnahme", false)}${sortspalte("datum", "Datum", true)}</span><span class="rh-ohne-sort">Titel</span>
        <span class="rechts">${sortspalte("dauer", "Länge", true)}</span><span class="rechts">${sortspalte("mb", "Größe", true)}</span><span class="rh-ohne-sort"></span></div>
      ${z.laeuft ? `<article class="rh-sender rh-aufnahme laeuft"><div class="rh-sender-kern" data-aktion="live">
        <span class="led"><ak-led farbe="rot" zustand="blinkt" groesse="klein" hilfe="nimmt auf"></ak-led></span>
        <span class="rh-logo-bild" style="--lack:${R.lack(A.LAEUFT.sender)}">${esc(R.kuerzel(A.LAEUFT.sender))}</span>
        <div class="name"><b>${esc(A.LAEUFT.sender)}</b><div class="meta"><span>läuft seit ${A.LAEUFT.start}</span><span>${esc(ziel()?.name ?? "Ohne Ordner")}</span></div></div>
        <div class="rh-a-titelzahl">${A.LAEUFT.titel.length}</div><div class="laenge">${zeit(A.LAEUFT.sekunden)}</div><div class="laenge">-</div>
        <div class="rh-aktionen rh-a-aktionen"><button class="rund" type="button" data-aktion="stopp" title="Aufnahme beenden" aria-label="Aufnahme beenden"><i class="fa-solid fa-stop"></i></button></div></div></article>` : ""}
      ${liste.map((s) => `<article class="rh-sender rh-aufnahme${z.spielt === s.id ? " spielt" : ""}" data-id="${s.id}">
        <div class="rh-sender-kern" data-aktion="waehlen">
          <span class="led"><ak-led farbe="${z.spielt === s.id ? "blau" : s.abgebrochen ? "bernstein" : "gelb"}" zustand="${z.spielt === s.id || s.abgebrochen ? "an" : "aus"}" groesse="klein" hilfe="${z.spielt === s.id ? "spielt" : s.abgebrochen ? "abgebrochen" : "bereit"}"></ak-led></span>
          <span class="rh-logo-bild" style="--lack:${R.lack(s.sender)}">${esc(R.kuerzel(s.sender))}</span>
          <div class="name"><b>${esc(s.sender)}</b><div class="meta"><span>${datum(s.datum)}</span><span>${esc(ordnerName(s.ordner))}</span>${s.abgebrochen ? `<span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>abgebrochen</span>` : ""}</div></div>
          <div class="rh-a-titelzahl">${s.titel.length}</div><div class="laenge">${zeit(s.dauer)}</div><div class="laenge">${mb(s.mb)}</div>
          <div class="rh-aktionen rh-a-aktionen">
            <button class="rund" type="button" data-aktion="hoeren" title="Hören" aria-label="Hören"><i class="fa-solid fa-play"></i></button>
            <button class="rund" type="button" data-aktion="schneiden" title="Schneiden" aria-label="Schneiden"><i class="fa-solid fa-scissors"></i></button>
            <button class="rund" type="button" data-aktion="waehlen" title="Titel zeigen" aria-label="Titel zeigen"><i class="fa-solid fa-chevron-right"></i></button>
          </div></div></article>`).join("")}
      <div class="rh-listen-fuss">${liste.length} Aufnahmen, alle geladen; ältere laden beim Rollen nach</div>`;
  }
  function titelliste(s) {
    return `<div class="rh-spalten rh-a-spalten" aria-hidden="true"><span>Titel</span><span class="rh-ohne-sort">ab</span><span class="rechts">Länge</span><span class="rechts">Größe</span><span></span></div>
      ${s.titel.map((t) => { const spielt = z.spielt === s.id && t.nr === 2; return `<article class="rh-sender rh-aufnahme rh-a-titel${spielt ? " spielt" : ""}" data-nr="${t.nr}">
        <div class="rh-sender-kern" data-aktion="hoeren">
          <span class="led"><ak-led farbe="blau" zustand="${spielt ? "an" : "aus"}" groesse="klein"></ak-led></span>
          <span class="rh-a-nr">${String(t.nr).padStart(2, "0")}</span>
          <div class="name"><b>${esc(t.titel)}</b>${t.titel === "Werbung" ? `<div class="meta"><span class="rh-geltung fest">gesperrt</span></div>` : ""}</div>
          <div class="rh-a-titelzahl rh-zahl">${zeit(t.start)}</div><div class="laenge">${zeit(t.dauer)}</div><div class="laenge">${mb(t.mb)}</div>
          <div class="rh-aktionen rh-a-aktionen">
            <button class="rund" type="button" data-aktion="hoeren" title="Ab hier hören" aria-label="Hören"><i class="fa-solid fa-play"></i></button>
            <button class="rund" type="button" title="Als Datei laden" aria-label="Laden"><i class="fa-solid fa-download"></i></button>
            <button class="rund" type="button" data-aktion="schneiden" title="Diesen Titel schneiden" aria-label="Schneiden"><i class="fa-solid fa-scissors"></i></button>
            <button class="rund" type="button" title="${t.titel === "Werbung" ? "Titel wieder teilen lassen" : "Diesen Titel künftig nicht teilen (Sperrliste)"}" aria-label="Sperren"><i class="fa-solid ${t.titel === "Werbung" ? "fa-eye" : "fa-eye-slash"}"></i></button>
            <button class="rund" type="button" data-aktion="fragen" data-art="titel" data-id="${t.nr}" title="Löschen" aria-label="Löschen"><i class="fa-solid fa-trash-can"></i></button>
          </div></div>
        ${gefragt("titel", t.nr) ? `<div class="rh-a-frage">${rueckfrage(`Titel "${esc(t.titel)}" löschen? ${mb(t.mb)} gehen in den Papierkorb der Kellerwolke.${s.titel.length === 1 ? " Es ist der letzte Titel: die ganze Aufnahme geht mit." : ""}`, "Löschen", "titel", t.nr)}</div>` : ""}
      </article>`; }).join("")}`;
  }
  function wolkenliste() {
    const ort = A.WOLKE[z.pfad] ?? { ordner: [], dateien: [] };
    if (!ort.dateien.length) return `<div class="rh-ohne-treffer"><i class="fa-solid fa-folder-open"></i><b>Keine Audiodateien in diesem Ordner</b><span>Links in einen Unterordner wechseln.</span></div>`;
    return `<div class="rh-spalten rh-a-spalten" role="group" aria-label="Sortierung"><span>${sortspalte("sender", "Datei", false)}${sortspalte("datum", "Datum", true)}</span><span class="rh-ohne-sort">Art</span>
        <span class="rechts">${sortspalte("dauer", "Länge", true)}</span><span class="rechts">${sortspalte("mb", "Größe", true)}</span><span></span></div>
      ${ort.dateien.map(([n, sek, groesse, tag], i) => `<article class="rh-sender rh-aufnahme" data-datei="${i}"><div class="rh-sender-kern" data-aktion="hoeren">
        <span class="led"><ak-led farbe="gelb" zustand="aus" groesse="klein"></ak-led></span>
        <span class="rh-a-dateisymbol"><i class="fa-solid fa-file-audio"></i></span>
        <div class="name"><b>${esc(n)}</b><div class="meta"><span>${esc(z.pfad)}</span><span>${new Date(tag).toLocaleDateString("de-DE")}</span></div></div>
        <div class="rh-a-titelzahl">${n.split(".").pop().toUpperCase()}</div><div class="laenge">${zeit(sek)}</div><div class="laenge">${mb(groesse)}</div>
        <div class="rh-aktionen rh-a-aktionen">
          <button class="rund" type="button" data-aktion="hoeren" title="Hören" aria-label="Hören"><i class="fa-solid fa-play"></i></button>
          <button class="rund" type="button" data-aktion="datei-schneiden" data-datei="${i}" title="Schneiden; das Ergebnis kommt als neue Datei daneben" aria-label="Schneiden"><i class="fa-solid fa-scissors"></i></button>
          <button class="rund" type="button" title="Auf dieses Gerät laden" aria-label="Laden"><i class="fa-solid fa-download"></i></button>
        </div></div></article>`).join("")}`;
  }
  $("#zeilen").addEventListener("click", (e) => {
    const so = e.target.closest("[data-sort]");
    if (so) { z.sort = z.sort[0] === so.dataset.sort ? [so.dataset.sort, !z.sort[1]] : [so.dataset.sort, so.dataset.sort === "datum" || so.dataset.sort === "dauer" || so.dataset.sort === "mb"]; neu(); return; }
    if (e.target.closest(".rh-schnitt")) return;
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    e.stopPropagation();
    const id = k.closest("[data-id]")?.dataset.id;
    const a = k.dataset.aktion;
    if (a === "waehlen") z.gewaehlt = id;
    if (a === "hoeren" && id) z.spielt = id;
    if (a === "schneiden") z.schnitt = oeffnen(id ?? z.gewaehlt);
    if (a === "datei-schneiden") { const d = A.WOLKE[z.pfad].dateien[+k.dataset.datei]; z.schnitt = oeffnenDatei(d); }
    if (a === "stopp") { z.laeuft = false; band(`<i class="fa-solid fa-circle-check" style="color:var(--led-gruen)"></i><span>Aufnahme gespeichert: <b>12:34</b>, 5 Titel, in <b>${esc(ziel()?.name ?? "Ohne Ordner")}</b></span>`); }
    if (a === "live") z.gewaehlt = null;
    if (a === "fragen") z.frage = [k.dataset.art, k.dataset.id];
    if (a === "abbrechen") z.frage = null;
    if (a === "ja") { z.frage = null; band(`<i class="fa-solid fa-trash-can"></i><span>In den Papierkorb der Kellerwolke gelegt</span>`); }
    neu();
  });
  $("#kopf").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    const a = k.dataset.aktion;
    if (a === "schneiden") z.schnitt = oeffnen(z.gewaehlt);
    if (a === "stopp") { z.laeuft = false; band(`<i class="fa-solid fa-circle-check" style="color:var(--led-gruen)"></i><span>Aufnahme gespeichert: <b>12:34</b>, 5 Titel</span>`); }
    if (a === "fragen") z.frage = [k.dataset.art, k.dataset.id];
    if (a === "abbrechen") z.frage = null;
    if (a === "ja") { z.sitzungen = z.sitzungen.filter((s) => s.id !== z.gewaehlt); z.gewaehlt = null; z.frage = null; band(`<i class="fa-solid fa-trash-can"></i><span>Aufnahme im Papierkorb der Kellerwolke</span>`); }
    if (a === "teilen") band(`<i class="fa-solid fa-wand-magic-sparkles"></i><span>Geteilt an den Titelwechseln; die ungeteilte Fassung bleibt als Version</span><button class="knopf primaer" type="button" data-band-zu><i class="fa-solid fa-rotate-left"></i>Rückgängig</button>`);
    neu();
  });

  // ─── Schnitt: Arbeitsplatz ───
  function oeffnen(id) {
    const s = sitzung(id);
    const marker = s.titel.slice(1).map((t) => t.start);
    return { art: "sitzung", id, name: `${s.sender}, ${datum(s.datum)}`, format: `${s.codec} ${s.kbit} kbit/s`, dauer: s.dauer,
      titel: s.titel, marker, verworfen: new Set(s.titel.map((t, i) => (t.titel === "Werbung" ? i : -1)).filter((i) => i >= 0)), von: 0, bis: s.dauer, kopfAn: 412 + 120,
      gain: 1, mitlaufen: true, schritte: [["Geöffnet", "21.11. 22:50"]], auftrag: null, fmt: "mp3" };
  }
  function oeffnenDatei([n, sek, , tag]) {
    return { art: "datei", name: n, pfad: z.pfad, format: n.split(".").pop().toUpperCase(), dauer: sek, titel: [], marker: [sek * 0.18, sek * 0.62],
      verworfen: new Set([0]), von: 0, bis: sek, kopfAn: sek * 0.3, gain: 1, mitlaufen: true, schritte: [["Geöffnet", new Date(tag).toLocaleDateString("de-DE")]], auftrag: null, fmt: "mp3" };
  }
  const stuecke = (s) => { const p = [0, ...s.marker, s.dauer]; return p.slice(0, -1).map((a, i) => ({ i, von: a, bis: p[i + 1], titel: s.titel.find((t) => Math.abs(t.start - a) < 1)?.titel ?? (s.art === "datei" ? `${s.name.replace(/\.[^.]+$/, "")} ${i + 1}` : `Teil ${i + 1}`) })); };
  function schnitt() {
    const s = z.schnitt, st = stuecke(s), behalten = st.filter((x) => !s.verworfen.has(x.i));
    const ziel = s.art === "datei" ? `${behalten.length} neue Dateien neben "${esc(s.name)}" im Ordner ${esc(s.pfad)}; das Original bleibt` : `ersetzt die Titel der Aufnahme durch ${behalten.length} neue; die alte Fassung bleibt als Version`;
    return `<section class="rh-schnitt" aria-label="Schnitt">
      <div class="rh-schnitt-kopf">
        <div><h2><i class="fa-solid fa-scissors"></i>Schnitt: ${esc(s.name)}</h2><p class="rh-still">${s.art === "datei" ? `Kellerwolke / ${esc(s.pfad)} · ` : ""}${s.format} · ${zeit(s.dauer)}</p></div>
        <div class="rh-schritte">
          <span class="ak-etikett">Schritte</span>
          <ol>${s.schritte.map(([was, wann], i) => `<li class="${i === s.schritte.length - 1 ? "jetzt" : ""}"><b>${i + 1}</b>${esc(was)}<span class="rh-still">${esc(wann)}</span></li>`).join("")}</ol>
          <button class="knopf" type="button" data-s="rueckgaengig" ${s.schritte.length < 2 ? "disabled" : ""} title="Den letzten Schritt zurücknehmen (Version der Kellerwolke)"><i class="fa-solid fa-rotate-left"></i>Rückgängig</button>
        </div>
        <button class="knopf" type="button" data-s="zu"><i class="fa-solid fa-xmark"></i>Schließen</button>
      </div>
      <div class="rh-schnitt-werkzeug">
        <div class="rh-knopfgruppe" role="group" aria-label="Ausschnitt">
          <button class="rund" type="button" data-s="zoom-raus" title="Weiter weg (Minus)" aria-label="Weiter weg"><i class="fa-solid fa-magnifying-glass-minus"></i></button>
          <output class="rh-zahl" title="sichtbarer Ausschnitt">${dauer(s.bis - s.von)}</output>
          <button class="rund" type="button" data-s="zoom-rein" title="Näher heran (Plus)" aria-label="Näher heran"><i class="fa-solid fa-magnifying-glass-plus"></i></button>
          <button class="knopf" type="button" data-s="alles" title="Die ganze Aufnahme"><i class="fa-solid fa-arrows-left-right-to-line"></i>Alles</button></div>
        <ak-dreh class="rh-gain" name="Höhe" hilfe="Höhe der Wellenform; der Ton bleibt, wie er ist" raster="1x|2x|4x|8x|16x" wert="0"></ak-dreh>
        <ak-taster art="flach" beschriftung="Mitlaufen" farbe="blau" ${s.mitlaufen ? "an" : ""} hilfe="Die Wellenform folgt dem Abspielkopf"></ak-taster>
        <div class="rh-knopfgruppe" role="group" aria-label="Marker">
          <button class="knopf" type="button" data-s="marker" title="Marker am Abspielkopf (M); Doppelklick in die Wellenform setzt ihn dort"><i class="fa-solid fa-location-pin"></i>Marker</button>
          ${s.titel.length ? `<button class="knopf" type="button" data-s="aus-titeln" title="Marker an die erkannten Titelwechsel setzen"><i class="fa-solid fa-tags"></i>Aus Titeln</button>` : ""}
          <button class="knopf" type="button" data-s="leeren" ${s.marker.length ? "" : "disabled"} title="Alle Marker entfernen"><i class="fa-solid fa-eraser"></i>Leeren (${s.marker.length})</button></div>
        <p class="rh-still rh-schnitt-tasten"><kbd>Leertaste</kbd> hören <kbd>M</kbd> Marker <kbd>Entf</kbd> Marker weg <kbd>+</kbd><kbd>-</kbd> Ausschnitt <kbd>Pfeile</kbd> springen</p>
      </div>
      <div class="rh-wellenform"><canvas id="welle" aria-label="Wellenform mit Titeln, Markern und Abspielkopf" role="img"></canvas></div>
      <div class="rh-uebersicht"><canvas id="uebersicht" aria-label="Übersicht der ganzen Aufnahme" role="img"></canvas></div>
      <div class="rh-stuecke">
        <div class="rh-spalten rh-stueck-spalten" aria-hidden="true"><span>Stück</span><span>von</span><span>bis</span><span class="rechts">Länge</span><span>Behalten</span><span></span></div>
        ${st.map((x) => `<div class="rh-stueck${s.verworfen.has(x.i) ? " weg" : ""}">
          <span class="rh-a-nr">${String(x.i + 1).padStart(2, "0")}</span>
          <label class="suche rh-stueck-name"><input type="text" value="${esc(x.titel)}" aria-label="Name des Stücks ${x.i + 1}" spellcheck="false"></label>
          <span class="rh-zahl">${zeit(x.von)}</span><span class="rh-zahl">${zeit(x.bis)}</span><span class="rh-zahl rechts">${zeit(x.bis - x.von)}</span>
          <ak-taster art="flach" beschriftung="${s.verworfen.has(x.i) ? "Weg" : "Behalten"}" farbe="gruen" ${s.verworfen.has(x.i) ? "" : "an"} data-stueck="${x.i}" hilfe="Stück behalten oder beim Schneiden verwerfen"></ak-taster>
          <button class="rund" type="button" title="Dieses Stück hören" aria-label="Hören"><i class="fa-solid fa-play"></i></button>
        </div>`).join("")}
      </div>
      <div class="rh-schnitt-aktionen">
        <div class="rh-schnitt-block"><span class="ak-etikett">Schneiden</span>
          <button class="knopf primaer" type="button" data-s="fragen-schnitt"><i class="fa-solid fa-scissors"></i>${behalten.length} ${behalten.length === 1 ? "Stück" : "Stücke"} behalten</button>
          <span class="rh-still">${ziel}</span></div>
        <div class="rh-schnitt-block"><span class="ak-etikett">Lautheit</span>
          <button class="knopf" type="button" data-s="normalisieren" title="Gleich laut wie Sender und Podcasts"><i class="fa-solid fa-volume-high"></i>Normalisieren auf -16 LUFS</button></div>
        <div class="rh-schnitt-block"><span class="ak-etikett">Umwandeln</span>
          <div class="segment" role="group" aria-label="Format">${["mp3", "ogg", "aac"].map((f) => `<button type="button" data-fmt="${f}" class="${s.fmt === f ? "aktiv" : ""}" aria-pressed="${s.fmt === f}">${f.toUpperCase()}</button>`).join("")}</div>
          <ak-dreh name="Bitrate" hilfe="Bitrate des Ergebnisses" raster="96|128|192|256|320" wert="2" einheit="kbit/s"></ak-dreh>
          <ak-taster art="flach" beschriftung="Mono" farbe="gelb" hilfe="Beide Kanäle zu einem zusammenlegen"></ak-taster>
          <button class="knopf" type="button" data-s="umwandeln"><i class="fa-solid fa-arrows-rotate"></i>Umwandeln</button></div>
      </div>
      ${s.frage ? rueckfrage(`${behalten.length} ${behalten.length === 1 ? "Stück" : "Stücke"} behalten und ${st.length - behalten.length} verwerfen? Das ${ziel}. Rückgängig geht danach über die Schritte.`, "Schneiden", "schnitt", "", "fa-scissors") : ""}
      ${s.auftrag ? `<div class="rh-auftrag"><ak-led farbe="gruen" zustand="blinkt" groesse="klein"></ak-led><span>${esc(s.auftrag.was)}: ${s.auftrag.text}</span>
        <div class="balken"><span style="width:${s.auftrag.anteil}%"></span></div><span class="rh-zahl">${s.auftrag.anteil} %</span><button class="rund" type="button" aria-label="Abbrechen" title="Abbrechen"><i class="fa-solid fa-xmark"></i></button></div>` : ""}
    </section>`;
  }
  $("#zeilen").addEventListener("click", (e) => {
    if (!z.schnitt) return;
    const s = z.schnitt, k = e.target.closest("[data-s], [data-fmt], [data-aktion]");
    if (!k) return;
    const was = k.dataset.s;
    if (k.dataset.fmt) s.fmt = k.dataset.fmt;
    if (was === "zu") { z.schnitt = null; neu(); return; }
    if (was === "zoom-rein") { const m = (s.von + s.bis) / 2, b = Math.max(10, (s.bis - s.von) / 2); s.von = Math.max(0, m - b / 2); s.bis = Math.min(s.dauer, m + b / 2); }
    if (was === "zoom-raus") { const m = (s.von + s.bis) / 2, b = Math.min(s.dauer, (s.bis - s.von) * 2); s.von = Math.max(0, m - b / 2); s.bis = Math.min(s.dauer, s.von + b); }
    if (was === "alles") { s.von = 0; s.bis = s.dauer; }
    if (was === "marker") { s.marker = [...s.marker, s.kopfAn].sort((a, b) => a - b); }
    if (was === "aus-titeln") { s.marker = s.titel.slice(1).map((t) => t.start); }
    if (was === "leeren") { s.marker = []; s.verworfen = new Set(); }
    if (was === "fragen-schnitt") s.frage = true;
    if (k.dataset.aktion === "abbrechen") s.frage = false;
    if (k.dataset.aktion === "ja") { s.frage = false; s.auftrag = { was: "Schneiden", text: "Stück 2 von 4 wird abgelegt", anteil: 45 }; s.schritte.push(["Geschnitten", "gerade eben"]); }
    if (was === "normalisieren") { s.auftrag = { was: "Normalisieren", text: "misst die Lautheit", anteil: 20 }; s.schritte.push(["Normalisiert -16 LUFS", "gerade eben"]); }
    if (was === "umwandeln") { s.auftrag = { was: "Umwandeln", text: `nach ${s.fmt.toUpperCase()}`, anteil: 10 }; s.schritte.push([`Umgewandelt in ${s.fmt.toUpperCase()}`, "gerade eben"]); }
    if (was === "rueckgaengig") { const [w] = s.schritte.pop(); s.auftrag = null; band(`<i class="fa-solid fa-rotate-left"></i><span>Zurückgenommen: <b>${esc(w)}</b> (vorige Version wiederhergestellt)</span>`); }
    neu();
  });
  $("#zeilen").addEventListener("input", (e) => {
    const t = e.target.closest("ak-taster[data-stueck]"); if (!t || !z.schnitt) return;
    const i = +t.dataset.stueck, weg = !t.hasAttribute("an");
    if (weg === z.schnitt.verworfen.has(i)) return;            // Taster melden beim Einhängen ihren Wert
    weg ? z.schnitt.verworfen.add(i) : z.schnitt.verworfen.delete(i); neu();
  });
  $("#zeilen").addEventListener("dblclick", (e) => {
    if (e.target.id !== "welle" || !z.schnitt) return;
    const s = z.schnitt, r = e.target.getBoundingClientRect(), t = s.von + (e.clientX - r.left) / r.width * (s.bis - s.von);
    s.marker = [...s.marker, Math.round(t * 10) / 10].sort((a, b) => a - b); neu();
  });

  // Wellenform zeichnen: Titelbereiche abwechselnd, verworfene Stücke schraffiert, Marker mit Nummer, Abspielkopf, Zeitleiste
  // Marken als fertige Farbe: über ein verstecktes Element aufgelöst (Mischungen wie color-mix kann die Zeichenfläche nicht lesen)
  const probe = Object.assign(document.createElement("i"), { hidden: true });
  document.body.append(probe);
  function farbe(n) { probe.style.color = `var(${n})`; return getComputedStyle(probe).color; }
  function spitze(t) { const a = Math.sin(t * 0.7) * 0.25 + Math.sin(t * 0.13) * 0.2 + Math.sin(t * 2.3) * 0.15; return Math.min(1, Math.max(0.05, 0.55 + a + (Math.sin(t * 37.1) * 0.5 + 0.5) * 0.25)); }
  function zeichne(canvas, von, bis, gross) {
    const s = z.schnitt, dpr = devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
    canvas.width = w * dpr; canvas.height = h * dpr;
    const c = canvas.getContext("2d"); c.scale(dpr, dpr);
    const x = (t) => (t - von) / (bis - von) * w, mitte = gross ? (h - 18) / 2 + 18 : h / 2, hoehe = gross ? (h - 24) / 2 : h / 2 - 2;
    stuecke(s).forEach((st, i) => {
      c.fillStyle = i % 2 ? farbe("--flaeche-2") : farbe("--mulde"); c.fillRect(x(st.von), 0, x(st.bis) - x(st.von), h);
      if (s.verworfen.has(st.i)) { c.fillStyle = "rgba(220, 60, 50, .16)"; c.fillRect(x(st.von), 0, x(st.bis) - x(st.von), h); }
      if (gross && x(st.bis) - x(st.von) > 60) { c.fillStyle = farbe("--text-3"); c.font = `600 11px ${getComputedStyle(document.body).fontFamily}`; c.fillText(st.titel.slice(0, 40), x(st.von) + 6, 13); }
    });
    c.fillStyle = farbe("--led-gruen");
    for (let px = 0; px < w; px += gross ? 2 : 1) {
      const t = von + px / w * (bis - von), weg = [...s.verworfen].some((i) => { const st = stuecke(s)[i]; return st && t >= st.von && t < st.bis; });
      const v = spitze(t) * hoehe * (gross ? 1 : 0.9);
      c.globalAlpha = weg ? 0.35 : 1; c.fillRect(px, mitte - v, gross ? 1.4 : 1, v * 2);
    }
    c.globalAlpha = 1;
    s.marker.forEach((m, i) => { const mx = x(m); if (mx < 0 || mx > w) return; c.fillStyle = farbe("--akzent"); c.fillRect(mx - 1, gross ? 16 : 0, 2, h);
      if (gross) { c.beginPath(); c.arc(mx, 22, 8, 0, Math.PI * 2); c.fill(); c.fillStyle = farbe("--hg"); c.font = `700 10px ${getComputedStyle(document.body).fontFamily}`; c.textAlign = "center"; c.fillText(String(i + 1), mx, 25.5); c.textAlign = "left"; } });
    const kx = x(s.kopfAn); c.fillStyle = farbe("--led-blau"); c.fillRect(kx - 1, 0, 2, h);
    if (!gross) { c.strokeStyle = farbe("--text"); c.lineWidth = 1.5; c.strokeRect(x(s.von) + 0.75, 0.75, x(s.bis) - x(s.von) - 1.5, h - 1.5); }
  }
  function wellenform() {
    const s = z.schnitt; if (!s) return;
    requestAnimationFrame(() => { const w = $("#welle"), u = $("#uebersicht"); if (w) zeichne(w, s.von, s.bis, true); if (u) zeichne(u, 0, s.dauer, false); });
  }
  addEventListener("resize", wellenform);
  document.addEventListener("keydown", (e) => {
    if (!z.schnitt || e.target.matches("input")) return;
    if (e.key === "m" || e.key === "M") { z.schnitt.marker = [...z.schnitt.marker, z.schnitt.kopfAn].sort((a, b) => a - b); neu(); }
    if (e.key === "+") $("[data-s=zoom-rein]")?.click();
    if (e.key === "-") $("[data-s=zoom-raus]")?.click();
  });

  // ─── Band ───
  function band(html) {
    const b = $("#band"); b.innerHTML = `${html}<button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`; b.hidden = false;
    clearTimeout(band.uhr); band.uhr = setTimeout(() => (b.hidden = true), 10000);
    b.querySelectorAll("[data-band-zu]").forEach((x) => x.addEventListener("click", () => (b.hidden = true)));
  }

  // ─── Seitenleiste als Tafel (schmal) ───
  const filter = $("#filter"), schleier = $("#schleier");
  const tafel = (auf) => { filter.classList.toggle("offen", auf); schleier.classList.toggle("offen", auf); $("#filter-auf").setAttribute("aria-expanded", String(auf)); };
  $("#filter-auf").addEventListener("click", () => tafel(true)); $("#filter-zu").addEventListener("click", () => tafel(false)); schleier.addEventListener("click", () => tafel(false));

  // ─── Zustände des Entwurfs ───
  const ZUSTAENDE = [
    ["alle Aufnahmen", () => { Object.assign(z, { quelle: "aufnahmen", ordner: "", gewaehlt: null, laeuft: false, schnitt: null, frage: null }); }],
    ["eine Aufnahme gewählt", () => { Object.assign(z, { quelle: "aufnahmen", ordner: "", gewaehlt: "s1", laeuft: false, schnitt: null, frage: null }); }],
    ["Aufnahme läuft", () => { Object.assign(z, { quelle: "aufnahmen", ordner: "", gewaehlt: null, laeuft: true, schnitt: null, frage: null }); }],
    ["Schnitt einer Aufnahme", () => { Object.assign(z, { quelle: "aufnahmen", gewaehlt: "s1", laeuft: false, frage: null }); z.schnitt = oeffnen("s1"); }],
    ["Schnitt: Normalisieren läuft, Schritte", () => { Object.assign(z, { quelle: "aufnahmen", gewaehlt: "s1", laeuft: false, frage: null }); z.schnitt = oeffnen("s1");
      z.schnitt.schritte.push(["Geschnitten in 6 Stücke", "22:52"]); z.schnitt.auftrag = { was: "Normalisieren", text: "Stück 3 von 6", anteil: 48 }; z.schnitt.schritte.push(["Normalisiert -16 LUFS", "läuft"]); }],
    ["Kellerwolke: fremde Dateien", () => { Object.assign(z, { quelle: "wolke", pfad: "Interviews", gewaehlt: null, laeuft: false, schnitt: null, frage: null }); }],
  ];
  let zustand = 0;
  function zeige(i) { zustand = (i + ZUSTAENDE.length) % ZUSTAENDE.length; ZUSTAENDE[zustand][1](); $("#entwurf-zustand").textContent = `${zustand + 1}/${ZUSTAENDE.length}: ${ZUSTAENDE[zustand][0]}`; neu(); }
  $("#entwurf-zurueck").addEventListener("click", () => zeige(zustand - 1));
  $("#entwurf-vor").addEventListener("click", () => zeige(zustand + 1));

  // Kanzel: während einer Aufnahme spielt der Sender live (Wechsel gesperrt), sonst die gewählte Aufnahme
  function kanzel() {
    const L = A.LAEUFT, live = z.laeuft, s = sitzung(z.spielt) ?? z.sitzungen[0];
    const titel = live ? L.titel[L.titel.length - 1][1] : s.titel[Math.min(1, s.titel.length - 1)].titel;
    $("#k-sender").textContent = live ? L.sender : s.sender; $("#k-titel").textContent = titel;
    $("#d-art").textContent = live ? "LIVE · AUFNAHME" : "AUFNAHME";
    $("#d-format").textContent = live ? `${L.codec} ${L.kbit} · ${L.titel.length} Titel erkannt · Wechsel gesperrt` : `${s.codec} ${s.kbit} · Titel 2 von ${s.titel.length}`;
    $("#d-sender").setAttribute("text", (live ? L.sender : s.sender).toUpperCase()); $("#d-titel").textContent = titel;
    $("#q-text").setAttribute("text", live ? "LIVE" : "AUFNAHME");
    $("#zeit").setAttribute("text", live ? zeit(L.sekunden).padStart(8, "0") : "00:03:12");
    $("#d-led").setAttribute("farbe", live ? "rot" : "blau");
  }

  function neu() {
    kanzel();
    $("#mitte").classList.toggle("rh-im-schnitt", !!z.schnitt);
    $("#nav-led-aufnahme")?.setAttribute("zustand", z.laeuft ? "blinkt" : "aus");
    $("#t-rec")?.toggleAttribute("an", z.laeuft);
    leiste(); werkzeug(); kopf(); zeilen();
  }
  const start = new URLSearchParams(location.search).get("zustand");
  zeige(start ? Number(start) - 1 : 0);
})();
