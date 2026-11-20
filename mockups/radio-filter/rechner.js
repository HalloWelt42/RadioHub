// Verhalten der Radio-Ansicht am Rechner (Entwurf RAD-3): Schnellfilter mit Zählern, aktive Filter als Chips, Liste
// mit Gruppen und Details, Ausblenden mit Rückgängig, Zustände der Abspielleiste. Nur Entwurf: Treffer gesamt sind eine
// Schätzung aus den Facettenzahlen, die Liste zeigt die Muster, die zur Auswahl passen. Filter stehen in der Adresse.

(() => {
  "use strict";
  const D = window.RHDaten, R = window.RH, $ = (s, w = document) => w.querySelector(s), $$ = (s, w = document) => [...w.querySelectorAll(s)];
  const GRUPPEN = ["land", "genre", "guete", "codec", "bewertung", "kategorie"];
  const adresse = new URLSearchParams(location.search);
  const neu = !adresse.has("f");   // ohne gespeicherte Auswahl: Beispielauswahl Deutschland, Stimmen ab 10
  const z = {
    land: new Set(neu ? ["DE"] : (adresse.get("land") || "").split(",").filter(Boolean)),
    genre: new Set((adresse.get("genre") || "").split(",").filter(Boolean)),
    guete: new Set((adresse.get("guete") || "").split(",").filter(Boolean)),
    codec: new Set((adresse.get("codec") || "").split(",").filter(Boolean)),
    bewertung: new Set((adresse.get("bewertung") || "").split(",").filter(Boolean)),
    kategorie: new Set((adresse.get("kategorie") || "").split(",").filter(Boolean)),
    favoriten: adresse.get("favoriten") === "1",
    stimmen: neu ? 1 : Number(adresse.get("stimmen") || 0),
    bitrate: Number(adresse.get("bitrate") || 0),
    suche: adresse.get("suche") || "",
    sort: adresse.get("sort") || "stimmen",
    offen: new Set(["dlfk"]), varianten: new Set(["dlf"]), ausgeblendet: new Set(), spielt: "dlfk",
    favorit: new Set(D.SENDER.filter((s) => s.favorit).map((s) => s.id)),
    bewertungVon: Object.fromEntries(D.SENDER.map((s) => [s.id, s.bewertung])),
  };
  const FAEHIGKEITEN = { voll: ["dienst", "aufnahme", "podcasts", "einstellungen", "zeitversatz", "uebergabe", "titel"], web: ["wecker", "demo"] };
  let faehig = new Set(FAEHIGKEITEN.voll);
  const NAMEN = { land: (w) => D.LAENDER[w], genre: (w) => w, guete: (w) => `Qualität ${w}`, codec: (w) => w,
    bewertung: (w) => (w === "werbung" ? "Werbung" : D.BEWERTUNG_NAMEN[w]), kategorie: (w) => w };
  const TITEL = { land: "Land", genre: "Genre", guete: "", codec: "Codec", bewertung: "Bewertung", kategorie: "Kategorie" };

  // ─── Facetten in der Seitenleiste ───
  function kennung(gruppe, w) {
    if (gruppe === "land") return `<span class="rh-kennung">${w}</span>`;
    if (gruppe === "guete") return R.guete(w);
    if (gruppe === "bewertung") return w === "werbung" ? `<span class="rh-kennung" title="als Werbung markiert"><i class="fa-solid fa-rectangle-ad"></i></span>` : R.sterne(Number(w));
    return "";
  }
  function facette(gruppe, w, n) {
    const k = kennung(gruppe, w);
    return `<label class="rh-facette${k ? "" : " ohne-kennung"}"><input type="checkbox" data-gruppe="${gruppe}" value="${R.esc(w)}"${z[gruppe].has(w) ? " checked" : ""}>${k}<span>${R.esc(NAMEN[gruppe](w))}</span><span class="rh-zahl">${R.zahl(n)}</span></label>`;
  }
  function facettenBauen() {
    for (const g of ["land", "guete", "bewertung", "kategorie"]) $(`#f-${g}`).innerHTML = D.FACETTEN[g].werte.map(([w, n]) => facette(g, w, n)).join("");
    const genres = D.FACETTEN.genre;
    $("#f-genre").innerHTML = genres.werte.map(([w, n]) => facette("genre", w, n)).join("")
      + `<div id="f-genre-mehr" hidden>${genres.mehr.map(([w, n]) => facette("genre", w, n)).join("")}</div>`;
    $("#genre-mehr").textContent = `Alle ${genres.werte.length + genres.mehr.length} zeigen`;
    $("#f-codec").innerHTML = D.FACETTEN.codec.werte.map(([w, n]) => `<button type="button" class="chip wahl${z.codec.has(w) ? " an" : ""}" data-gruppe="codec" data-wert="${w}" aria-pressed="${z.codec.has(w)}">${w}<span class="rh-zahl">${R.zahl(n)}</span></button>`).join("");
  }
  $("#genre-mehr").addEventListener("click", (e) => {
    const mehr = $("#f-genre-mehr"); mehr.hidden = !mehr.hidden;
    e.currentTarget.textContent = mehr.hidden ? `Alle ${D.FACETTEN.genre.werte.length + D.FACETTEN.genre.mehr.length} zeigen` : "Weniger zeigen";
  });
  $("#filter").addEventListener("change", (e) => {
    const k = e.target.closest("input[data-gruppe]"); if (!k) return;
    z[k.dataset.gruppe][k.checked ? "add" : "delete"](k.value); aktualisieren();
  });
  $("#f-codec").addEventListener("click", (e) => {
    const k = e.target.closest("[data-gruppe]"); if (!k) return;
    const an = !z.codec.has(k.dataset.wert);
    z.codec[an ? "add" : "delete"](k.dataset.wert); k.classList.toggle("an", an); k.setAttribute("aria-pressed", String(an)); aktualisieren();
  });

  // Schnellwahl: Favoriten (Taster), Stimmen (Drehwahl), Bitrate (Schieber)
  const taster = $("#nur-favoriten"), dreh = $("#stimmen-wahl"), schieber = $("#bitrate-wahl");
  taster.addEventListener("input", () => { const an = taster.hasAttribute("an"); if (an !== z.favoriten) { z.favoriten = an; aktualisieren(); } });
  dreh.addEventListener("input", () => { if (dreh.wert !== z.stimmen) { z.stimmen = dreh.wert; aktualisieren(); } });
  schieber.addEventListener("input", () => { if (schieber.wert !== z.bitrate) { z.bitrate = schieber.wert; aktualisieren(); } });

  // ─── Auswahl auswerten ───
  const passt = (s) => !z.ausgeblendet.has(s.id)
    && (!z.land.size || z.land.has(s.land))
    && (!z.genre.size || s.genres.some((g) => z.genre.has(g)))
    && (!z.guete.size || z.guete.has(s.guete))
    && (!z.codec.size || z.codec.has(s.codec))
    && (!z.bewertung.size || [...z.bewertung].some((b) => (b === "werbung" ? s.werbung : z.bewertungVon[s.id] === Number(b))))
    && (!z.kategorie.size || s.kategorien.some((k) => z.kategorie.has(k)))
    && (!z.favoriten || z.favorit.has(s.id))
    && s.stimmen >= D.STIMMEN_STUFEN[z.stimmen][1]
    && (D.BITRATE_STUFEN[z.bitrate][1] === 0 || s.kbps >= D.BITRATE_STUFEN[z.bitrate][1])
    && (!z.suche || `${s.name} ${s.genres.join(" ")} ${s.ort}`.toLowerCase().includes(z.suche.toLowerCase()));
  function trefferGesamt(passend) {
    if (z.favoriten || z.bewertung.size || z.kategorie.size) return Math.max(passend.length, Math.round(passend.length * (D.BESTAND.favoriten / 16)));
    let n = D.BESTAND.sichtbar;
    for (const g of ["land", "genre", "guete", "codec"]) {
      if (!z[g].size) continue;
      const summe = D.FACETTEN[g].werte.concat(D.FACETTEN[g].mehr || []).filter(([w]) => z[g].has(w)).reduce((a, [, x]) => a + x, 0);
      n *= Math.min(1, summe / D.BESTAND.sichtbar);
    }
    n *= D.STIMMEN_STUFEN[z.stimmen][2] * D.BITRATE_STUFEN[z.bitrate][2];
    if (z.suche) n = Math.min(n, passend.length * 3 + 2);
    return Math.max(passend.length, Math.round(n));
  }

  // ─── Aktive Filter als Chips ───
  function chips() {
    const liste = [];
    for (const g of GRUPPEN) for (const w of z[g]) liste.push([`${TITEL[g] ? `${TITEL[g]}: ` : ""}<b>${R.esc(NAMEN[g](w))}</b>`, () => { z[g].delete(w); $$(`input[data-gruppe="${g}"]`).forEach((k) => { if (k.value === w) k.checked = false; }); $$(`#f-codec [data-wert="${w}"]`).forEach((k) => { k.classList.remove("an"); k.setAttribute("aria-pressed", "false"); }); }]);
    if (z.favoriten) liste.push(["<b>Nur Favoriten</b>", () => { z.favoriten = false; taster.setzen(false); }]);
    if (z.stimmen) liste.push([`Stimmen: <b>${D.STIMMEN_STUFEN[z.stimmen][0]}</b>`, () => { z.stimmen = 0; dreh.wert = 0; }]);
    if (z.bitrate) liste.push([`Bitrate: <b>ab ${D.BITRATE_STUFEN[z.bitrate][0]} kbit/s</b>`, () => { z.bitrate = 0; schieber.wert = 0; }]);
    if (z.suche) liste.push([`Suche: <b>${R.esc(z.suche)}</b>`, () => { z.suche = ""; $("#suche").value = ""; }]);
    const feld = $("#aktiv-chips");
    feld.innerHTML = liste.length ? liste.map(([t], i) => `<span class="chip">${t}<button type="button" data-chip="${i}" aria-label="Filter entfernen" title="Entfernen"><i class="fa-solid fa-xmark"></i></button></span>`).join("")
      : `<span class="rh-leer-chips">Keine Schnellfilter, alle sichtbaren Sender</span>`;
    feld.onclick = (e) => { const b = e.target.closest("[data-chip]"); if (b) { liste[Number(b.dataset.chip)][1](); aktualisieren(); } };
    $("#alle-zurueck").disabled = !liste.length;
    $("#filter-zurueck").disabled = !liste.length;
    $("#filter-zahl").textContent = `${liste.length} aktiv`;
    $("#filter-auf-zahl").textContent = String(liste.length);
  }
  function alleZuruecksetzen() {
    GRUPPEN.forEach((g) => z[g].clear()); z.favoriten = false; z.stimmen = 0; z.bitrate = 0; z.suche = "";
    $$("#filter input[data-gruppe]").forEach((k) => { k.checked = false; }); $$("#f-codec .chip").forEach((k) => { k.classList.remove("an"); k.setAttribute("aria-pressed", "false"); });
    taster.setzen(false); dreh.wert = 0; schieber.wert = 0; $("#suche").value = "";
    aktualisieren();
  }
  $("#alle-zurueck").addEventListener("click", alleZuruecksetzen);
  $("#filter-zurueck").addEventListener("click", alleZuruecksetzen);
  $("#suche").addEventListener("input", (e) => { z.suche = e.target.value.trim(); aktualisieren(); });
  $("#suche-leeren").addEventListener("click", () => { z.suche = ""; $("#suche").value = ""; aktualisieren(); });

  // ─── Liste ───
  const RANG = { verlustfrei: 4, hoch: 3, mittel: 2, niedrig: 1, unbekannt: 0 };
  const SORTEN = { stimmen: (a, b) => b.stimmen - a.stimmen, name: (a, b) => a.name.localeCompare(b.name, "de"),
    guete: (a, b) => RANG[b.guete] - RANG[a.guete] || b.kbps - a.kbps, bitrate: (a, b) => b.kbps - a.kbps };
  const slug = (n) => n.toLowerCase().replace(/ä/g, "ae").replace(/ö/g, "oe").replace(/ü/g, "ue").replace(/[^a-z0-9]+/g, "");

  function detail(s) {
    const verlauf = D.VERLAUF[s.id] || D.VERLAUF._musik;
    const aehnlich = (D.AEHNLICH[s.id] || D.SENDER.filter((x) => x.id !== s.id && x.genres.some((g) => s.genres.includes(g))).slice(0, 4).map((x) => [x.id, `${x.genres.join(", ")}, ${D.GUETE[x.guete].name}`]))
      .map(([id, grund]) => [D.SENDER.find((x) => x.id === id), grund]);
    const strom = `https://streams.${slug(s.name)}.de/live/${s.codec.toLowerCase()}-${s.kbps || s.verz}`;
    const b = z.bewertungVon[s.id];
    return `<div class="rh-detail">
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-circle-info"></i>Steckbrief</h4>
        <dl class="rh-werte">
          <dt>Homepage</dt><dd><a href="#" onclick="return false">www.${slug(s.name)}.de</a></dd>
          <dt>Stream</dt><dd class="rh-strom"><code>${strom}</code><button class="rund" type="button" title="Adresse kopieren" aria-label="Adresse kopieren"><i class="fa-regular fa-copy"></i></button></dd>
          <dt>Codec</dt><dd>${R.bitrate(s)} gemessen${s.verz ? `, Verzeichnis ${s.verz}` : ""}</dd>
          <dt>Sprache</dt><dd>${s.sprache}</dd>
          <dt>Ort</dt><dd>${s.ort}, ${D.LAENDER[s.land]}</dd>
          <dt>Geprüft</dt><dd>heute 04:12, Strom erreichbar</dd>
          <dt>Werbung</dt><dd>${s.werbung ? "Verdacht mittel (eigene Markierung)" : "kein Verdacht"}</dd>
        </dl></section>
      ${faehig.has("titel") ? `<section class="rh-tafel-detail"><h4><i class="fa-solid fa-clock-rotate-left"></i>Titelverlauf</h4>
        <div class="ak-glas rh-verlauf">${verlauf.map(([zeit, t]) => `<div><time>${zeit}</time><span>${R.esc(t)}</span></div>`).join("")}</div>
        <span class="rh-still">aus dem Strom gelesen, die letzten 6 von höchstens 200</span></section>` : ""}
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-diagram-project"></i>Ähnliche Sender</h4>
        <div class="rh-aehnlich">${aehnlich.map(([x, grund]) => `<div class="rh-aehnlich-zeile">${R.logo(x, "klein")}<span><b>${R.esc(x.name)}</b><span>${R.esc(grund)}</span></span><button class="rund" type="button" data-aktion="spielen" data-id="${x.id}" title="${R.esc(x.name)} hören" aria-label="${R.esc(x.name)} hören"><i class="fa-solid fa-play"></i></button></div>`).join("")}</div></section>
      <section class="rh-tafel-detail"><h4><i class="fa-solid fa-star"></i>Eigene Bewertung</h4>
        <div class="rh-bewerten">${[1, 2, 3].map((i) => `<button type="button" class="rh-stern${i <= b ? " an" : ""}" data-aktion="stern" data-wert="${i}" aria-label="${i} Sterne" title="${D.BEWERTUNG_NAMEN[i]}"><i class="fa-solid fa-star"></i></button>`).join("")}
          <button type="button" class="chip wahl${s.werbung ? " an" : ""}" data-aktion="werbung"><i class="fa-solid fa-rectangle-ad"></i>Werbung</button></div>
        <h4><i class="fa-solid fa-folder"></i>Eigene Kategorien</h4>
        <div class="rh-bewerten">${D.FACETTEN.kategorie.werte.map(([k]) => `<button type="button" class="chip wahl${s.kategorien.includes(k) ? " an" : ""}" data-aktion="kategorie" data-wert="${R.esc(k)}">${R.esc(k)}</button>`).join("")}</div></section>
    </div>`;
  }
  function varianten(s) {
    const liste = [...s.varianten].sort((a, b) => RANG[b.guete] - RANG[a.guete] || b.kbps - a.kbps);
    return `<div class="rh-varianten" role="list" aria-label="Varianten von ${R.esc(s.name)}">${liste.map((v, i) => `<div class="rh-variante" role="listitem">
      <ak-led farbe="${i === 0 ? "gruen" : "gelb"}" zustand="${i === 0 ? "an" : "aus"}" groesse="klein"></ak-led>
      <span><b>${v.codec} ${R.zahl(v.kbps)} kbit/s</b> · ${v.art}${i === 0 ? ` <span class="stand-pille fertig">beste Variante</span>` : ""}</span>
      <span class="rh-guete-text">${R.guete(v.guete)}</span><span class="stimmen-v rh-zahl"><i class="fa-solid fa-thumbs-up"></i> ${R.zahl(v.stimmen)}</span>
      <button class="knopf" type="button" data-aktion="spielen" data-id="${s.id}"><i class="fa-solid fa-play"></i>Hören</button></div>`).join("")}</div>`;
  }
  function zeile(s) {
    const spielt = z.spielt === s.id, offen = z.offen.has(s.id), fav = z.favorit.has(s.id), n = s.varianten.length;
    const varKnopf = n ? `<button class="knopf rh-varianten-knopf" type="button" data-aktion="varianten" aria-expanded="${z.varianten.has(s.id)}" title="Gleicher Sender in ${n} Varianten, beste vorn"><i class="fa-solid fa-layer-group"></i><span><span class="rh-zahl">${n}</span> Varianten</span></button>` : "";
    return `<article class="rh-sender${spielt ? " spielt" : offen ? " gewaehlt" : ""}${offen ? " offen" : ""}" data-id="${s.id}">
      <div class="rh-sender-kern" data-aktion="spielen" data-id="${s.id}">
        <span class="led"><ak-led farbe="${spielt ? "blau" : "gelb"}" zustand="${spielt || offen ? "an" : "aus"}" groesse="klein" text="" hilfe="${spielt ? "spielt" : offen ? "gewählt" : "bereit"}"></ak-led></span>
        ${R.logo(s)}
        <div class="name"><b>${R.esc(s.name)}</b><div class="meta"><span class="rh-kennung">${s.land}</span><span>${R.esc(s.ort)}</span>${faehig.has("titel") ? `<span class="rh-titel"><i class="fa-solid ${spielt ? "fa-volume-high" : "fa-music"}"></i>${R.esc(s.titel)}</span>` : ""}
          ${n ? varKnopf.replace("rh-varianten-knopf", "rh-varianten-knopf rh-varianten-knopf-schmal") : ""}
</div></div>
        <div class="genres">${s.genres.map((g) => `<span class="rh-genre">${g}</span>`).join("")}</div>
        <div class="guete-zelle">${R.guete(s.guete)}<b>${D.GUETE[s.guete].name}</b><span>${s.kbps ? `${s.codec} ${R.zahl(s.kbps)}` : `${s.codec} ?`}</span></div>
        <div class="stimmen"><button class="rund rh-auge-schmal" type="button" data-aktion="ausblenden" title="Ausblenden, mit Rückgängig" aria-label="${R.esc(s.name)} ausblenden"><i class="fa-solid fa-eye-slash"></i></button><span title="Stimmen im Senderverzeichnis"><i class="fa-solid fa-thumbs-up"></i>${R.zahl(s.stimmen)}</span></div>
        <div class="rh-aktionen">
          <span class="rh-varianten-zelle">${varKnopf || `<span class="rh-platz"></span>`}</span>
          <button class="rund${fav ? " favorit" : ""}" type="button" data-aktion="favorit" aria-pressed="${fav}" title="${fav ? "Aus den Favoriten nehmen" : "Zu den Favoriten"}" aria-label="Favorit"><i class="fa-${fav ? "solid" : "regular"} fa-star"></i></button>
          <span class="auge-zelle"><button class="rund" type="button" data-aktion="ausblenden" title="Ausblenden, mit Rückgängig" aria-label="${R.esc(s.name)} ausblenden"><i class="fa-solid fa-eye-slash"></i></button></span>
          <button class="rund" type="button" data-aktion="details" aria-expanded="${offen}" title="Details" aria-label="Details zu ${R.esc(s.name)}"><i class="fa-solid fa-chevron-down"></i></button>
        </div>
      </div>
      ${n && z.varianten.has(s.id) ? varianten(s) : ""}
      ${offen ? detail(s) : ""}
    </article>`;
  }
  function liste(passend) {
    const sortiert = [...passend].sort(SORTEN[z.sort]);
    const treffer = trefferGesamt(passend);
    $("#zeilen").innerHTML = sortiert.length ? sortiert.map(zeile).join("")
      + `<div class="rh-listen-fuss">${R.zahl(sortiert.length)} von ${R.zahl(treffer)} Treffern geladen, weitere Seiten laden beim Rollen</div>`
      : `<div class="rh-ohne-treffer"><i class="fa-solid fa-filter-circle-xmark"></i><b>Keine Muster für diese Auswahl im Entwurf</b><span>In der App stünden hier die ${R.zahl(treffer)} Treffer.</span><button class="knopf" type="button" data-aktion="zurueck">Alle Filter zurücksetzen</button></div>`;
  }
  $("#zeilen").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    const zeileEl = k.closest("[data-id]"), id = k.dataset.id || zeileEl?.dataset.id, s = D.SENDER.find((x) => x.id === id);
    const a = k.dataset.aktion;
    if (a === "zurueck") return alleZuruecksetzen();
    if (a === "spielen") { if (k.classList.contains("rh-sender-kern") && e.target.closest("a, .rh-detail")) return; spielen(s); }
    if (a === "details") { z.offen.has(id) ? z.offen.delete(id) : z.offen.add(id); }
    if (a === "varianten") { z.varianten.has(id) ? z.varianten.delete(id) : z.varianten.add(id); }
    if (a === "favorit") { z.favorit.has(id) ? z.favorit.delete(id) : z.favorit.add(id); }
    if (a === "ausblenden") { z.ausgeblendet.add(id); band(s); }
    if (a === "stern") { const w = Number(k.dataset.wert); z.bewertungVon[id] = z.bewertungVon[id] === w ? 0 : w; }
    if (a === "werbung") { s.werbung = !s.werbung; }
    if (a === "kategorie") { const w = k.dataset.wert; s.kategorien = s.kategorien.includes(w) ? s.kategorien.filter((x) => x !== w) : [...s.kategorien, w]; }
    e.stopPropagation();
    aktualisieren(false);
  });

  // Ausblenden: kein anderer Sender startet; das Band bietet Rückgängig und den Weg zur Liste der ausgeblendeten
  let bandUhr;
  function band(s) {
    const b = $("#band");
    b.innerHTML = `<i class="fa-solid fa-eye-slash"></i><span><b>${R.esc(s.name)}</b> ausgeblendet (Einzelsperre)</span><button class="knopf primaer" type="button" id="band-zurueck"><i class="fa-solid fa-rotate-left"></i>Rückgängig</button><a class="knopf still" href="regeln.html?reiter=ausgeblendet">Liste</a><button class="rund" type="button" id="band-zu" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`;
    b.hidden = false;
    $("#band-zurueck").onclick = () => { z.ausgeblendet.delete(s.id); b.hidden = true; aktualisieren(false); };
    $("#band-zu").onclick = () => { b.hidden = true; };
    clearTimeout(bandUhr); bandUhr = setTimeout(() => { b.hidden = true; }, 12000);
  }

  // ─── Sortierung, Filter-Tafel ───
  R.auswahl($("#sortierung"), (w) => { z.sort = w; aktualisieren(); });
  const filter = $("#filter"), schleier = $("#schleier");
  const filterTafel = (auf) => { filter.classList.toggle("offen", auf); schleier.classList.toggle("offen", auf); $("#filter-auf").setAttribute("aria-expanded", String(auf)); };
  $("#filter-auf").addEventListener("click", () => filterTafel(true));
  $("#filter-zu").addEventListener("click", () => filterTafel(false));
  schleier.addEventListener("click", () => filterTafel(false));

  // ─── Ablauf ───
  function adresseSchreiben() {
    const p = new URLSearchParams({ f: "1" });
    for (const g of GRUPPEN) if (z[g].size) p.set(g, [...z[g]].join(","));
    if (z.favoriten) p.set("favoriten", "1"); if (z.stimmen) p.set("stimmen", z.stimmen); if (z.bitrate) p.set("bitrate", z.bitrate);
    if (z.suche) p.set("suche", z.suche); if (z.sort !== "stimmen") p.set("sort", z.sort);
    for (const k of ["thema", "schrift", "vorlage"]) if (adresse.has(k)) p.set(k, adresse.get(k));
    history.replaceState(null, "", `?${p}`);
  }
  function aktualisieren(schreiben = true) {
    const passend = D.SENDER.filter(passt);
    $("#zaehler").setAttribute("text", R.zahl(trefferGesamt(passend)));
    $("#hinweis-zahl").textContent = R.zahl(D.BESTAND.ausgeblendet + z.ausgeblendet.size);
    chips(); liste(passend);
    if (schreiben) adresseSchreiben();
  }

  // ─── Abspielleiste: Sender und Zustände ───
  const K = { kanzel: $("#kanzel"), display: $("#display"), sender: $("#d-sender"), titel: $("#d-titel"), art: $("#d-art"), format: $("#d-format"), dled: $("#d-led"),
    quelle: $("#q-text"), qaktion: $("#q-aktion"), zeit: $("#zeit"), pufferText: $("#puffer-text"), puffer: $("#puffer"), live: $("#knopf-live"), zurueck30: $("#knopf-30"),
    play: $("#t-play"), rec: $("#t-rec"), prev: $("#t-prev"), next: $("#t-next"), stop: $("#t-stop"), haus: $("#haus-geraet"), hausLed: $("#haus-led"), holen: $("#haus-holen"),
    hausText: $("#haus-text"), kSender: $("#k-sender"), kTitel: $("#k-titel"), kPlay: $("#k-play"), navLed: $("#nav-led-aufnahme"), pegel: $$(".rh-laut ak-pegel"), fernBand: $("#fern-hinweis") };
  function spielen(s) {
    z.spielt = s.id;
    K.sender.setAttribute("text", s.name.toUpperCase());
    K.kSender.textContent = s.name;
    K.format.innerHTML = `${R.guete(s.guete)}<span>${R.bitrate(s)}</span>`;
    zustandSetzen(zustandIndex === 6 ? 6 : 2);
  }
  const ZUSTAENDE = [
    { id: "laedt", name: "lädt", quelle: ["LÄDT", "gelb"], led: ["gelb", "blinkt"], art: "VERBINDET", titel: "Verbinde mit dem Sender", zeit: "--:--:--", puffer: 0, play: "fa-play" },
    { id: "puffert", name: "puffert", quelle: ["PUFFER", "gelb"], led: ["gelb", "atmet"], art: "PUFFERT 64 %", titel: "Puffert, gleich geht es weiter", zeit: "00:00:00", puffer: 4, play: "fa-pause" },
    { id: "live", name: "spielt live", quelle: ["LIVE", "blau"], led: ["blau", "an"], art: "LIVE", titel: null, zeit: "00:42:17", puffer: 42, play: "fa-pause" },
    { id: "versatz", name: "zeitversetzt", quelle: ["VERSATZ", "bernstein"], led: ["bernstein", "an"], art: "4:12 HINTER LIVE", titel: null, zeit: "-00:04:12", puffer: 42, play: "fa-pause" },
    { id: "aufnahme", name: "Aufnahme läuft", quelle: ["REC", "rot"], led: ["rot", "blinkt"], art: "AUFNAHME 00:12:48", titel: null, zeit: "00:12:48", puffer: 42, play: "fa-pause", rec: true },
    { id: "fehler", name: "Fehler", quelle: ["FEHLER", "rot"], led: ["rot", "an"], art: "VERBINDUNG VERLOREN", titel: "Neuer Versuch in 5 s", zeit: "--:--:--", puffer: 42, play: "fa-rotate-right", ton: "fehler" },
    { id: "fern", name: "anderes Gerät spielt", quelle: ["FERN", "blau"], led: ["blau", "atmet"], art: "SPIELT AUF TELEFON", titel: null, zeit: "00:42:17", puffer: 42, play: "fa-pause", ton: "fern" },
    { id: "web", name: "Webversion", quelle: ["LIVE", "blau"], led: ["blau", "an"], art: "LIVE", titel: null, zeit: "00:42:17", puffer: 0, play: "fa-pause" },
  ];

  // Fähigkeiten: Teile erscheinen nur, wenn die Ausgabe sie kann (keine toten Knöpfe). Die Webversion (Pages, ohne
  // Dienst) kann Radio, Filter, Regeln und Favoriten im Browser und den Wecker; kein Zeitversatz, keine Aufnahme, keine
  // Übergabe, keine laufenden Titel, keine Podcasts.
  function ausgabeSetzen(art) {
    if ($(".rh-app").dataset.ausgabe === art) return;
    faehig = new Set(FAEHIGKEITEN[art]);
    $(".rh-app").dataset.ausgabe = art;
    $$("[data-braucht]").forEach((el) => { el.hidden = !el.dataset.braucht.split(" ").every((f) => faehig.has(f)); });
    aktualisieren(false);
  }
  let zustandIndex = 2;
  function zustandSetzen(i) {
    zustandIndex = (i + ZUSTAENDE.length) % ZUSTAENDE.length;
    const st = ZUSTAENDE[zustandIndex], s = D.SENDER.find((x) => x.id === z.spielt);
    K.kanzel.dataset.zustand = st.id;
    $("#entwurf-zustand").textContent = `${zustandIndex + 1}/${ZUSTAENDE.length}: ${st.name}`;
    ausgabeSetzen(st.id === "web" ? "web" : "voll");
    K.display.dataset.ton = st.ton || "";
    K.art.textContent = st.art;
    K.dled.setAttribute("farbe", st.led[0]); K.dled.setAttribute("zustand", st.led[1]);
    K.titel.textContent = st.titel ?? s.titel;
    K.kTitel.textContent = st.titel ?? (st.id === "fern" ? `spielt auf Telefon: ${s.titel}` : s.titel);
    K.quelle.setAttribute("text", st.quelle[0]); K.quelle.style.setProperty("--farbe", `var(--led-${st.quelle[1]})`);
    K.zeit.setAttribute("text", st.zeit);
    K.pufferText.textContent = `${st.puffer ? `${Math.round(st.puffer * 30 / 42)}:00` : "0:00"} von 30:00`;
    K.puffer.style.width = `${Math.round((st.puffer / 42) * 100)}%`;
    K.live.disabled = st.id !== "versatz";
    K.zurueck30.disabled = ["laedt", "fehler"].includes(st.id);
    for (const t of [K.play, K.kPlay]) { t.querySelector("i").className = `fa-solid ${st.play}`; t.setzen?.(["live", "versatz", "aufnahme", "fern", "puffert", "web"].includes(st.id)); }
    K.rec.setzen(!!st.rec);
    K.navLed.setAttribute("zustand", st.rec ? "blinkt" : "aus");
    for (const t of [K.prev, K.next]) { t.toggleAttribute("gesperrt", !!st.rec); t.querySelector("ak-led")?.setAttribute("zustand", st.rec ? "an" : "aus"); t.title = st.rec ? "Kein Senderwechsel während der Aufnahme" : t.dataset.hilfe; }
    // Im Glas nur Anzeige (RAD-8): Neu verbinden ist die Spielen-Taste im Fehlerfall, die Bitrate eine Leiste der Steuerung
    K.qaktion.innerHTML = st.id === "laedt" || st.id === "puffert" ? `<div class="balken"><span style="width:${st.id === "laedt" ? 18 : 64}%"></span></div>`
      : st.rec ? `<span title="Kein Senderwechsel während der Aufnahme"><ak-led farbe="bernstein" zustand="an" groesse="klein"></ak-led> WECHSEL GESPERRT</span>`
      : ["live", "versatz"].includes(st.id) ? "PUFFER WIE GESENDET" : "";
    K.play.title = st.id === "fehler" ? "Die Quelle sofort neu laden" : "Hören oder anhalten";
    const fern = st.id === "fern";
    K.haus.textContent = fern ? "Telefon" : "Rechner im Arbeitszimmer";
    K.hausText.textContent = fern ? "Spielt auf" : "Spielt hier:";
    K.hausLed.setAttribute("zustand", fern ? "atmet" : "an");
    K.holen.disabled = !fern; K.holen.classList.toggle("primaer", fern);
    K.fernBand.hidden = !fern;
    K.pegel.forEach((p) => (fern || ["laedt", "fehler"].includes(st.id) ? p.setAttribute("wert", "-60") : p.removeAttribute("wert")));
    $$("#geraete button").forEach((b) => b.classList.toggle("aktiv", b.dataset.wert === (fern ? "telefon" : "rechner")));
  }
  $("#entwurf-vor").addEventListener("click", () => zustandSetzen(zustandIndex + 1));
  $("#entwurf-zurueck").addEventListener("click", () => zustandSetzen(zustandIndex - 1));
  K.holen.addEventListener("click", () => zustandSetzen(2));
  R.auswahl($("#haus-wahl"), (w) => zustandSetzen(w === "rechner" ? 2 : 6));
  $("#kanzel-auf").addEventListener("click", (e) => { const auf = !K.kanzel.classList.contains("offen"); K.kanzel.classList.toggle("offen", auf); e.currentTarget.setAttribute("aria-expanded", String(auf)); e.currentTarget.querySelector("i").className = `fa-solid fa-chevron-${auf ? "down" : "up"}`; });

  // Hördauer zählt im Zustand live weiter
  let sekunden = 42 * 60 + 17;
  setInterval(() => {
    if (!["live", "fern", "aufnahme", "web"].includes(ZUSTAENDE[zustandIndex].id)) return;
    sekunden++;
    const f = (n) => String(n).padStart(2, "0"), t = `${f(Math.floor(sekunden / 3600))}:${f(Math.floor(sekunden / 60) % 60)}:${f(sekunden % 60)}`;
    if (ZUSTAENDE[zustandIndex].id !== "aufnahme") K.zeit.setAttribute("text", t);
  }, 1000);

  // Start, sobald die Instrumente bereit sind
  customElements.whenDefined("ak-segmente").then(() => customElements.whenDefined("ak-dreh")).then(() => {
    facettenBauen();
    $("#suche").value = z.suche;
    if (z.favoriten) taster.setzen(true);
    dreh.wert = z.stimmen; schieber.wert = z.bitrate;
    $$("#sortierung button").forEach((b) => { if (b.dataset.wert === z.sort) { b.classList.add("aktiv"); $("#sortierung .auswahl-text").textContent = b.dataset.titel; } });
    spielen(D.SENDER.find((s) => s.id === z.spielt));
    // Zustand der Leiste aus der Adresse (?zustand=web, aufnahme, fern ...), für Verweise und Bildschirmfotos
    const start = ZUSTAENDE.findIndex((x) => x.id === adresse.get("zustand"));
    if (start >= 0) zustandSetzen(start);
    aktualisieren(!neu);
  });
})();
