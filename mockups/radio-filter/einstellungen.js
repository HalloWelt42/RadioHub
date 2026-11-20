// Entwurf RAD-11: Einstellungen aller Bereiche im Stil des abgenommenen Radio-Entwurfs (regeln.html; dessen drei Reiter
// verweisen hierher und zurück). Bereich und Reiter
// stehen in der Adresse (?bereich=...&reiter=...). Werte "für alle Geräte" sammeln sich in der Leiste Speichern (wie
// der Einstellungsbaustein des Appkerns: Punkt am geänderten Wert, Verwerfen, Speichern); Werte "nur dieses Gerät"
// gelten sofort. Löschen fragt immer vorher und nennt die Folgen.

(() => {
  "use strict";
  const E = window.RHEinstellungen, R = window.RH, $ = (s, w = document) => w.querySelector(s), $$ = (s, w = document) => [...w.querySelectorAll(s)];
  const esc = R.esc;
  const adresse = new URLSearchParams(location.search);
  let bereich = E.BEREICHE.find((b) => b.id === adresse.get("bereich")) ?? E.BEREICHE[0];
  let reiter = bereich.reiter.find((r) => r.id === adresse.get("reiter") && !r.verweis) ?? bereich.reiter.find((r) => !r.verweis);

  /** geänderte Werte für alle Geräte, bis Speichern: Schlüssel -> { zeile, wert } */
  const entwurf = new Map();
  const ordner = E.AUFNAHMEORDNER.map((o) => ({ ...o }));
  const muster = E.MUSTER.map((m) => ({ ...m }));
  const kategorien = E.KATEGORIEN.map((k) => ({ ...k }));
  let frage = null;                     // offene Rückfrage: { art, id }

  const SCHRIFT = ["Normal", "Groß", "Sehr groß"];
  const schluessel = (z) => `${bereich.id}.${z.name}`;

  // ─── Bereiche links ───
  function bereicheZeigen() {
    $("#bereiche").innerHTML = E.BEREICHE.map((b) => {
      const ziel = `?bereich=${b.id}`;
      return `<a href="${ziel}" data-bereich="${b.id}" class="${b === bereich ? "aktiv" : ""}"${b === bereich ? ' aria-current="page"' : ""}><i class="fa-solid ${b.symbol}"></i>${esc(b.titel)}</a>`;
    }).join("");
  }
  $("#bereiche").addEventListener("click", (e) => {
    const a = e.target.closest("a[data-bereich]");
    if (!a) return;
    e.preventDefault();
    bereich = E.BEREICHE.find((b) => b.id === a.dataset.bereich);
    reiter = bereich.reiter.find((r) => !r.verweis);
    alles();
  });

  // ─── Reiter oben ───
  function reiterZeigen() {
    $("#pfad-bereich").textContent = bereich.titel;
    const sichtbar = bereich.reiter.length > 1;
    $("#reiter").hidden = !sichtbar;
    $("#reiter").setAttribute("aria-label", bereich.titel);
    $("#reiter").innerHTML = sichtbar ? bereich.reiter.map((r) => r.verweis
      ? `<a role="tab" href="${r.verweis}" class="rh-reiter-verweis">${r.symbol ? `<i class="fa-solid ${r.symbol}"></i>` : ""}${esc(r.titel)}</a>`
      : `<button type="button" role="tab" data-reiter="${r.id}" class="${r === reiter ? "aktiv" : ""}" aria-selected="${r === reiter}">${r.symbol ? `<i class="fa-solid ${r.symbol}"></i>` : ""}${esc(r.titel)}</button>`).join("") : "";
    const p = new URLSearchParams(); p.set("bereich", bereich.id); if (sichtbar) p.set("reiter", reiter.id);
    history.replaceState(null, "", `?${p}`);
  }
  $("#reiter").addEventListener("click", (e) => {
    const b = e.target.closest("button[data-reiter]"); if (!b) return;
    reiter = bereich.reiter.find((r) => r.id === b.dataset.reiter);
    alles();
  });

  // ─── Zeilen einfacher Werte ───
  function geltung(z) {
    if (z.fest) return `<span class="rh-geltung fest" title="Vom Ausrollen gesetzt, hier nicht änderbar"><i class="fa-solid fa-lock"></i>Fest gesetzt</span>`;
    return z.geltung === "alle"
      ? `<span class="rh-geltung alle" title="Gilt für alle Geräte; speichern über die Leiste unten"><i class="fa-solid fa-house"></i>Alle Geräte</span>`
      : `<span class="rh-geltung geraet" title="Gilt sofort und nur auf diesem Gerät"><i class="fa-solid fa-display"></i>Dieses Gerät</span>`;
  }

  function wertVon(z) { return entwurf.has(schluessel(z)) ? entwurf.get(schluessel(z)).wert : z.wert; }

  function bedienung(z) {
    const w = wertVon(z), k = esc(schluessel(z)), gesperrt = z.fest ? " gesperrt" : "";
    switch (z.art) {
      case "schalter":
        return `<ak-taster art="flach" beschriftung="${w ? "An" : "Aus"}" farbe="gruen" data-k="${k}"${w ? " an" : ""}${gesperrt} hilfe="${esc(z.name)}"></ak-taster>`;
      case "zahl":
        return `<ak-schieber art="balken" leuchte="gruen" segmente="8" data-k="${k}" name="${esc(z.name)}" min="${z.min}" max="${z.max}" schritt="${z.schritt}" einheit="${esc(z.einheit)}" wert="${w}"${gesperrt}></ak-schieber>`;
      case "wahl": case "mehrfach":
        return `<div class="segment" role="group" aria-label="${esc(z.name)}" data-k="${k}" data-art="${z.art}">${z.optionen.map(([v, t, s]) => {
          const an = z.art === "mehrfach" ? w.includes(v) : w === v;
          return `<button type="button" data-wert="${v}" class="${an ? "aktiv" : ""}" aria-pressed="${an}">${s ? `<i class="fa-solid ${s}"></i>` : ""}${esc(t)}</button>`;
        }).join("")}</div>`;
      case "sprache": {
        const name = E.SPRACHEN.find(([c]) => c === w)?.[1] ?? w;
        return `<div class="auswahl rh-sprachwahl" data-k="${k}"><button class="auswahl-knopf" type="button" aria-haspopup="listbox"><i class="fa-solid fa-language"></i><span class="auswahl-text">${esc(name)}</span><i class="fa-solid fa-chevron-down auswahl-pfeil"></i></button>
          <div class="auswahl-liste" role="listbox">${E.SPRACHEN.map(([c, t]) => `<button type="button" role="option" data-wert="${c}" data-titel="${esc(t)}" class="${c === w ? "aktiv" : ""}">${esc(t)}</button>`).join("")}</div></div>`;
      }
      case "schrift":
        return `<div class="rh-schrift-wahl" data-k="${k}"><button class="knopf" type="button" data-schritt="-1" aria-label="Schrift kleiner" title="Schrift kleiner"${w <= 0 ? " disabled" : ""}><i class="fa-solid fa-minus"></i></button>
          <output>${SCHRIFT[w]}</output><button class="knopf" type="button" data-schritt="1" aria-label="Schrift größer" title="Schrift größer"${w >= SCHRIFT.length - 1 ? " disabled" : ""}><i class="fa-solid fa-plus"></i></button></div>`;
      case "uhrzeit":
        return uhrzeitFeld(k, w, z.leerErlaubt);
      case "zeitraum":
        return `<span class="rh-zeitraum">${uhrzeitFeld(`${k}.von`, w[0], true, "von")}<span>bis</span>${uhrzeitFeld(`${k}.bis`, w[1], true, "bis")}</span>`;
      case "text":
        return `<span class="rh-e-text-wert"><label class="suche rh-e-eingabe"><i class="fa-solid fa-link"></i><input type="text" value="${esc(w)}" data-k="${k}" spellcheck="false" aria-label="${esc(z.name)}"${z.fest ? " disabled" : ""}></label>${vorgabe(z)}</span>`;
      case "liste":
        return `<div class="rh-e-liste" data-k="${k}">${w.map((x, i) => `<span class="rh-e-listeneintrag"><span>${esc(x)}</span><button class="rund" type="button" data-weg="${i}" aria-label="${esc(x)} entfernen" title="Entfernen"><i class="fa-solid fa-xmark"></i></button></span>`).join("")}
          ${w.length ? "" : `<span class="rh-still">Leer</span>`}
          <span class="rh-e-neu"><label class="suche rh-e-eingabe"><i class="fa-solid fa-plus"></i><input type="text" placeholder="Adresse hinzufügen" spellcheck="false" aria-label="${esc(z.name)}: Adresse hinzufügen"></label>${vorgabe(z)}</span></div>`;
      default: return "";
    }
  }

  function vorgabe(z) { return z.vorgabeKnopf ? `<button class="knopf still" type="button" data-vorgabe="${esc(schluessel(z))}" title="Zurück auf die Vorgabe; fragt vorher"><i class="fa-solid fa-rotate-left"></i>Vorgabe</button>` : ""; }

  /** eigenes Uhrzeitfeld (nie das native, das ist amerikanisch): Stunde und Minute als Auswahl */
  function uhrzeitFeld(k, w, leer, wort = "") {
    const [h, m] = w ? w.split(":") : ["", ""];
    const stunden = [...Array(24)].map((_, i) => String(i).padStart(2, "0")), minuten = ["00", "15", "30", "45"];
    const knopf = (teil, wert, werte) => `<div class="auswahl rh-uhr-teil" data-k="${k}" data-teil="${teil}"><button class="auswahl-knopf" type="button" aria-label="${wort} ${teil === "h" ? "Stunde" : "Minute"}"><span class="auswahl-text">${wert || "--"}</span><i class="fa-solid fa-chevron-down auswahl-pfeil"></i></button>
      <div class="auswahl-liste" role="listbox">${leer ? `<button type="button" data-wert="" data-titel="--">leer</button>` : ""}${werte.map((x) => `<button type="button" data-wert="${x}" data-titel="${x}" class="${x === wert ? "aktiv" : ""}">${x}</button>`).join("")}</div></div>`;
    return `<span class="rh-uhr">${knopf("h", h, stunden)}<b>:</b>${knopf("m", m, minuten)}</span>`;
  }

  function zeile(z) {
    const geaendert = entwurf.has(schluessel(z));
    return `<div class="rh-e-zeile${z.art === "liste" || z.art === "text" ? " breit" : ""}${z.fest ? " fest" : ""}" data-zeile="${esc(schluessel(z))}">
      <div class="rh-e-beschreibung"><div class="rh-e-name">${geaendert ? `<span class="einstellung-punkt" title="Geändert, noch nicht gespeichert"></span>` : ""}<b>${esc(z.name)}</b>${geltung(z)}</div>
        <p>${esc(z.erklaerung)}${z.pruefung ? ` <span class="rh-e-pruefung">${esc(z.pruefung)}</span>` : ""}</p></div>
      <div class="rh-e-wert">${bedienung(z)}</div></div>`;
  }

  function karte(k) {
    return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid ${k.symbol}"></i>${esc(k.titel)}</h2>${k.verweis ? `<a class="knopf" href="#" onclick="return false"><i class="fa-solid ${k.verweis[1]}"></i>${esc(k.verweis[0])}</a>` : ""}</div>
      ${k.hinweis ? `<p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>${esc(k.hinweis)}</span></p>` : ""}
      ${k.teil ? teil(k.teil) : ""}
      ${k.zeilen ? `<div class="rh-e-zeilen">${k.zeilen.map(zeile).join("")}</div>` : ""}</div>`;
  }

  // ─── Sonderteile ───
  function rueckfrage(text, knopf, art, id) {
    return `<div class="rueckfrage" role="alertdialog" aria-label="${esc(knopf)}?"><span class="frage">${text}</span><span class="aktionen">
      <button class="knopf" type="button" data-abbrechen>Abbrechen</button><button class="knopf gefahr" type="button" data-ja="${art}" data-id="${id}"><i class="fa-solid fa-trash"></i>${esc(knopf)}</button></span></div>`;
  }
  const gefragt = (art, id) => frage && frage.art === art && String(frage.id) === String(id);

  function teil(name) {
    switch (name) {
      case "tastatur":
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-keyboard"></i>Tastenkürzel</h2><span class="rh-still">abgeleitet aus der wirksamen Tastenbelegung, nicht von Hand gepflegt</span></div>
          <div class="rh-tasten">${E.TASTEN.map((g) => `<section><h3>${esc(g.gruppe)}</h3><dl>${g.tasten.map(([t, w]) => `<dt>${t.split("|").map((x) => `<kbd>${esc(x)}</kbd>`).join(" ")}</dt><dd>${esc(w)}</dd>`).join("")}</dl></section>`).join("")}</div></div>`;
      case "ueber":
        return ["Technische Informationen", "Lizenz", "Datenschutz und Nutzungsbedingungen"].map((t, i) => `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid ${["fa-microchip", "fa-scale-balanced", "fa-shield-halved"][i]}"></i>${t}</h2></div>
          <div class="rh-langtext"><p class="gekuerzt">${[
            "RadioHub spielt Sender aus dem freien Senderverzeichnis, puffert sie für Zeitversatz und Aufnahme und legt Aufnahmen und Podcast-Folgen in der Kellerwolke ab. Die Oberfläche läuft im Browser, der Dienst auf dem Rechner im Haus. Qualität und Werbeerkennung misst RadioHub selbst; die Zeichen in der Senderliste erklären sich im Hover.",
            "RadioHub steht unter einer Lizenz für private, nicht kommerzielle Nutzung. Weitergabe mit Hinweis auf die Herkunft ist erlaubt, Verkauf und Einbau in kommerzielle Angebote nicht. Der volle Wortlaut folgt hier.",
            "RadioHub speichert nur, was du selbst einstellst, auf deinem eigenen Rechner und in deiner Kellerwolke. Es gibt keine Werbung, keine Zählung und keine Weitergabe an Dritte. Die Nutzungsbedingungen regeln den Betrieb im eigenen Netz.",
          ][i]}</p><button class="knopf still rh-mehr" type="button"><i class="fa-solid fa-chevron-down"></i>Mehr zeigen</button></div></div>`).join("");
      case "bedanken":
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-heart"></i>Bedanken</h2></div>
          <p class="rh-still">RadioHub ist privat und ohne Werbung. Wer etwas zurückgeben möchte:</p>
          <div class="rh-dank"><a class="knopf primaer" href="#" onclick="return false"><i class="fa-solid fa-mug-hot"></i>Spendenseite öffnen</a>
          ${["BTC", "DOGE", "ETH"].map((c) => `<button class="knopf" type="button"><i class="fa-solid fa-qrcode"></i>${c}</button>`).join("")}</div></div>`;
      case "kategorien":
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-folder"></i>Kategorien</h2><span class="rh-still">eigene Sammlungen von Sendern; in der Seitenleiste wählbar</span></div>
          <div class="rh-regeln rh-feste" style="--aktion: calc(var(--gross) * 8.5); --weg: calc(var(--gross) * 7)">${kategorien.map((k) => `<div class="rh-regel" data-id="${k.id}"><ak-led farbe="gelb" zustand="${k.sender ? "an" : "aus"}" groesse="klein"></ak-led>
            <span class="rh-regel-art"><i class="fa-solid fa-folder"></i></span><span class="rh-regel-text"><b>${esc(k.name)}</b><span>${k.sender ? `${k.sender} Sender` : "noch leer"}</span></span>
            <span class="rh-regel-zahl"><b>${k.sender}</b>Sender</span>
            <button class="knopf rh-regel-aktion" type="button" title="Umbenennen"><i class="fa-solid fa-pen"></i>Umbenennen</button>
            <button class="knopf gefahr" type="button" data-fragen="kategorie" data-id="${k.id}"><i class="fa-solid fa-trash"></i>Löschen</button>
            ${gefragt("kategorie", k.id) ? rueckfrage(`Kategorie "${esc(k.name)}" löschen? ${k.sender ? `Die Zuordnung von ${k.sender} Sendern geht mit. Die Sender selbst bleiben, Favoriten auch.` : "Sie ist leer, es geht keine Zuordnung verloren."}`, "Löschen", "kategorie", k.id) : ""}</div>`).join("")}</div>
          <div class="rh-e-neu-zeile"><label class="suche rh-e-eingabe"><i class="fa-solid fa-folder-plus"></i><input type="text" placeholder="Neue Kategorie, etwa Abends" aria-label="Neue Kategorie"></label><button class="knopf primaer" type="button"><i class="fa-solid fa-plus"></i>Anlegen</button></div></div>`;
      case "aufnahmeordner": {
        const aktiv = ordner.find((o) => o.aktiv);
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-folder-tree"></i>Aufnahmeordner</h2><span class="rh-still">neue Aufnahmen landen im Ordner mit Licht</span></div>
          <div class="rh-regeln rh-feste" style="--aktion: calc(var(--gross) * 11); --weg: 94px">
            <div class="rh-regel${aktiv ? " aus" : ""}"><ak-led farbe="rot" zustand="${aktiv ? "aus" : "an"}" groesse="klein"></ak-led><span class="rh-regel-art"><i class="fa-solid fa-house"></i></span>
              <span class="rh-regel-text"><b>Stammordner</b><span>ohne eigenen Ordner, direkt unter Aufnahmen</span></span><span class="rh-regel-zahl"><b>${E.STAMM_AUFNAHMEN}</b>Aufnahmen</span>
              <button class="knopf rh-regel-aktion" type="button" data-aktiv="0"${aktiv ? "" : " disabled"}><i class="fa-solid fa-circle-dot"></i>${aktiv ? "Hierhin aufnehmen" : "Nimmt auf"}</button></div>
            ${ordner.map((o) => `<div class="rh-regel${o.aktiv ? "" : " aus"}" data-id="${o.id}"><ak-led farbe="rot" zustand="${o.aktiv ? "an" : "aus"}" groesse="klein"></ak-led><span class="rh-regel-art"><i class="fa-solid fa-folder"></i></span>
              <span class="rh-regel-text"><b>${esc(o.name)}</b><span>${o.aktiv ? "neue Aufnahmen landen hier" : "Ordner"}</span></span><span class="rh-regel-zahl"><b>${o.aufnahmen}</b>Aufnahmen</span>
              <button class="knopf rh-regel-aktion" type="button" data-aktiv="${o.id}"${o.aktiv ? " disabled" : ""}><i class="fa-solid fa-circle-dot"></i>${o.aktiv ? "Nimmt auf" : "Hierhin aufnehmen"}</button>
              <span class="rh-e-zeilenknoepfe"><button class="rund" type="button" title="Umbenennen" aria-label="${esc(o.name)} umbenennen"><i class="fa-solid fa-pen"></i></button><button class="rund" type="button" title="Löschen" aria-label="${esc(o.name)} löschen" data-fragen="ordner" data-id="${o.id}"><i class="fa-solid fa-trash"></i></button></span>
              ${gefragt("ordner", o.id) ? (o.aufnahmen ? `<p class="hinweis-band rh-e-gesperrt"><i class="fa-solid fa-lock"></i><span>"${esc(o.name)}" enthält ${o.aufnahmen} Aufnahmen und lässt sich erst löschen, wenn er leer ist. Aufnahmen verschiebt man in Aufnahmen.</span><button class="knopf" type="button" data-abbrechen>Verstanden</button></p>`
                : rueckfrage(`Ordner "${esc(o.name)}" löschen? Er ist leer; es geht keine Aufnahme verloren.`, "Löschen", "ordner", o.id)) : ""}</div>`).join("")}</div>
          <div class="rh-e-neu-zeile"><label class="suche rh-e-eingabe"><i class="fa-solid fa-folder-plus"></i><input type="text" placeholder="Neuer Ordner, etwa Hörspiele" aria-label="Neuer Ordner"></label><button class="knopf primaer" type="button"><i class="fa-solid fa-plus"></i>Anlegen</button></div></div>`;
      }
      case "muster":
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-ban"></i>Titel ignorieren</h2><span class="rh-still">diese Titel im Strom teilen eine Aufnahme nicht in Stücke</span></div>
          <div class="rh-regeln rh-feste" style="--aktion: 0px; --weg: calc(var(--gross) * 8)">${muster.map((m) => `<div class="rh-regel" data-id="${m.id}"><ak-led farbe="gelb" zustand="an" groesse="klein"></ak-led><span class="rh-regel-art" title="${m.art === "exakt" ? "Genau dieser Titel" : "Titel enthält"}"><i class="fa-solid ${m.art === "exakt" ? "fa-equals" : "fa-magnifying-glass"}"></i></span>
            <span class="rh-regel-text"><b>${esc(m.muster)}</b><span>${m.art === "exakt" ? "genau dieser Titel" : "Titel enthält"}${m.eingebaut ? " · eingebaut" : " · eigenes Muster"}</span></span>
            <span class="rh-regel-zahl"><b>${m.treffer}</b>Treffer</span>
            ${m.eingebaut ? `<span class="rh-geltung fest" title="Eingebaute Muster bleiben; man kann sie nicht löschen"><i class="fa-solid fa-lock"></i>Eingebaut</span>`
              : `<button class="knopf gefahr" type="button" data-fragen="muster" data-id="${m.id}"><i class="fa-solid fa-trash"></i>Entfernen</button>`}
            ${gefragt("muster", m.id) ? rueckfrage(`Muster "${esc(m.muster)}" entfernen? Künftig teilt dieser Titel Aufnahmen wieder in Stücke (zuletzt ${m.treffer} Treffer). Bestehende Aufnahmen ändern sich nicht.`, "Entfernen", "muster", m.id) : ""}</div>`).join("")}</div>
          <div class="rh-e-neu-zeile"><label class="suche rh-e-eingabe"><i class="fa-solid fa-plus"></i><input type="text" placeholder="Titel, etwa Verkehrsfunk" aria-label="Neues Muster"></label>
            <div class="segment" role="group" aria-label="Art des Musters"><button type="button" class="aktiv" aria-pressed="true"><i class="fa-solid fa-equals"></i>Genau</button><button type="button" aria-pressed="false"><i class="fa-solid fa-magnifying-glass"></i>Enthält</button></div>
            <button class="knopf primaer" type="button"><i class="fa-solid fa-plus"></i>Hinzufügen</button></div></div>`;
      case "stimme":
        return `<div class="rh-e-zeilen"><div class="rh-e-zeile"><div class="rh-e-beschreibung"><div class="rh-e-name"><b>Zeit-Stimme</b>${geltung({ geltung: "alle" })}</div>
            <p>Stimme der Zeitansage aus der Vertonung. Jede Stimme spricht ihre eigenen Bausteine; nach einem Wechsel fehlen sie, bis sie erzeugt sind.</p></div>
          <div class="rh-e-wert"><div class="auswahl" data-k="stimme"><button class="auswahl-knopf" type="button"><i class="fa-solid fa-microphone-lines"></i><span class="auswahl-text">Sohee</span><i class="fa-solid fa-chevron-down auswahl-pfeil"></i></button>
            <div class="auswahl-liste" role="listbox">${E.STIMMEN.map(([v, t], i) => `<button type="button" data-wert="${v}" data-titel="${esc(t)}" class="${i ? "" : "aktiv"}">${esc(t)}</button>`).join("")}</div></div>
            <button class="knopf" type="button" title="Hörprobe der Stimme"><i class="fa-solid fa-play"></i>Hörprobe</button></div></div>
          <div class="rh-e-zeile"><div class="rh-e-beschreibung"><div class="rh-e-name"><b>Bausteine der Zeitansage</b></div><p>Gesprochene Uhrzeiten dieser Stimme, abgelegt in der Kellerwolke.</p></div>
          <div class="rh-e-wert rh-bausteine"><ak-segmente art="7" stellen="4" farbe="gruen" text="${E.BAUSTEINE.vorhanden}"></ak-segmente><span class="rh-still">von ${R.zahl(E.BAUSTEINE.gesamt)} vorhanden</span>
            <button class="knopf" type="button" disabled title="Alle Bausteine sind da"><i class="fa-solid fa-wand-magic-sparkles"></i>Erzeugen</button></div></div></div>`;
      case "ort":
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-location-dot"></i>Ort der Sonnenzeiten</h2>${geltung({ geltung: "alle" })}<span class="rh-still">für die Nachtschaltung der Weckansicht</span></div>
          <div class="rh-ort">
            <div class="rh-ort-suche"><label class="suche" role="search"><i class="fa-solid fa-magnifying-glass"></i><input type="search" value="Hannover" placeholder="Stadt suchen" aria-label="Stadt suchen"></label><button class="knopf" type="button"><i class="fa-solid fa-magnifying-glass"></i>Suchen</button>
              <button class="knopf" type="button"><i class="fa-solid fa-location-crosshairs"></i>Standort dieses Geräts</button></div>
            <div class="rh-ort-treffer" data-ort>${[["Hannover", "Niedersachsen, Deutschland", "52,3744", "9,7386"], ["Hann. Münden", "Niedersachsen, Deutschland", "51,4167", "9,6500"]].map(([n, w, b, l], i) => `<button type="button" class="${i ? "" : "aktiv"}"><b>${n}</b><span>${w}</span><span class="rh-zahl">${b} · ${l}</span></button>`).join("")}</div>
            <div class="rh-ort-felder" data-ort>
              <label><span class="ak-etikett">Name</span><span class="suche"><input type="text" value="Hannover" aria-label="Name des Orts"></span></label>
              <label><span class="ak-etikett">Breite</span><span class="suche"><input type="text" value="52,3744" inputmode="decimal" aria-label="Breite"></span></label>
              <label><span class="ak-etikett">Länge</span><span class="suche"><input type="text" value="9,7386" inputmode="decimal" aria-label="Länge"></span></label>
            </div>
            <div class="ak-geraet rh-sonne" data-bauform="inspektor"><span class="ak-schraube lo" style="--dreh:20deg"></span><span class="ak-schraube ro" style="--dreh:-40deg"></span>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text="07:48"></ak-segmente><span class="ak-etikett">Sonnenaufgang heute</span></div>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="rot" text="16:22"></ak-segmente><span class="ak-etikett">Sonnenuntergang heute</span></div></div>
          </div></div>`;
      case "ablage": {
        const a = E.ABLAGE, anteil = (x) => Math.max(2, Math.round((x / (a.belegt + a.frei)) * 100));
        return `<div class="karte rh-karte"><div class="rh-karte-kopf"><h2><i class="fa-solid fa-hard-drive"></i>Datenordner</h2><span class="rh-geltung fest"><i class="fa-solid fa-lock"></i>Vom Ausrollen gesetzt</span></div>
          <p class="hinweis-band"><i class="fa-solid fa-circle-info"></i><span>Wo Datenbank und Puffer liegen, legt das Ausrollen fest. Hier steht nur, was belegt ist; ein Umzug geschieht beim Ausrollen, nie aus der Oberfläche.</span></p>
          <div class="rh-ablage"><code class="rh-pfadwert">${esc(a.datenordner)}</code>
            <div class="ak-geraet rh-bestand rh-ablage-zahlen" data-bauform="inspektor"><span class="ak-schraube lo" style="--dreh:10deg"></span><span class="ak-schraube ro" style="--dreh:70deg"></span><span class="ak-schraube lu" style="--dreh:-30deg"></span><span class="ak-schraube ru" style="--dreh:45deg"></span>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text="${String(a.datenbank).replace(".", ",")}"></ak-segmente><span class="ak-etikett">Datenbank GB</span></div>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="gruen" text="${String(a.puffer).replace(".", ",")}"></ak-segmente><span class="ak-etikett">Puffer GB</span></div>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text="${R.zahl(a.dateien)}"></ak-segmente><span class="ak-etikett">Dateien</span></div>
              <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text="${a.frei}"></ak-segmente><span class="ak-etikett">Frei GB</span></div></div>
            <div class="rh-belegung" title="Belegt ${String(a.belegt).replace(".", ",")} GB von ${a.belegt + a.frei} GB"><span style="width:${anteil(a.belegt)}%"></span></div></div></div>`;
      }
      default: return "";
    }
  }

  // ─── Inhalt ───
  function inhaltZeigen() {
    const r = reiter;
    $("#inhalt").innerHTML = `<section class="rh-reiter">${r.teil && !r.karten ? teil(r.teil) : ""}${r.teil && r.karten ? teil(r.teil) : ""}${(r.karten ?? []).map(karte).join("")}</section>`;
    $$("#inhalt .auswahl").forEach((w) => R.auswahl(w, (wert) => {
      if (w.dataset.k && !w.classList.contains("rh-uhr-teil")) aendern(w.dataset.k, wert);
    }));
    customElements.whenDefined("ak-taster").then(() => R.tastenlicht?.($("#inhalt")));
  }

  function zeileVon(k) {
    for (const r of bereich.reiter) for (const kt of r.karten ?? []) for (const z of kt.zeilen ?? []) if (schluessel(z) === k) return z;
    return null;
  }

  function aendern(k, wert) {
    const z = zeileVon(k); if (!z) return;
    if (JSON.stringify(wert) === JSON.stringify(wertVon(z))) return;      // Bauteile melden beim Einhängen ihren Wert
    if (z.geltung === "geraet") { z.wert = wert; band(`${z.name}: gilt sofort auf diesem Gerät.`); }
    else if (JSON.stringify(wert) === JSON.stringify(z.wert)) entwurf.delete(k);
    else entwurf.set(k, { zeile: z, wert });
    leiste();
    inhaltZeigen();
  }

  $("#inhalt").addEventListener("click", (e) => {
    const t = e.target;
    const seg = t.closest(".segment[data-k] button");
    if (seg) {
      const g = seg.closest(".segment"), z = zeileVon(g.dataset.k);
      if (g.dataset.art === "mehrfach") { const w = [...wertVon(z)]; const i = w.indexOf(seg.dataset.wert); if (i >= 0) w.splice(i, 1); else w.push(seg.dataset.wert); aendern(g.dataset.k, w); }
      else aendern(g.dataset.k, seg.dataset.wert);
      return;
    }
    const schritt = t.closest(".rh-schrift-wahl [data-schritt]");
    if (schritt) { const g = schritt.closest("[data-k]"), z = zeileVon(g.dataset.k); aendern(g.dataset.k, Math.min(SCHRIFT.length - 1, Math.max(0, wertVon(z) + Number(schritt.dataset.schritt)))); return; }
    const weg = t.closest(".rh-e-liste [data-weg]");
    if (weg) { const g = weg.closest("[data-k]"), z = zeileVon(g.dataset.k); const w = [...wertVon(z)]; w.splice(Number(weg.dataset.weg), 1); aendern(g.dataset.k, w); return; }
    const vg = t.closest("[data-vorgabe]");
    if (vg) { frage = { art: "vorgabe", id: vg.dataset.vorgabe }; inhaltZeigen(); vorgabeFrage(vg.dataset.vorgabe); return; }
    const fr = t.closest("[data-fragen]");
    if (fr) { frage = { art: fr.dataset.fragen, id: fr.dataset.id }; inhaltZeigen(); return; }
    if (t.closest("[data-abbrechen]")) { frage = null; inhaltZeigen(); return; }
    const ja = t.closest("[data-ja]");
    if (ja) { loeschen(ja.dataset.ja, ja.dataset.id); return; }
    const akt = t.closest("[data-aktiv]");
    if (akt) { ordner.forEach((o) => { o.aktiv = String(o.id) === akt.dataset.aktiv; }); band(`Neue Aufnahmen landen jetzt ${akt.dataset.aktiv === "0" ? "im Stammordner" : `in "${ordner.find((o) => o.aktiv).name}"`}.`); inhaltZeigen(); return; }
    const treffer = t.closest("[data-ort] button");
    if (treffer) { treffer.parentElement.querySelectorAll("button").forEach((b) => b.classList.toggle("aktiv", b === treffer)); ortGeaendert(); return; }
    const mehr = t.closest(".rh-langtext .rh-mehr");
    if (mehr) { const p = mehr.previousElementSibling; const auf = p.classList.toggle("gekuerzt"); mehr.innerHTML = auf ? `<i class="fa-solid fa-chevron-down"></i>Mehr zeigen` : `<i class="fa-solid fa-chevron-up"></i>Weniger zeigen`; }
  });

  $("#inhalt").addEventListener("input", (e) => {
    const t = e.target;
    if (t.closest("[data-ort]")) { ortGeaendert(); return; }
    if (t.matches("ak-taster[data-k]")) { aendern(t.dataset.k, t.hasAttribute("an")); return; }
    if (t.matches("ak-schieber[data-k]")) {
      const z = zeileVon(t.dataset.k), w = +(Math.round(t.wert / z.schritt) * z.schritt).toFixed(2);
      if (z.geltung !== "alle") return;
      if (w === z.wert) entwurf.delete(t.dataset.k); else entwurf.set(t.dataset.k, { zeile: z, wert: w });
      leiste();
      const name = t.closest(".rh-e-zeile").querySelector(".rh-e-name"), punkt = name.querySelector(".einstellung-punkt");
      if (entwurf.has(t.dataset.k) && !punkt) name.insertAdjacentHTML("afterbegin", `<span class="einstellung-punkt" title="Geändert, noch nicht gespeichert"></span>`);
      if (!entwurf.has(t.dataset.k)) punkt?.remove();
    }
  });

  /** der Ort (Name, Breite, Länge) ist ein Wert für alle Geräte: er wartet in der Leiste wie jede andere Änderung */
  const ORT = { name: "Ort der Sonnenzeiten", geltung: "alle", wert: "Hannover" };
  function ortGeaendert() { entwurf.set("ort", { zeile: ORT, wert: "geändert" }); leiste(); }

  function vorgabeFrage(k) {
    const z = zeileVon(k), ort = $(`[data-zeile="${CSS.escape(k)}"] .rh-e-wert`);
    ort.insertAdjacentHTML("beforeend", rueckfrage(`"${esc(z.name)}" auf die Vorgabe setzen? Die eigene Angabe (${esc(Array.isArray(z.wert) ? z.wert.join(", ") : z.wert)}) ist danach weg.`, "Auf Vorgabe setzen", "vorgabe", k).replace("fa-trash", "fa-rotate-left"));
  }

  function loeschen(art, id) {
    frage = null;
    if (art === "kategorie") { const i = kategorien.findIndex((k) => String(k.id) === id); const [k] = kategorien.splice(i, 1); band(`Kategorie "${k.name}" gelöscht.`, () => { kategorien.splice(i, 0, k); inhaltZeigen(); }); }
    if (art === "ordner") { const i = ordner.findIndex((o) => String(o.id) === id); const [o] = ordner.splice(i, 1); band(`Ordner "${o.name}" gelöscht.`, () => { ordner.splice(i, 0, o); inhaltZeigen(); }); }
    if (art === "muster") { const i = muster.findIndex((m) => String(m.id) === id); const [m] = muster.splice(i, 1); band(`Muster "${m.muster}" entfernt.`, () => { muster.splice(i, 0, m); inhaltZeigen(); }); }
    if (art === "vorgabe") band("Auf die Vorgabe gesetzt.");
    inhaltZeigen();
  }

  // ─── Leiste Speichern ───
  function leiste() {
    const n = entwurf.size, l = $("#speichern");
    l.hidden = !n;
    $("#speichern-text").innerHTML = n ? `<b>${n} ${n === 1 ? "Änderung" : "Änderungen"}</b> für alle Geräte: ${[...entwurf.values()].map((x) => esc(x.zeile.name)).join(", ")}` : "";
  }
  $("#verwerfen").addEventListener("click", () => { entwurf.clear(); leiste(); inhaltZeigen(); });
  $("#uebernehmen").addEventListener("click", () => {
    const n = entwurf.size;
    entwurf.forEach(({ zeile: z, wert }) => { z.wert = wert; });
    entwurf.clear(); leiste(); inhaltZeigen(); band(`${n} ${n === 1 ? "Einstellung" : "Einstellungen"} gespeichert, gilt für alle Geräte.`);
  });

  // ─── Band ───
  let bandUhr;
  function band(text, zurueck) {
    const b = $("#band");
    b.innerHTML = `<i class="fa-solid fa-circle-check" style="color:var(--led-gruen)"></i><span>${esc(text)}</span>${zurueck ? `<button class="knopf primaer" type="button" id="band-zurueck"><i class="fa-solid fa-rotate-left"></i>Rückgängig</button>` : ""}<button class="rund" type="button" id="band-zu" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button>`;
    b.hidden = false;
    if (zurueck) $("#band-zurueck").onclick = () => { zurueck(); b.hidden = true; };
    $("#band-zu").onclick = () => { b.hidden = true; };
    clearTimeout(bandUhr); bandUhr = setTimeout(() => { b.hidden = true; }, 10000);
  }

  function alles() { frage = null; bereicheZeigen(); reiterZeigen(); inhaltZeigen(); leiste(); }
  alles();
})();
