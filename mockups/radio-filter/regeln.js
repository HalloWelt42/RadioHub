// Einstellungen > Radio im Entwurf RAD-3: lebende Regeln (an, aus, entfernen mit Rückfrage), neue Regel mit
// Vorschau beim Tippen und Anlegen erst danach, Rückgängig nach jeder Änderung, ausgeblendete Sender seitenweise mit
// Grund und Freigeben, Länderwahl der Seitenleiste getrennt davon. Reiter stehen in der Adresse (?reiter=...).

(() => {
  "use strict";
  const D = window.RHDaten, R = window.RH, $ = (s, w = document) => w.querySelector(s), $$ = (s, w = document) => [...w.querySelectorAll(s)];
  const adresse = new URLSearchParams(location.search);
  const regeln = D.REGELN.map((r) => ({ ...r }));
  let ausgeblendet = D.BESTAND.ausgeblendet;

  // ─── Reiter ───
  function reiter(name) {
    $$(".rh-einst-kopf [data-reiter]").forEach((b) => { const an = b.dataset.reiter === name; b.classList.toggle("aktiv", an); b.setAttribute("aria-selected", String(an)); });
    $$(".rh-reiter").forEach((s) => { s.hidden = s.dataset.inhalt !== name; });
    const p = new URLSearchParams(location.search); p.set("reiter", name); history.replaceState(null, "", `?${p}`);
  }
  $$(".rh-einst-kopf [data-reiter]").forEach((b) => b.addEventListener("click", () => reiter(b.dataset.reiter)));

  // ─── Band mit Rückgängig ───
  let bandUhr;
  function band(text, zurueck) {
    const b = $("#band");
    b.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--led-gruen)"></i><span>${text}</span>${zurueck ? `<button class="knopf primaer" type="button" id="band-zurueck"><i class="fa-solid fa-rotate-left"></i>Rückgängig</button>` : ""}<button class="rund" type="button" id="band-zu" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`;
    b.hidden = false;
    if (zurueck) $("#band-zurueck").onclick = () => { zurueck(); b.hidden = true; };
    $("#band-zu").onclick = () => { b.hidden = true; };
    clearTimeout(bandUhr); bandUhr = setTimeout(() => { b.hidden = true; }, 12000);
  }

  // ─── Lebende Regeln ───
  const text = (r) => r.art === "sprache" ? `Sprache ist ${r.wert} (${r.code})` : r.art === "tag" ? `Genre ist ${r.wert}` : r.wert;
  // Anteil eindeutiger Sender an der Summe der Regeln (Überschneidungen zählen einmal), am Bestand geeicht
  const ueberschneidung = D.BESTAND.ausgeblendet / D.REGELN.filter((r) => r.an).reduce((a, r) => a + r.betroffen, 0);
  function bestand() {
    ausgeblendet = Math.round(regeln.filter((r) => r.an).reduce((a, r) => a + r.betroffen, 0) * ueberschneidung);
    $("#b-aus").setAttribute("text", R.zahl(ausgeblendet));
    $("#b-sichtbar").setAttribute("text", R.zahl(D.BESTAND.gesamt - D.BESTAND.verschwunden - ausgeblendet));
    $("#a-zahl").textContent = R.zahl(ausgeblendet);
  }
  function regelnZeigen() {
    $("#regeln").innerHTML = regeln.map((r) => {
      const a = D.REGEL_ARTEN[r.art];
      return `<div class="rh-regel${r.an ? "" : " aus"}${r.neu ? " neu" : ""}" data-id="${r.id}">
        <span class="rh-regel-art" title="${a.name}"><i class="fa-solid ${a.symbol}"></i></span>
        <span class="rh-regel-text"><b>${R.esc(text(r))}</b><span>${a.name}: ${a.erklaerung}${r.neu ? " · gerade angelegt" : ""}</span></span>
        <span class="rh-regel-zahl"><b>${R.zahl(r.betroffen)}</b>Sender${r.favoriten ? `, ${r.favoriten} Favoriten` : ", 0 Favoriten"}</span>
        <button class="schalter${r.an ? " an" : ""}" type="button" aria-pressed="${r.an}" data-aktion="schalten" aria-label="Regel ${r.an ? "ausschalten" : "einschalten"}" title="${r.an ? "Ausschalten: Sender werden wieder sichtbar" : "Einschalten"}"></button>
        <button class="knopf gefahr" type="button" data-aktion="fragen"><i class="fa-solid fa-trash"></i>Entfernen</button>
        ${r.frage ? `<div class="rueckfrage" role="alertdialog" aria-label="Regel entfernen?"><span class="frage">Regel entfernen? ${r.an ? `${R.zahl(r.betroffen)} Sender werden wieder sichtbar.` : "Sie ist aus; sichtbar ändert sich nichts."} Neue Sender dieser Art erscheinen künftig.</span>
          <span class="aktionen"><button class="knopf gefahr" type="button" data-aktion="entfernen"><i class="fa-solid fa-trash"></i>Endgültig entfernen</button><button class="knopf" type="button" data-aktion="abbrechen">Abbrechen</button></span></div>` : ""}
      </div>`;
    }).join("");
    bestand();
  }
  $("#regeln").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    const r = regeln.find((x) => x.id === k.closest("[data-id]").dataset.id), i = regeln.indexOf(r);
    if (k.dataset.aktion === "schalten") {
      r.an = !r.an; regelnZeigen();
      band(`${R.esc(text(r))} ${r.an ? "an" : "aus"}: ${R.zahl(r.betroffen)} Sender ${r.an ? "ausgeblendet" : "wieder sichtbar"}`, () => { r.an = !r.an; regelnZeigen(); });
      return;
    }
    if (k.dataset.aktion === "fragen") { regeln.forEach((x) => { x.frage = x === r; }); }
    if (k.dataset.aktion === "abbrechen") r.frage = false;
    if (k.dataset.aktion === "entfernen") {
      regeln.splice(i, 1); r.frage = false; regelnZeigen();
      band(`Regel entfernt: ${R.esc(text(r))}`, () => { regeln.splice(i, 0, r); regelnZeigen(); });
      return;
    }
    regelnZeigen();
  });

  // ─── Neue Regel: Art, Eingabe, Vorschau ───
  const ARTEN = ["sprache", "tag", "stimmen", "werbung", "bewertung", "einzeln"];
  let art = adresse.get("art") || "sprache", entwurf = null;
  $("#arten").innerHTML = ARTEN.map((a) => `<button type="button" data-art="${a}"><i class="fa-solid ${D.REGEL_ARTEN[a].symbol}"></i>${D.REGEL_ARTEN[a].name}</button>`).join("");
  $("#arten").addEventListener("click", (e) => { const b = e.target.closest("[data-art]"); if (b) { art = b.dataset.art; feld(); } });

  const STIMMEN = [["unter 1", 1, 1820], ["unter 3", 3, 2640], ["unter 5", 5, 4210], ["unter 10", 10, 7905], ["unter 25", 25, 14320], ["unter 50", 50, 19870], ["unter 100", 100, 25110]];
  const WERBUNG = [["hoch", 214, 0], ["mittel", 890, 3], ["jeder Verdacht", 2310, 24]];
  function suchfeld(platzhalter, wert = "") {
    return `<label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input id="neu-suche" type="search" placeholder="${platzhalter}" aria-label="${platzhalter}" value="${R.esc(wert)}" autocomplete="off"></label><div class="rh-treffer" id="neu-treffer"></div>`;
  }
  function feld() {
    $$("#arten button").forEach((b) => b.classList.toggle("aktiv", b.dataset.art === art));
    entwurf = null; vorschau();
    const f = $("#neu-feld");
    if (art === "sprache") f.innerHTML = suchfeld("Sprache tippen, etwa chin", adresse.get("sprache") || "") + `<p class="rh-neu-feld-hilfe">Exakte Einträge mit Sprachcode; Sender ohne Sprachangabe bleiben sichtbar.</p>`;
    if (art === "tag") f.innerHTML = suchfeld("Genre tippen, etwa schlager") + `<p class="rh-neu-feld-hilfe">Normalisiert: alle Schreibweisen eines Genres zählen zusammen.</p>`;
    if (art === "einzeln") f.innerHTML = suchfeld("Sender suchen") + `<p class="rh-neu-feld-hilfe">Einzelsperren entstehen auch über das Auge in der Senderliste.</p>`;
    if (art === "stimmen") {
      f.innerHTML = `<ak-schieber id="neu-stimmen" art="leuchte" leuchte="bernstein" name="Ausblenden bei Stimmen" hilfe="Sender mit weniger Stimmen ausblenden" raster="${STIMMEN.map((s) => s[0]).join("|")}" wert="1"></ak-schieber><p class="rh-neu-feld-hilfe">Gilt auch für Sender, die später dazukommen; Favoriten bleiben immer sichtbar.</p>`;
      const s = $("#neu-stimmen"); const lesen = () => { const [n, , betroffen] = STIMMEN[s.wert]; entwurf = { art, wert: `weniger als ${n.replace("unter ", "")} Stimmen`, betroffen, favoriten: 0 }; vorschau(); };
      s.addEventListener("input", lesen); customElements.whenDefined("ak-schieber").then(() => requestAnimationFrame(lesen));
    }
    if (art === "werbung") {
      f.innerHTML = `<ak-wahl id="neu-werbung" name="Werbeverdacht ab" hilfe="Stufe des Werbeverdachts aus Messung und eigener Bewertung" optionen="${WERBUNG.map((w) => w[0]).join("|")}" wert="hoch" farbe="bernstein"></ak-wahl><p class="rh-neu-feld-hilfe">Der Cache-Kopf allein zählt nicht mehr als Verdacht.</p>`;
      const w = $("#neu-werbung"); const lesen = () => { const [n, betroffen, favoriten] = WERBUNG.find((x) => x[0] === w.getAttribute("wert")); entwurf = { art, wert: `Werbeverdacht ${n}`, betroffen, favoriten }; vorschau(); };
      w.addEventListener("input", lesen); requestAnimationFrame(lesen);
    }
    if (art === "bewertung") {
      f.innerHTML = `<div class="rh-chips-wahl" id="neu-bewertung">${[["1", "Geht so", 7], ["werbung", "als Werbung markiert", 12], ["2", "Gut", 18]].map(([w, n, z]) => `<button type="button" class="chip wahl" data-wert="${w}" data-zahl="${z}" data-name="${n}">${w === "werbung" ? `<i class="fa-solid fa-rectangle-ad"></i>` : R.sterne(Number(w))}${n}<span class="rh-zahl">${z}</span></button>`).join("")}</div><p class="rh-neu-feld-hilfe">Eigene Bewertungen; "Werbung" fließt zusätzlich in die Werbeerkennung.</p>`;
      $("#neu-bewertung").addEventListener("click", (e) => { const b = e.target.closest("[data-wert]"); if (!b) return; $$("#neu-bewertung .chip").forEach((x) => x.classList.toggle("an", x === b));
        entwurf = { art, wert: `eigene Bewertung ${b.dataset.name}`, betroffen: Number(b.dataset.zahl), favoriten: b.dataset.wert === "2" ? 9 : 0 }; vorschau(); });
    }
    const suche = $("#neu-suche");
    if (suche) { suche.addEventListener("input", treffer); treffer(); }
  }
  function treffer() {
    const q = $("#neu-suche").value.trim().toLowerCase(), ziel = $("#neu-treffer");
    if (!q) { ziel.innerHTML = ""; entwurf = null; vorschau(); return; }
    let liste;
    if (art === "sprache") liste = D.SPRACHEN.filter(([n, c]) => n.toLowerCase().includes(q) || c === q).map(([n, c, z, f]) => ({ wert: n, code: c, betroffen: z, favoriten: f }));
    if (art === "tag") liste = D.GENRE_REGELN.filter(([n]) => n.toLowerCase().includes(q)).map(([n, z, f]) => ({ wert: n, code: "", betroffen: z, favoriten: f }));
    if (art === "einzeln") liste = D.SENDER.filter((s) => s.name.toLowerCase().includes(q)).map((s) => ({ wert: s.name, code: s.land, betroffen: 1, favoriten: s.favorit ? 1 : 0 }));
    liste = liste.filter((t) => !regeln.some((r) => r.art === art && r.wert === t.wert)).slice(0, 6);
    ziel.innerHTML = liste.length ? liste.map((t, i) => `<button type="button" data-i="${i}"><b>${R.esc(t.wert)}${t.code ? ` <span class="rh-kennung">${t.code}</span>` : ""}</b><span class="rh-zahl">${R.zahl(t.betroffen)} Sender</span><span class="fav${t.favoriten ? "" : " null"}">${t.favoriten ? `<i class="fa-solid fa-star"></i> ${t.favoriten} Favoriten` : "0 Favoriten"}</span></button>`).join("")
      : `<p class="rh-neu-feld-hilfe">Kein Eintrag passt; bestehende Regeln stehen oben.</p>`;
    ziel.onclick = (e) => { const b = e.target.closest("[data-i]"); if (!b) return; $$("button", ziel).forEach((x) => x.classList.toggle("aktiv", x === b)); entwurf = { art, ...liste[Number(b.dataset.i)] }; vorschau(); };
    // beim Tippen zeigt die Vorschau gleich den besten Treffer
    if (liste.length) { ziel.firstElementChild.classList.add("aktiv"); entwurf = { art, ...liste[0] }; } else entwurf = null;
    vorschau();
  }
  function vorschau() {
    const stand = $("#v-stand"), zahlEl = $("#v-zahl");
    $("#v-anlegen").disabled = !entwurf; $("#v-verwerfen").disabled = !entwurf;
    if (!entwurf) {
      zahlEl.setAttribute("text", "-----"); stand.textContent = "Bereit";
      $("#v-text").textContent = "Wähle eine Art und tippe; die Folgen stehen hier, bevor etwas geschieht.";
      $("#v-fav").innerHTML = ""; $("#v-beispiele").innerHTML = ""; return;
    }
    zahlEl.setAttribute("text", R.zahl(entwurf.betroffen));
    stand.textContent = entwurf.favoriten ? "Prüfen" : "Bereit";
    $("#v-text").innerHTML = `Sender würden ausgeblendet: <b>${R.esc(text({ ...entwurf }))}</b>`;
    $("#v-fav").innerHTML = entwurf.favoriten
      ? `<span><b>${entwurf.favoriten} Favoriten</b> wären betroffen. Favoriten bleiben sichtbar, sie stehen dann als Ausnahme in der Liste.</span>`
      : `<span>davon <b>0 Favoriten</b></span>`;
    // erfundene, neutrale Beispielnamen passend zur Art und Sprache der Regel
    const BEISPIELE = {
      zh: ["Huanghe Musikfunk", "Radio Changjiang 101,3", "Jinling Klassik"], yue: ["Radio Zhujiang 96,2", "Lingnan Welle", "Kanton Abendfunk"],
      ru: ["Radio Volna 102,4", "Radio Sever 88,0", "Radio Zvezda 97,1"], tr: ["Radyo Dalga 94,2", "Ufuk FM", "Radyo Sahil 101,0"],
      ar: ["Radio Nour 99,5", "Salam FM", "Radio Baraka 92,1"], uk: ["Radio Svitanok 103,1", "Dnipro Welle", "Radio Karpaty"],
    };
    const namen = BEISPIELE[entwurf.code] || ["Beispielsender Nord", "Beispielsender Süd", "Beispielsender West"];
    $("#v-beispiele").innerHTML = entwurf.betroffen > 1 ? `<span>Beispiele aus ${R.zahl(entwurf.betroffen)}:</span>${namen.slice(0, 3).map((n) => `<span><b>${n}</b> · ${R.zahl(80 + n.length * 7)} Stimmen</span>`).join("")}` : "";
  }
  $("#v-verwerfen").addEventListener("click", () => feld());
  $("#v-anlegen").addEventListener("click", () => {
    const r = { id: `n${Date.now()}`, art: entwurf.art, wert: entwurf.wert, code: entwurf.code || "", betroffen: entwurf.betroffen, favoriten: entwurf.favoriten, an: true, neu: true };
    regeln.forEach((x) => { x.neu = false; }); regeln.unshift(r); regelnZeigen(); feld();
    band(`Regel angelegt: ${R.zahl(r.betroffen)} Sender ausgeblendet, davon ${r.favoriten} Favoriten`, () => { regeln.splice(regeln.indexOf(r), 1); regelnZeigen(); });
    $(".rh-einst-rollt").scrollTo({ top: 0, behavior: "smooth" });
  });

  // ─── Ausgeblendete Sender: seitenweise, durchsuchbar, Grund je Sender, Freigeben ───
  const JE_SEITE = 12;
  let seite = 0, grund = "", freigegeben = new Set();
  $("#a-gruende").innerHTML = `<button type="button" data-wert="" data-titel="Alle Gründe" class="aktiv">Alle Gründe</button>`
    + regeln.filter((r) => r.an).map((r) => `<button type="button" data-wert="${r.id}" data-titel="${R.esc(text(r))}">${R.esc(text(r))}<span class="rh-zahl">${R.zahl(r.betroffen)}</span></button>`).join("");
  R.auswahl($("#a-grund"), (w) => { grund = w; seite = 0; ausgeblendeteZeigen(); });
  $("#a-suche").addEventListener("input", () => { seite = 0; ausgeblendeteZeigen(); });
  $("#a-zurueck").addEventListener("click", () => { seite = Math.max(0, seite - 1); ausgeblendeteZeigen(); });
  $("#a-vor").addEventListener("click", () => { seite++; ausgeblendeteZeigen(); });
  function ausgeblendeteZeigen() {
    const q = $("#a-suche").value.trim().toLowerCase();
    const liste = D.AUSGEBLENDET.filter((a) => (!grund || a.regel === grund) && (!q || a.name.toLowerCase().includes(q)));
    const gesamt = q ? liste.length : grund ? D.REGELN.find((r) => r.id === grund).betroffen : ausgeblendet;
    const seiten = Math.max(1, Math.ceil(gesamt / JE_SEITE));
    seite = Math.min(seite, seiten - 1);
    const stueck = Array.from({ length: Math.min(JE_SEITE, Math.max(0, gesamt - seite * JE_SEITE)) }, (_, i) => liste[(seite * JE_SEITE + i) % Math.max(1, liste.length)]).filter(Boolean);
    $("#a-liste").innerHTML = stueck.length ? stueck.map((a, i) => {
      const r = D.REGELN.find((x) => x.id === a.regel), schluessel = `${seite}-${i}`, frei = freigegeben.has(schluessel);
      return `<div class="rh-a-zeile${frei ? " frei" : ""}" role="listitem">${R.logo(a, "klein")}<span class="name"><b>${R.esc(a.name)}</b><span><span class="rh-kennung">${a.land}</span></span></span>
        <span class="grund"><i class="fa-solid ${D.REGEL_ARTEN[r.art].symbol}"></i><span>${R.esc(text(r))}</span></span><span class="stimmen">${R.zahl(a.stimmen)}</span>
        <button class="knopf${frei ? "" : ""}" type="button" data-frei="${schluessel}">${frei ? `<i class="fa-solid fa-rotate-left"></i>Wieder aus` : `<i class="fa-solid fa-eye"></i>Freigeben`}</button></div>`;
    }).join("") : `<div class="rh-ohne-treffer"><i class="fa-solid fa-magnifying-glass"></i><b>Kein ausgeblendeter Sender passt</b></div>`;
    $("#a-seite").textContent = `Seite ${R.zahl(seite + 1)} von ${R.zahl(seiten)}`;
    $("#a-zurueck").disabled = seite === 0; $("#a-vor").disabled = seite >= seiten - 1;
  }
  $("#a-liste").addEventListener("click", (e) => {
    const b = e.target.closest("[data-frei]"); if (!b) return;
    const k = b.dataset.frei, name = b.closest(".rh-a-zeile").querySelector("b").textContent;
    if (freigegeben.has(k)) freigegeben.delete(k); else { freigegeben.add(k); band(`${R.esc(name)} freigegeben: als Ausnahme wieder sichtbar`, () => { freigegeben.delete(k); ausgeblendeteZeigen(); }); }
    ausgeblendeteZeigen();
  });

  // ─── Länder der Seitenleiste ───
  const LAENDER_ALLE = [["DE", "Deutschland", 5419], ["US", "USA", 7824], ["FR", "Frankreich", 2447], ["GB", "Großbritannien", 2086], ["NL", "Niederlande", 1256], ["CH", "Schweiz", 1034],
    ["AT", "Österreich", 812], ["IT", "Italien", 1624], ["ES", "Spanien", 1588], ["PL", "Polen", 1290], ["BE", "Belgien", 610], ["DK", "Dänemark", 402], ["SE", "Schweden", 538],
    ["NO", "Norwegen", 311], ["CZ", "Tschechien", 402], ["GR", "Griechenland", 734], ["PT", "Portugal", 498], ["IE", "Irland", 287], ["CA", "Kanada", 1402], ["AU", "Australien", 1954]];
  const gewaehlt = new Set(["DE", "US", "FR", "GB", "NL", "CH", "AT"]);
  function laenderZeigen() {
    const q = $("#l-suche").value.trim().toLowerCase();
    $("#laender").innerHTML = LAENDER_ALLE.filter(([c, n]) => !q || n.toLowerCase().includes(q) || c.toLowerCase() === q).sort((a, b) => b[2] - a[2])
      .map(([c, n, z]) => `<label class="rh-facette"><input type="checkbox" value="${c}"${gewaehlt.has(c) ? " checked" : ""}><span class="rh-kennung">${c}</span><span>${n}</span><span class="rh-zahl">${R.zahl(z)}</span></label>`).join("");
    $("#l-zahl").textContent = String(gewaehlt.size);
  }
  $("#l-suche").addEventListener("input", laenderZeigen);
  $("#laender").addEventListener("change", (e) => { const k = e.target; k.checked ? gewaehlt.add(k.value) : gewaehlt.delete(k.value); $("#l-zahl").textContent = String(gewaehlt.size); });

  customElements.whenDefined("ak-segmente").then(() => {
    regelnZeigen(); feld(); ausgeblendeteZeigen(); laenderZeigen();
    reiter(["regeln", "ausgeblendet", "laender"].includes(adresse.get("reiter")) ? adresse.get("reiter") : "regeln");
  });
})();
