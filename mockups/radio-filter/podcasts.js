// Verhalten des Entwurfs Podcasts am Rechner (RAD-17): Abos in der Seitenleiste wählen (mehrere), Folgen filtern
// (ungehört, gemerkt, Zeitraum), suchen, sortieren, aufklappen, hören, merken, als gehört setzen; ein gewähltes Abo
// zeigt seinen Kopf; Abonnieren sucht im Verzeichnis; "alle merken" zeigt den Fortschritt. Nur Entwurf, Musterdaten.

(() => {
  "use strict";
  const P = window.RHPodcasts, R = window.RH, $ = (s, w = document) => w.querySelector(s);
  const z = {
    abos: new Set(), wahl: "alle", suche: "", sort: "neu",
    offen: new Set(["s1"]), spielt: "s1", verzeichnis: false, verzeichnisSuche: "Stern", merkt: null,
    auto: Object.fromEntries(P.ABOS.map((a) => [a.id, a.auto])),
    folgen: P.FOLGEN.map((f) => ({ ...f })),
  };
  const abo = (id) => P.ABOS.find((a) => a.id === id);
  const minuten = (m) => (m >= 60 ? `${Math.floor(m / 60)} h ${m % 60} min` : `${m} min`);
  const datum = (d) => {
    const tage = Math.round((new Date(2026, 10, 20) - d) / 86400000);
    return tage === 0 ? "heute" : tage === 1 ? "gestern" : d.toLocaleDateString("de-DE", { day: "numeric", month: "short" });
  };
  const gehoert = (f) => f.stand >= f.laenge;
  const ungehoert = (a) => z.folgen.filter((f) => f.abo === a && !gehoert(f)).length;

  // ─── Auswahl ───
  function passend() {
    const q = z.suche.trim().toLowerCase();
    return z.folgen.filter((f) => (!z.abos.size || z.abos.has(f.abo)) && (z.wahl !== "neu" || !gehoert(f)) && (z.wahl !== "gemerkt" || f.gemerkt)
      && (!q || `${f.titel} ${f.text}`.toLowerCase().includes(q)));
  }
  const SORTEN = {
    neu: (a, b) => b.datum - a.datum, alt: (a, b) => a.datum - b.datum,
    titel: (a, b) => a.titel.localeCompare(b.titel, "de"), laenge: (a, b) => a.laenge - b.laenge,
  };

  // ─── Seitenleiste: Abos ───
  function abos() {
    $("#abos").innerHTML = `<label class="rh-facette ohne-kennung"><input type="checkbox" data-abo=""${z.abos.size ? "" : " checked"}><span>Alle Abos</span><span class="rh-zahl" title="ungehört">${z.folgen.filter((f) => !gehoert(f)).length}</span></label>`
      + P.ABOS.map((a) => `<label class="rh-facette rh-abo" draggable="true" title="${R.esc(a.autor)}">
        <span class="rh-griff" aria-hidden="true"><i class="fa-solid fa-grip-vertical"></i></span>
        <input type="checkbox" data-abo="${a.id}"${z.abos.has(a.id) ? " checked" : ""}>${R.logo(a, "klein")}
        <span>${R.esc(a.name)}${z.auto[a.id] ? ` <i class="fa-solid fa-cloud-arrow-down rh-auto" title="Merkt neue Folgen von selbst"></i>` : ""}</span>
        <span class="rh-zahl" title="ungehört">${ungehoert(a.id) || ""}</span></label>`).join("");
  }
  $("#abos").addEventListener("change", (e) => {
    const id = e.target.dataset.abo; if (id === undefined) return;
    if (!id) z.abos.clear(); else e.target.checked ? z.abos.add(id) : z.abos.delete(id);
    z.verzeichnis = false; neu();
  });

  // ─── Kopf eines gewählten Abos ───
  function aboKopf() {
    const el = $("#abo-kopf");
    if (z.abos.size !== 1 || z.verzeichnis) { el.innerHTML = ""; return; }
    const a = abo([...z.abos][0]), fs = z.folgen.filter((f) => f.abo === a.id);
    const laenge = fs.reduce((s, f) => s + f.laenge, 0), gemerkt = fs.filter((f) => f.gemerkt).length;
    el.innerHTML = `<section class="rh-abo-kopf">
      ${R.logo(a, "gross")}
      <div class="rh-abo-text"><h2>${R.esc(a.name)}</h2><p class="rh-still">${R.esc(a.autor)}</p><p>${R.esc(a.beschreibung)}</p>
        <div class="rh-abo-zahlen"><span><b>${fs.length}</b> Folgen</span><span><b>${ungehoert(a.id)}</b> ungehört</span><span><b>${gemerkt}</b> gemerkt</span><span><b>${minuten(laenge)}</b> zusammen</span></div></div>
      <ak-taster id="abo-auto" art="flach" beschriftung="Neue merken" farbe="gruen" ${z.auto[a.id] ? "an" : ""} hilfe="Neue Folgen dieses Abos von selbst im Gerät merken"></ak-taster>
      <div class="rh-detail-knoepfe rh-abo-knoepfe">
        <button class="knopf" type="button" data-aktion="aktualisieren"><i class="fa-solid fa-rotate"></i>Aktualisieren</button>
        <button class="knopf" type="button" data-aktion="alle-merken" ${z.merkt ? "disabled" : ""}><i class="fa-solid fa-download"></i>Alle merken</button>
        <button class="knopf" type="button" data-aktion="abbestellen"><i class="fa-solid fa-trash-can"></i>Abbestellen</button>
      </div>
      ${z.merkt ? `<div class="rh-auftrag"><span>Merke ${z.merkt.fertig} von ${z.merkt.gesamt} Folgen</span>
        <div class="balken"><span style="width:${Math.round(z.merkt.fertig / z.merkt.gesamt * 100)}%"></span></div>
        <button class="knopf" type="button" data-aktion="merken-halt"><i class="fa-solid fa-pause"></i>Anhalten</button><button class="rund" type="button" data-aktion="merken-ab" aria-label="Abbrechen" title="Abbrechen"><i class="fa-solid fa-xmark"></i></button></div>` : ""}
    </section>`;
  }

  // ─── Liste der Folgen ───
  function stand(f) {
    if (gehoert(f)) return `<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>gehört</span>`;
    if (!f.stand) return `<span class="rh-stand neu">neu</span>`;
    return `<span class="rh-stand"><span class="balken"><span style="width:${Math.round(f.stand / f.laenge * 100)}%"></span></span>noch ${f.laenge - f.stand} min</span>`;
  }
  function detail(f) {
    const ab = f.stand && !gehoert(f) ? `Weiter ab ${f.stand}:00` : "Hören";
    return `<div class="rh-detail rh-folge-detail">
      <p>${R.esc(f.text)}</p>
      <div class="rh-detail-knoepfe">
        <button class="knopf primaer" type="button" data-aktion="spielen"><i class="fa-solid fa-play"></i>${ab}</button>
        ${f.stand ? `<button class="knopf" type="button" data-aktion="vorn"><i class="fa-solid fa-backward-fast"></i>Von vorn</button>` : ""}
        <button class="knopf" type="button" data-aktion="gehoert"><i class="fa-solid ${gehoert(f) ? "fa-rotate-left" : "fa-check"}"></i>${gehoert(f) ? "Als ungehört" : "Als gehört"}</button>
        <button class="knopf" type="button" data-aktion="merken"><i class="fa-solid ${f.gemerkt ? "fa-trash-can" : "fa-download"}"></i>${f.gemerkt ? `Freigeben (${f.mb} MB)` : "Im Gerät merken"}</button>
        <a class="knopf still" href="#" data-aktion="zum-abo"><i class="fa-solid fa-podcast"></i>${R.esc(abo(f.abo).name)}</a>
      </div></div>`;
  }
  function zeile(f) {
    const spielt = z.spielt === f.id, offen = z.offen.has(f.id), a = abo(f.abo);
    return `<article class="rh-sender rh-folge${spielt ? " spielt" : offen ? " gewaehlt" : ""}${offen ? " offen" : ""}${gehoert(f) ? " gehoert" : ""}" data-id="${f.id}">
      <div class="rh-sender-kern" data-aktion="spielen">
        ${R.logo(a)}
        <div class="name"><b>${R.esc(f.titel)}</b><div class="meta"><span>${R.esc(a.name)}</span><span>${datum(f.datum)}</span>${f.gemerkt ? `<span class="rh-gemerkt" title="Im Gerät gemerkt, auch ohne Netz"><i class="fa-solid fa-circle-down"></i>gemerkt</span>` : ""}</div></div>
        <div class="stand-zelle">${stand(f)}</div>
        <div class="laenge">${f.laenge} min</div>
        <div class="rh-aktionen rh-folgen-aktionen">
          <button class="rund${f.gemerkt ? " an" : ""}" type="button" data-aktion="merken" aria-pressed="${f.gemerkt}" title="${f.gemerkt ? `Gemerkt (${f.mb} MB): tippen gibt frei` : "Im Gerät merken"}" aria-label="Merken"><i class="fa-solid ${f.gemerkt ? "fa-circle-down" : "fa-download"}"></i></button>
          <button class="rund${gehoert(f) ? " an" : ""}" type="button" data-aktion="gehoert" aria-pressed="${gehoert(f)}" title="${gehoert(f) ? "Gehört: tippen setzt zurück" : "Als gehört setzen"}" aria-label="Gehört"><i class="fa-solid fa-check"></i></button>
          <button class="rund" type="button" data-aktion="details" aria-expanded="${offen}" title="Details" aria-label="Details"><i class="fa-solid fa-chevron-down"></i></button>
        </div>
      </div>
      ${offen ? detail(f) : ""}
    </article>`;
  }
  function verzeichnis() {
    const q = z.verzeichnisSuche.trim().toLowerCase();
    const treffer = P.VERZEICHNIS.filter((t) => !q || `${t.name} ${t.autor}`.toLowerCase().includes(q));
    return `<section class="rh-verzeichnis">
      <div class="rh-verzeichnis-kopf"><h2><i class="fa-solid fa-plus"></i>Abonnieren</h2>
        <label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input id="verzeichnis-suche" type="search" value="${R.esc(z.verzeichnisSuche)}" placeholder="Podcast im Verzeichnis suchen" aria-label="Im Verzeichnis suchen"></label>
        <button class="rund" type="button" data-aktion="verzeichnis-zu" aria-label="Schließen" title="Schließen"><i class="fa-solid fa-xmark"></i></button></div>
      ${treffer.map((t) => `<article class="rh-sender rh-fund"><div class="rh-sender-kern rh-fund-kern">${R.logo(t)}
        <div class="name"><b>${R.esc(t.name)}</b><div class="meta"><span>${R.esc(t.autor)}</span><span class="rh-kennung">${t.herkunft}</span></div></div>
        ${t.abo ? `<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>abonniert</span>` : `<button class="knopf primaer" type="button" data-aktion="abonnieren" data-name="${R.esc(t.name)}"><i class="fa-solid fa-plus"></i>Abonnieren</button>`}
      </div></article>`).join("") || `<div class="rh-ohne-treffer"><i class="fa-solid fa-magnifying-glass"></i><b>Nichts gefunden</b><span>Ein anderes Wort oder die Adresse des Feeds.</span></div>`}
      <p class="rh-still">Gesucht wird in zwei Verzeichnissen; die Adresse eines Feeds geht auch.</p>
    </section>`;
  }
  function liste() {
    $(".rh-folgen-spalten").hidden = z.verzeichnis;
    if (z.verzeichnis) { $("#zeilen").innerHTML = verzeichnis(); return; }
    const fs = passend().sort(SORTEN[z.sort]);
    $("#zeilen").innerHTML = fs.length ? fs.map(zeile).join("") + `<div class="rh-listen-fuss">${fs.length} von ${fs.length} Folgen geladen, weitere laden beim Rollen</div>`
      : `<div class="rh-ohne-treffer"><i class="fa-solid fa-filter-circle-xmark"></i><b>Keine Folgen für diese Auswahl</b><span>Filter lockern oder ein anderes Abo wählen.</span><button class="knopf" type="button" data-aktion="zurueck">Filter zurücksetzen</button></div>`;
    $("#zaehler").setAttribute("text", String(fs.length));
    $("#zaehler-zusatz").textContent = `${fs.filter((f) => !gehoert(f)).length} ungehört`;
  }
  function chips() {
    const c = [];
    z.abos.forEach((id) => c.push(["abo", id, "Abo", abo(id).name]));
    if (z.wahl !== "alle") c.push(["wahl", "", "Folgen", z.wahl === "neu" ? "ungehört" : "gemerkt"]);
    if (z.suche) c.push(["suche", "", "Suche", z.suche]);
    $("#aktiv-chips").innerHTML = c.map(([art, w, name, wert]) => `<span class="chip">${name}: <b>${R.esc(wert)}</b><button type="button" data-art="${art}" data-wert="${w}" aria-label="Filter entfernen" title="Entfernen"><i class="fa-solid fa-xmark"></i></button></span>`).join("")
      || `<span class="rh-leer-chips">Alle Abos, alle Folgen</span>`;
  }
  $("#aktiv-chips").addEventListener("click", (e) => {
    const k = e.target.closest("button[data-art]"); if (!k) return;
    ({ abo: () => z.abos.delete(k.dataset.wert), wahl: () => (z.wahl = "alle"), suche: () => (z.suche = $("#suche").value = "") })[k.dataset.art]();
    neu();
  });

  // ─── Band (Rückgängig) ───
  function band(html) {
    const b = $("#band"); b.innerHTML = html; b.hidden = false;
    clearTimeout(band.uhr); band.uhr = setTimeout(() => (b.hidden = true), 12000);
    b.querySelector("[data-band-zu]")?.addEventListener("click", () => (b.hidden = true));
  }

  // ─── Klicks in der Liste ───
  $("#zeilen").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    const id = k.closest("[data-id]")?.dataset.id, f = z.folgen.find((x) => x.id === id), a = k.dataset.aktion;
    e.preventDefault(); e.stopPropagation();
    if (a === "spielen") { if (e.target.closest(".rh-detail") && k.classList.contains("rh-sender-kern")) return; z.spielt = id; kanzel(f); }
    if (a === "vorn") { f.stand = 0; z.spielt = id; kanzel(f); }
    if (a === "details") z.offen.has(id) ? z.offen.delete(id) : z.offen.add(id);
    if (a === "gehoert") f.stand = gehoert(f) ? 0 : f.laenge;
    if (a === "merken") {
      f.gemerkt = !f.gemerkt; f.mb = f.gemerkt ? Math.round(f.laenge * 0.9) : 0;
      band(`<i class="fa-solid ${f.gemerkt ? "fa-circle-down" : "fa-trash-can"}"></i><span><b>${R.esc(f.titel)}</b> ${f.gemerkt ? "im Gerät gemerkt" : "freigegeben (im Papierkorb der Ablage)"}</span><button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`);
    }
    if (a === "zum-abo") { z.abos = new Set([f.abo]); }
    if (a === "zurueck") { z.abos.clear(); z.wahl = "alle"; z.suche = ""; }
    if (a === "verzeichnis-zu") z.verzeichnis = false;
    if (a === "abonnieren") band(`<i class="fa-solid fa-podcast"></i><span><b>${R.esc(k.dataset.name)}</b> abonniert, die Folgen kommen gleich</span><button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`);
    neu();
  });
  $("#abo-kopf").addEventListener("click", (e) => {
    const k = e.target.closest("[data-aktion]"); if (!k) return;
    const a = abo([...z.abos][0]);
    if (k.dataset.aktion === "alle-merken") { const offen = z.folgen.filter((f) => f.abo === a.id && !f.gemerkt); z.merkt = { gesamt: offen.length || 1, fertig: 0 }; schritt(); }
    if (k.dataset.aktion === "merken-ab") z.merkt = null;
    if (k.dataset.aktion === "abbestellen") band(`<i class="fa-solid fa-trash-can"></i><span><b>${R.esc(a.name)}</b> abbestellt; gemerkte Folgen bleiben in der Ablage</span><button class="knopf primaer" type="button" data-band-zu><i class="fa-solid fa-rotate-left"></i>Rückgängig</button><button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`);
    if (k.dataset.aktion === "aktualisieren") band(`<i class="fa-solid fa-rotate"></i><span><b>${R.esc(a.name)}</b>: keine neuen Folgen</span><button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`);
    neu();
  });
  $("#abo-kopf").addEventListener("input", (e) => {
    if (e.target.id !== "abo-auto") return;
    z.auto[[...z.abos][0]] = !!e.target.an; abos();
  });
  function schritt() {
    if (!z.merkt) return;
    if (z.merkt.fertig >= z.merkt.gesamt) { z.merkt = null; neu(); return; }
    setTimeout(() => { if (!z.merkt) return; z.merkt.fertig += 1; neu(); schritt(); }, 1400);
  }

  // ─── Werkzeugleiste und Seitenleiste ───
  $("#suche").addEventListener("input", (e) => { z.suche = e.target.value; neu(); });
  $("#suche-leeren").addEventListener("click", () => { z.suche = $("#suche").value = ""; neu(); });
  R.auswahl($("#sortierung"), (w) => { z.sort = w; neu(); });
  $("#abonnieren-auf").addEventListener("click", (e) => { e.preventDefault(); z.verzeichnis = true; neu(); });
  $("#aktualisieren").addEventListener("click", () => band(`<i class="fa-solid fa-rotate"></i><span>Alle Abos gefragt: <b>2 neue Folgen</b></span><button class="rund" type="button" data-band-zu aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`));
  $("#folgen-wahl").addEventListener("click", (e) => { const b = e.target.closest("[data-wahl]"); if (!b) return; z.wahl = b.dataset.wahl; neu(); });
  function wahl() { document.querySelectorAll("#folgen-wahl [data-wahl]").forEach((b) => { const an = b.dataset.wahl === z.wahl; b.classList.toggle("aktiv", an); b.setAttribute("aria-pressed", String(an)); }); }
  $("#zeilen").addEventListener("input", (e) => { if (e.target.id === "verzeichnis-suche") { z.verzeichnisSuche = e.target.value; const pos = e.target.selectionStart; liste(); const i = $("#verzeichnis-suche"); i.focus(); i.setSelectionRange(pos, pos); } });
  const filter = $("#filter"), schleier = $("#schleier");
  const tafel = (auf) => { filter.classList.toggle("offen", auf); schleier.classList.toggle("offen", auf); $("#filter-auf").setAttribute("aria-expanded", String(auf)); };
  $("#filter-auf").addEventListener("click", () => tafel(true)); $("#filter-zu").addEventListener("click", () => tafel(false)); schleier.addEventListener("click", () => tafel(false));

  // ─── Abspielleiste mit der Folge ───
  function kanzel(f) {
    const a = abo(f.abo);
    $("#k-sender").textContent = a.name; $("#k-titel").textContent = f.titel;
    $("#d-sender").setAttribute("text", a.name.toUpperCase()); $("#d-titel").textContent = f.titel;
    $("#d-format").textContent = `${f.gemerkt ? "gemerkt" : "aus dem Netz"} · ${f.laenge} min`;
  }

  // ─── Zustände des Entwurfs ───
  const ZUSTAENDE = [
    ["alle Abos", () => { z.abos.clear(); z.verzeichnis = false; z.merkt = null; }],
    ["ein Abo gewählt", () => { z.abos = new Set(["sterne"]); z.verzeichnis = false; z.merkt = null; }],
    ["Abonnieren: Suche im Verzeichnis", () => { z.abos.clear(); z.verzeichnis = true; z.merkt = null; }],
    ["alle merken läuft", () => { z.abos = new Set(["werkstatt"]); z.verzeichnis = false; z.merkt = { gesamt: 2, fertig: 1 }; }],
  ];
  let zustand = 0;
  function zeige(i) { zustand = (i + ZUSTAENDE.length) % ZUSTAENDE.length; ZUSTAENDE[zustand][1](); $("#entwurf-zustand").textContent = `${zustand + 1}/${ZUSTAENDE.length}: ${ZUSTAENDE[zustand][0]}`; neu(); }
  $("#entwurf-zurueck").addEventListener("click", () => zeige(zustand - 1));
  $("#entwurf-vor").addEventListener("click", () => zeige(zustand + 1));

  function neu() { wahl(); abos(); aboKopf(); chips(); liste(); }
  neu();
})();
