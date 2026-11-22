// Podcasts am Telefon im Entwurf RAD-14: hören mit Stelle und Weiterhören, neue Folgen aller Abos zuerst, Abos mit
// Ordnern, ein Abo mit Kopf, das Blatt einer Folge (weiter, von vorn, speichern, herunterladen, gehört), Löschen mit
// Rückfrage, Abonnieren über das Verzeichnis. Dieselben Bausteine wie Radio und Aufnahmen am Telefon.
(() => {
  "use strict";
  const P = window.RHPodcasts, R = window.RH, esc = R.esc;
  const abo = (id) => P.ABOS.find((a) => a.id === id);
  const datum = (d) => {
    const tage = Math.round((new Date(2026, 10, 20) - d) / 86400000);
    return tage === 0 ? "heute" : tage === 1 ? "gestern" : d.toLocaleDateString("de-DE", { day: "numeric", month: "short" });
  };
  const gehoert = (f) => f.stand >= f.laenge;
  const ungehoert = (a) => P.FOLGEN.filter((f) => f.abo === a.id && !gehoert(f)).length;
  const gespeichert = (a) => P.FOLGEN.filter((f) => f.abo === a.id && f.gemerkt).length;
  const folgen = (a) => P.FOLGEN.filter((f) => f.abo === a.id).length;
  const SPIELT = "s1";

  const rahmen = (kopf, inhalt, zusatz = "") => `<div class="t-app t-app-podcasts">
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div>
      <div class="t-luft" aria-hidden="true"></div>
      ${kopf}
      <div class="t-liste">${inhalt}</div>
      <div class="t-spieler" role="button" aria-label="Spieler öffnen">
        <div class="ak-glas"><b>Warum der Himmel nachts dunkel ist</b><span>Sternstunde Physik · 12:40 von 48:00</span></div>
        <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="Anhalten" an></ak-taster>
        <button class="rund" type="button" aria-label="Spieler öffnen" title="Spieler öffnen"><i class="fa-solid fa-chevron-up"></i></button>
      </div>
      <nav class="t-reiter" aria-label="Bereiche"><span><i class="fa-solid fa-radio"></i>Radio</span><span><i class="fa-solid fa-circle-dot"></i>Aufnahmen</span><span class="aktiv"><i class="fa-solid fa-podcast"></i>Podcasts</span></nav>
      ${zusatz}
    </div>`;

  const kopfStart = (wahl) => `<div class="t-kopf"><span class="rh-logo">RadioHub</span><div class="t-kopf-rechts">
      <span class="t-treffer" title="${wahl === "abos" ? "Abos" : "Folgen für die Auswahl, nicht nur die geladenen"}"><ak-segmente art="7" stellen="3" farbe="gruen" text="${wahl === "abos" ? P.ABOS.length : P.FOLGEN.length}"></ak-segmente>${wahl === "abos" ? "Abos" : "Folgen"}</span>
      <button class="rund" type="button" aria-label="Abonnieren" title="Podcast suchen und abonnieren"><i class="fa-solid fa-plus"></i></button></div></div>
    <div class="t-suche tp-suche"><label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input type="search" placeholder="${wahl === "abos" ? "In Abos suchen" : "In Folgen suchen"}" aria-label="Suchen"></label></div>
    <div class="tp-wahl"><div class="segment" role="group" aria-label="Was zeigen">
      ${[["neu", "Neu"], ["ungehoert", "Ungehört"], ["gespeichert", "Gespeichert"], ["abos", "Abos"]].map(([w, n]) =>
        `<button type="button" class="${w === wahl ? "aktiv" : ""}" aria-pressed="${w === wahl}">${n}</button>`).join("")}
    </div></div>`;

  function stand(f) {
    if (gehoert(f)) return `<span class="rh-stand fertig"><i class="fa-solid fa-check"></i>gehört</span>`;
    if (!f.stand) return `<span class="rh-stand neu">neu</span>`;
    return `<span class="rh-stand tp-stand"><span class="balken"><span style="width:${Math.round(f.stand / f.laenge * 100)}%"></span></span>noch ${f.laenge - f.stand} min</span>`;
  }

  function folgeZeile(f, mitAbo = true) {
    const a = abo(f.abo), spielt = f.id === SPIELT;
    const weiter = f.stand && !gehoert(f);
    return `<div class="t-zeile tp-folge${spielt ? " spielt" : ""}${gehoert(f) ? " gehoert" : ""}">
      ${R.logo(a)}
      <div><b>${esc(f.titel)}</b>
        <div class="t-meta">${mitAbo ? `<span>${esc(a.name)}</span>` : ""}<span>${datum(f.datum)}</span><span>${f.laenge} min</span>
          ${f.gemerkt ? `<span class="tp-gespeichert" title="In der Kellerwolke gespeichert"><i class="fa-solid fa-cloud"></i></span>` : ""}</div>
        <div class="tp-stand-zeile">${stand(f)}</div></div>
      <button class="rund" type="button" aria-label="${weiter ? `Weiter ab ${f.stand}:00` : "Hören"}" title="${weiter ? `Weiter ab ${f.stand}:00` : "Hören"}">
        <i class="fa-solid ${spielt ? "fa-volume-high" : weiter ? "fa-forward" : "fa-play"}"></i></button>
    </div>`;
  }

  // 1: neue Folgen aller Abos, neueste zuerst
  function neu(el) {
    const liste = [...P.FOLGEN].sort((a, b) => b.datum - a.datum);
    el.innerHTML = rahmen(kopfStart("neu"), liste.map((f) => folgeZeile(f)).join("") + `<p class="tf-hinweis">Alle 12 geladen</p>`);
  }

  // 2: Abos, nach Ordnern; Zahl ungehört und gespeichert
  function abos(el) {
    const ORDNER = [["Wissen", ["sterne", "zahlen"]], ["Ohne Ordner", ["morgen", "werkstatt", "kueche", "hoerspiel"]]];
    const zeile = (a) => `<div class="t-zeile tp-abo">${R.logo(a)}
      <div><b>${esc(a.name)}</b><div class="t-meta"><span>${esc(a.autor)}</span></div>
        <div class="t-meta">${ungehoert(a) ? `<span class="tp-ungehoert">${ungehoert(a)} ungehört</span>` : `<span>alles gehört</span>`}
          <span><i class="fa-solid fa-cloud"></i> ${gespeichert(a)}/${folgen(a)}</span>${a.auto ? `<span class="tp-auto" title="Speichert neue Folgen von selbst"><i class="fa-solid fa-bolt"></i>neue speichern</span>` : ""}</div></div>
      <button class="rund" type="button" aria-label="Öffnen" title="Öffnen"><i class="fa-solid fa-chevron-right"></i></button></div>`;
    const inhalt = ORDNER.map(([n, ids]) => `<p class="tp-ordner"><i class="fa-solid ${n === "Ohne Ordner" ? "fa-inbox" : "fa-folder"}"></i>${n}</p>${ids.map((id) => zeile(abo(id))).join("")}`).join("");
    el.innerHTML = rahmen(kopfStart("abos"), inhalt + `<p class="tf-hinweis">Nächste Aktualisierung in 2 h 14 min</p>`);
  }

  // 3: ein Abo mit Kopf und Folgen
  const kopfAbo = (a) => `<div class="t-kopf-zurueck tp-kopf"><button class="rund" type="button" aria-label="Zurück" title="Zurück"><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>${esc(a.name)}</b><span class="rh-still">${esc(a.autor)}</span></div></div>`;
  function aboKarte(a) {
    return `<section class="tp-abokopf">
      ${R.logo(a, "gross")}
      <div><p class="rh-still">${esc(a.beschreibung)}</p>
        <div class="t-meta"><span><b>${folgen(a)}</b> Folgen</span><span><b>${ungehoert(a)}</b> ungehört</span><span><i class="fa-solid fa-cloud"></i> <b>${gespeichert(a)}/${folgen(a)}</b> gespeichert</span></div></div>
      <div class="tp-knoepfe">
        <button class="knopf" type="button"><i class="fa-solid fa-rotate"></i>Aktualisieren</button>
        <button class="knopf rh-schalter" type="button" aria-pressed="${a.auto}"><ak-led class="rh-tastenlicht" farbe="gruen" zustand="${a.auto ? "an" : "aus"}"></ak-led>Neue speichern</button>
        <button class="knopf gefahr" type="button"><i class="fa-solid fa-trash-can"></i>Abbestellen</button>
      </div></section>
      <div class="t-chips tp-sort"><span class="rh-still">Sortierung</span>${["Neueste", "Älteste", "Kürzeste"].map((n, i) => `<button type="button" class="chip wahl${i === 0 ? " an" : ""}">${n}</button>`).join("")}</div>`;
  }
  function einAbo(el) {
    const a = abo("sterne");
    el.innerHTML = rahmen(kopfAbo(a), aboKarte(a) + P.FOLGEN.filter((f) => f.abo === a.id).map((f) => folgeZeile(f, false)).join(""));
  }

  // 4 und 5: Blatt einer Folge über dem Abo, einmal mit Aktionen, einmal mit der Rückfrage zum Löschen
  function blatt(f, frage) {
    const a = abo(f.abo), weiter = f.stand && !gehoert(f);
    return `<div class="t-schleier"></div>
      <div class="t-blatt tp-blatt" role="dialog" aria-label="Folge">
        <div class="t-blatt-kopf"><h2>${esc(f.titel)}</h2><button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="t-blatt-rollt">
          <div class="t-meta"><span>${esc(a.name)}</span><span>${datum(f.datum)}</span><span>${f.laenge} min</span>${f.gemerkt ? `<span>${f.mb} MB in der Kellerwolke</span>` : ""}</div>
          <div class="tp-stand-zeile">${stand(f)}</div>
          <p class="tp-text">${esc(f.text)} <button class="knopf still tp-mehr" type="button">Mehr zeigen</button></p>
          ${frage ? `<div class="rueckfrage" role="alertdialog"><span class="frage">Gespeicherte Folge löschen?</span>
              <span>Die Datei Podcasts/${esc(a.name)}/2026-11-11 ${esc(f.titel)}.mp3 (${f.mb} MB) kommt in den Papierkorb der Kellerwolke. Die Folge bleibt im Abo und lässt sich wieder speichern.</span>
              <div class="aktionen"><button class="knopf" type="button">Abbrechen</button><button class="knopf gefahr-voll" type="button"><i class="fa-solid fa-trash-can"></i>Löschen</button></div></div>`
            : `<div class="tp-aktionen">
              <button class="knopf primaer" type="button"><i class="fa-solid ${weiter ? "fa-forward" : "fa-play"}"></i>${weiter ? `Weiter ab ${f.stand}:00` : "Hören"}</button>
              ${weiter ? `<button class="knopf" type="button"><i class="fa-solid fa-backward-step"></i>Von vorn</button>` : ""}
              ${f.gemerkt ? `<button class="knopf rh-schalter" type="button" aria-pressed="true"><ak-led class="rh-tastenlicht" farbe="gruen" zustand="an"></ak-led>Gespeichert</button>`
                : `<button class="knopf rh-schalter" type="button" aria-pressed="false"><ak-led class="rh-tastenlicht" farbe="gruen" zustand="aus"></ak-led>Speichern</button>`}
              <button class="knopf" type="button"><i class="fa-solid fa-download"></i>Herunterladen</button>
              <button class="knopf rh-schalter" type="button" aria-pressed="${gehoert(f)}"><ak-led class="rh-tastenlicht" farbe="gruen" zustand="${gehoert(f) ? "an" : "aus"}"></ak-led>Gehört</button>
            </div>`}
        </div>
      </div>`;
  }
  function folgeBlatt(el) {
    const a = abo("sterne");
    el.innerHTML = rahmen(kopfAbo(a), aboKarte(a) + P.FOLGEN.filter((f) => f.abo === a.id).map((f) => folgeZeile(f, false)).join(""), blatt(P.FOLGEN.find((f) => f.id === "s1"), false));
  }
  function loeschen(el) {
    const a = abo("sterne");
    el.innerHTML = rahmen(kopfAbo(a), aboKarte(a) + P.FOLGEN.filter((f) => f.abo === a.id).map((f) => folgeZeile(f, false)).join(""), blatt(P.FOLGEN.find((f) => f.id === "s2"), true));
  }

  // 6: Abonnieren über das Verzeichnis oder die Adresse eines Feeds
  function abonnieren(el) {
    const kopf = `<div class="t-kopf-zurueck tp-kopf"><button class="rund" type="button" aria-label="Zurück" title="Zurück"><i class="fa-solid fa-chevron-left"></i></button>
        <div><b>Abonnieren</b><span class="rh-still">Verzeichnis durchsuchen oder Adresse eines Feeds</span></div></div>
      <div class="t-suche tp-suche"><label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input type="search" value="stern" aria-label="Podcast suchen"></label></div>`;
    const treffer = P.VERZEICHNIS.map((t) => `<div class="t-zeile tp-abo">${R.logo(t)}
        <div><b>${esc(t.name)}</b><div class="t-meta"><span>${esc(t.autor)}</span><span>${t.herkunft}</span></div></div>
        ${t.abo ? `<span class="tp-abonniert"><i class="fa-solid fa-check"></i>abonniert</span>`
          : `<button class="rund" type="button" aria-label="Abonnieren" title="Abonnieren"><i class="fa-solid fa-plus"></i></button>`}</div>`).join("");
    el.innerHTML = rahmen(kopf, treffer + `<p class="tf-hinweis">Gesucht wird in zwei Verzeichnissen; die Adresse eines Feeds geht auch.</p>`);
  }

  const ZUSTAENDE = { neu, abos, abo: einAbo, folge: folgeBlatt, loeschen, abonnieren };
  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-telefon]").forEach((el) => {
      ZUSTAENDE[el.dataset.telefon](el);
      R.tastenlicht?.(el);
      el.addEventListener("click", (e) => {
        const c = e.target.closest(".chip.wahl, .segment button"); if (!c) return;
        c.parentElement.querySelectorAll(":scope > button").forEach((x) => { x.classList.toggle(c.matches(".chip") ? "an" : "aktiv", x === c); });
      });
    });
  });
})();
