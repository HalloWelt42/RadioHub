// Werbung in Podcasts (Entwurf RAD-32): Werbestellen je Folge mit Herkunft, beim Hören übersprungen (die Datei bleibt
// vollständig), in der Leiste der Wiedergabe sichtbar, im Detail der Folge prüfbar und änderbar, im Abo ein Schalter,
// im Schnitt als Stück markierbar, am Telefon im Blatt der Folge. Nur Entwurf, Musterdaten.
(() => {
  "use strict";
  const P = window.RHPodcasts, R = window.RH, esc = R.esc;
  const abo = (id) => P.ABOS.find((a) => a.id === id);
  const F = P.FOLGEN.find((f) => f.id === "s1");                  // Warum der Himmel nachts dunkel ist, 48 min
  const zeit = (s) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, "0")}`;
  // Werbestellen der Folge in Sekunden; Herkunft: kapitel, hand, vergleich, transkript, wiederkehrend
  const STELLEN = [
    { von: 0, bis: 38, herkunft: "vergleich", text: "eingefügter Spot vor Beginn" },
    { von: 1312, bis: 1384, herkunft: "transkript", text: "\"Diese Folge wird unterstützt von ... mit dem Code STERN zehn Prozent\"" },
    { von: 2476, bis: 2520, herkunft: "kapitel", text: "Kapitel \"Werbung\" aus dem Feed" },
  ];
  const HERKUNFT = {
    kapitel: ["fa-list-ol", "Kapitel im Feed"], hand: ["fa-hand-pointer", "von Hand"], vergleich: ["fa-code-compare", "Vergleich zweier Fassungen"],
    transkript: ["fa-comment-dots", "aus dem Transkript"], wiederkehrend: ["fa-repeat", "wiederkehrender Spot"],
  };
  const DAUER = F.laenge * 60, STELLE = 1384 + 3;
  const summe = STELLEN.reduce((s, x) => s + x.bis - x.von, 0);

  // Leiste der Stelle mit den Werbestellen (bernstein) und dem Abspielkopf
  const leiste = (klasse = "") => `<div class="rp-leiste ${klasse}" role="img" aria-label="Stelle in der Folge mit ${STELLEN.length} Werbestellen">
      <span class="rp-gehoert" style="width:${(STELLE / DAUER) * 100}%"></span>
      ${STELLEN.map((x) => `<span class="rp-werbung" style="left:${(x.von / DAUER) * 100}%;width:${Math.max(0.8, ((x.bis - x.von) / DAUER) * 100)}%" title="Werbung ${zeit(x.von)} bis ${zeit(x.bis)}"></span>`).join("")}
      <span class="rp-kopf" style="left:${(STELLE / DAUER) * 100}%"></span></div>`;

  const schalter = (an, text, farbe = "bernstein", hilfe = "") => `<button class="knopf rh-schalter" type="button" aria-pressed="${an}" title="${hilfe}">
      <ak-led farbe="${farbe}" zustand="${an ? "an" : "aus"}" groesse="klein"></ak-led>${text}</button>`;

  // 1: Abspielleiste (Modul Wiedergabe) beim Hören; eine Stelle wurde eben übersprungen
  function kanzel(el) {
    el.innerHTML = `<div class="rp-kanzel">
      <section class="rh-modul rh-m-zeit" aria-label="Wiedergabe"><span class="ak-etikett">Wiedergabe</span>
        <div class="rh-zeit">
          <div class="ak-glas rh-zeit-glas">
            <ak-segmente art="14" stellen="8" farbe="gruen" text="PODCAST" hilfe="Art der Wiedergabe"></ak-segmente>
            <ak-segmente art="7" stellen="7" farbe="gruen" text="0:23:07" hilfe="Stelle in der Folge"></ak-segmente>
          </div>
          <div class="rh-puffer-zeile">
            <button class="knopf" type="button" title="30 Sekunden zurück"><i class="fa-solid fa-rotate-left"></i>30</button>
            <div class="rh-puffer rp-puffer">${leiste()}<span>23:07 von 48:00 · <span class="rp-ohne">ohne Werbung 45:26</span></span></div>
            <button class="knopf" type="button" title="30 Sekunden vor"><i class="fa-solid fa-rotate-right"></i>30</button>
          </div>
        </div>
      </section>
      <div class="rh-band rp-band" role="status"><i class="fa-solid fa-forward"></i><span><b>Werbung übersprungen</b> (1:12, aus dem Transkript)</span>
        <button class="knopf" type="button"><i class="fa-solid fa-rotate-left"></i>Zurück und anhören</button>
        <button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button></div>
    </div>`;
  }

  // Liste der Werbestellen (Detail der Folge, Blatt am Telefon)
  const stellenListe = (mitAktionen = true) => `<ol class="rp-stellen">${STELLEN.map((x, i) => `<li>
      <span class="rh-a-nr">${String(i + 1).padStart(2, "0")}</span>
      <span class="rp-zeit"><b>${zeit(x.von)} bis ${zeit(x.bis)}</b><span>${zeit(x.bis - x.von)}</span></span>
      <span class="rp-herkunft"><span><i class="fa-solid ${HERKUNFT[x.herkunft][0]}"></i>${HERKUNFT[x.herkunft][1]}</span><span class="rh-still">${esc(x.text)}</span></span>
      ${mitAktionen ? `<span class="rp-aktionen"><button class="rund" type="button" title="Diese Stelle anhören" aria-label="Anhören"><i class="fa-solid fa-play"></i></button>
        <button class="rund" type="button" title="Keine Werbung: nicht mehr überspringen (mit Rückgängig)" aria-label="Keine Werbung"><i class="fa-solid fa-xmark"></i></button></span>` : ""}
    </li>`).join("")}</ol>`;

  // 2 und 3: Folge aufgeklappt; einmal fertig, einmal während der Suche
  function folge(el, sucht) {
    const a = abo(F.abo);
    el.innerHTML = `<div class="rp-rechner"><article class="rh-sender rh-folge spielt offen">
      <div class="rh-sender-kern">
        <span class="led"><ak-led farbe="blau" zustand="an" groesse="klein"></ak-led></span>${R.logo(a)}
        <div class="name"><b>${esc(F.titel)}</b><div class="meta"><span>${esc(a.name)}</span><span>18. Nov.</span>
          <span class="rp-marke" title="${STELLEN.length} Werbestellen, ${zeit(summe)}, werden übersprungen"><i class="fa-solid fa-forward"></i>${STELLEN.length} × Werbung, ${zeit(summe)}</span></div></div>
        <div class="stand-zelle"><span class="rh-stand"><span class="balken"><span style="width:48%"></span></span>noch 25 min</span></div>
        <div class="laenge">48 min</div>
        <div class="rh-aktionen rh-folgen-aktionen">
          <button class="rund" type="button" aria-label="Speichern"><i class="fa-solid fa-cloud-arrow-up"></i></button>
          <button class="rund" type="button" aria-label="Gehört"><i class="fa-solid fa-check"></i></button>
          <button class="rund" type="button" aria-expanded="true" aria-label="Details"><i class="fa-solid fa-chevron-up"></i></button>
        </div>
      </div>
      <div class="rh-detail rh-folge-detail rp-detail">
        <p>${esc(F.text)}</p>
        <section class="rp-werbeteil"><div class="rp-kopf-zeile"><h3><i class="fa-solid fa-rectangle-ad"></i>Werbung in dieser Folge</h3>
            <span class="rh-still">${STELLEN.length} Stellen, zusammen ${zeit(summe)}; die Datei bleibt vollständig</span></div>
          ${leiste("gross")}
          ${sucht ? `<div class="rh-auftrag"><ak-led farbe="gruen" zustand="blinkt" groesse="klein"></ak-led><span>Werbung suchen: Transkript lesen</span>
              <div class="balken"><span style="width:60%"></span></div><span class="rh-zahl">2/3</span><button class="knopf" type="button">Abbrechen</button></div>
            <p class="rh-still rp-schritte"><i class="fa-solid fa-check"></i>Kapitel im Feed: 1 Stelle · <i class="fa-solid fa-check"></i>Vergleich zweier Fassungen: 1 Stelle · <i class="fa-solid fa-spinner fa-spin"></i>Transkript ...</p>`
            : stellenListe()}
          <div class="rh-detail-knoepfe">
            ${schalter(true, "Überspringen", "bernstein", "Werbestellen beim Hören überspringen (gilt für dieses Abo)")}
            <button class="knopf" type="button" ${sucht ? "disabled" : ""}><i class="fa-solid fa-magnifying-glass"></i>Werbung suchen</button>
            <button class="knopf" type="button" title="Am Abspielkopf beginnen, im Schnitt genau setzen"><i class="fa-solid fa-plus"></i>Stelle markieren</button>
            <button class="knopf" type="button" title="Neue Datei ohne die Werbestellen daneben; das Original bleibt"><i class="fa-solid fa-scissors"></i>Ohne Werbung speichern</button>
          </div>
        </section>
      </div></article></div>`;
  }

  // 4: Kopf eines Abos mit dem Schalter
  function aboKopf(el) {
    const a = abo(F.abo);
    el.innerHTML = `<div class="rp-rechner"><section class="rh-abo-kopf">
      ${R.logo(a, "gross")}
      <div class="rh-abo-text"><h2>${esc(a.name)}</h2><p class="rh-still">${esc(a.autor)}</p><p>${esc(a.beschreibung)}</p>
        <div class="rh-abo-zahlen"><span><b>2</b> Folgen</span><span><b>1</b> ungehört</span><span><b>1/2</b> gespeichert</span>
          <span class="rp-marke"><i class="fa-solid fa-rectangle-ad"></i><b>2</b> Folgen mit Werbung, zusammen 4 min</span></div></div>
      <div class="rh-detail-knoepfe rh-abo-knoepfe">
        <button class="knopf" type="button"><i class="fa-solid fa-rotate"></i>Aktualisieren</button>
        ${schalter(true, "Neue speichern", "gruen")}
        ${schalter(true, "Werbung überspringen", "bernstein", "Erkannte Werbestellen in allen Folgen dieses Abos überspringen")}
        ${schalter(true, "Neue Folgen prüfen", "bernstein", "Neue Folgen nach dem Speichern von selbst auf Werbung durchsuchen")}
        <button class="knopf" type="button"><i class="fa-solid fa-thumbtack"></i>Oben anheften</button>
        <button class="knopf gefahr" type="button"><i class="fa-solid fa-trash-can"></i>Abbestellen</button>
      </div></section></div>`;
  }

  // 5: Schnitt einer gespeicherten Folge: Stücke als Werbung markieren
  function schnitt(el) {
    const st = [[0, 38, "Werbung", "werbung"], [38, 1312, "Teil 1", "behalten"], [1312, 1384, "Werbung", "werbung"], [1384, 2476, "Teil 2", "behalten"], [2476, 2520, "Werbung", "werbung"], [2520, 2880, "Teil 3", "behalten"]];
    el.innerHTML = `<div class="rp-rechner rh-schnitt rp-schnitt">
      <div class="rh-stuecke">
        <div class="rh-spalten rh-stueck-spalten" aria-hidden="true"><span>Stück</span><span>von</span><span>bis</span><span class="rechts">Länge</span><span>Art</span></div>
        ${st.map(([von, bis, name, art], i) => `<div class="rh-stueck${art === "werbung" ? " rp-werbung-stueck" : ""}">
          <span class="rh-a-nr">${String(i + 1).padStart(2, "0")}</span>
          <label class="suche rh-stueck-name"><input type="text" value="${name}" aria-label="Name"></label>
          <span class="rh-zahl">${zeit(von)}</span><span class="rh-zahl">${zeit(bis)}</span><span class="rh-zahl rechts">${zeit(bis - von)}</span>
          ${art === "werbung" ? schalter(true, "Werbung", "bernstein", "Als Werbung markiert: beim Hören übersprungen, beim Schneiden ohne Werbung weggelassen") : schalter(true, "Behalten", "gruen")}
          <button class="rund" type="button" aria-label="Hören"><i class="fa-solid fa-play"></i></button></div>`).join("")}
      </div>
      <div class="rh-schnitt-aktionen">
        <div class="rh-schnitt-block"><span class="ak-etikett">Werbung</span>
          <button class="knopf primaer" type="button"><i class="fa-solid fa-rectangle-ad"></i>3 Werbestellen übernehmen</button>
          <button class="knopf" type="button"><i class="fa-solid fa-scissors"></i>Ohne Werbung speichern</button></div>
        <p class="rh-still rh-schnitt-ziel"><i class="fa-solid fa-circle-info"></i>Übernehmen ändert die Datei nicht: die Stellen werden beim Hören übersprungen. Ohne Werbung speichern legt eine neue Datei daneben, das Original bleibt.</p>
      </div></div>`;
  }

  // 6 und 7: Telefon
  const rahmen = (inhalt, zusatz = "") => `<div class="t-app t-app-podcasts">
      <div class="t-status"><span>9:41</span><span class="insel"></span><span><i class="fa-solid fa-signal"></i><i class="fa-solid fa-wifi"></i><i class="fa-solid fa-battery-three-quarters"></i></span></div>
      <div class="t-luft" aria-hidden="true"></div>
      ${inhalt}
      <div class="t-spieler" role="button" aria-label="Spieler öffnen">
        <div class="ak-glas"><b><ak-led farbe="blau" zustand="an" groesse="klein"></ak-led>${esc(F.titel)}</b><span>Sternstunde Physik · 23:07 von 48:00</span></div>
        <ak-taster art="glas" symbol="fa-pause" farbe="blau" led="blau" hilfe="Anhalten" an></ak-taster>
        <button class="rund" type="button" aria-label="Spieler öffnen"><i class="fa-solid fa-chevron-up"></i></button>
      </div>
      <nav class="t-reiter" aria-label="Bereiche"><span><i class="fa-solid fa-radio"></i>Radio</span><span><i class="fa-solid fa-circle-dot"></i>Aufnahmen</span><span class="aktiv"><i class="fa-solid fa-podcast"></i>Podcasts</span></nav>
      ${zusatz}</div>`;
  const kopfAbo = `<div class="t-kopf-zurueck tp-kopf"><button class="rund" type="button" aria-label="Zurück"><i class="fa-solid fa-chevron-left"></i></button>
      <div><b>Sternstunde Physik</b><span class="rh-still">Lehrstuhl am Fluss</span></div></div>`;
  const zeile = `<div class="t-zeile tp-folge spielt">${R.logo(abo(F.abo))}
      <div><b>${esc(F.titel)}</b><div class="t-meta"><span>18. Nov.</span><span>48 min</span><span class="rp-marke"><i class="fa-solid fa-forward"></i>3 × Werbung</span></div>
        <div class="tp-stand-zeile"><span class="rh-stand tp-stand"><span class="balken"><span style="width:48%"></span></span>noch 25 min</span></div></div>
      <button class="rund" type="button" aria-label="Hören"><i class="fa-solid fa-volume-high"></i></button></div>`;
  function telefonBlatt(el) {
    el.innerHTML = rahmen(`${kopfAbo}<div class="t-liste">${zeile}</div>`, `<div class="t-schleier"></div>
      <div class="t-blatt tp-blatt" role="dialog"><div class="t-blatt-kopf"><h2>${esc(F.titel)}</h2><button class="rund" type="button" aria-label="Schließen"><i class="fa-solid fa-xmark"></i></button></div>
        <div class="t-blatt-rollt">
          <div class="t-meta"><span>Sternstunde Physik</span><span>18. Nov.</span><span>48 min</span></div>
          <div class="tp-aktionen"><button class="knopf primaer" type="button"><i class="fa-solid fa-forward"></i>Weiter ab 23:07</button>
            ${schalter(true, "Überspringen", "bernstein")}</div>
          <h3 class="rp-blatt-titel"><i class="fa-solid fa-rectangle-ad"></i>Werbung: 3 Stellen, ${zeit(summe)}</h3>
          ${leiste("gross")}
          ${stellenListe(true)}
          <div class="tp-aktionen"><button class="knopf" type="button"><i class="fa-solid fa-magnifying-glass"></i>Werbung suchen</button></div>
        </div></div>`);
  }
  function telefonBand(el) {
    el.innerHTML = rahmen(`${kopfAbo}<div class="t-liste">${zeile}</div>`, `<div class="rh-band rp-band rp-band-telefon" role="status"><i class="fa-solid fa-forward"></i>
      <span><b>Werbung übersprungen</b> (1:12)</span><button class="knopf" type="button"><i class="fa-solid fa-rotate-left"></i>Zurück</button></div>`);
  }

  const ZUSTAENDE = { kanzel, folge: (el) => folge(el, false), sucht: (el) => folge(el, true), abo: aboKopf, schnitt, blatt: telefonBlatt, band: telefonBand };
  customElements.whenDefined("ak-segmente").then(() => {
    document.querySelectorAll("[data-zustand]").forEach((el) => { ZUSTAENDE[el.dataset.zustand](el); R.tastenlicht?.(el); });
  });
})();
