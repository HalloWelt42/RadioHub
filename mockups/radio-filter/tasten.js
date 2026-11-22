// Tasten (Entwurf RAD-58): jede Fassung mit der ganzen Steuerung der Kanzel (Zurück, Stopp,
// Abspielen, Aufnahme, Vor, Fokus, Moduswechsel, Reihenfolge) und den Zuständen aus, an, gedrückt, gesperrt, dunkel und
// hell nebeneinander. Das Tastenlicht (Schlitz oben in der Kappe), die Größe und die Lage der Symbole sind in allen
// Fassungen gleich; die Fassung setzt nur Material, Plastizität und Farbe (tasten.css, Klasse tv-<name>).
(() => {
  "use strict";
  const TASTEN = [
    { id: "heute", name: "Heute", text: "Graue Glaskappe mit Glanz von oben, wie in der Kanzel jetzt. Zum Vergleich." },
    { id: "alu", name: "Gebürstetes Aluminium", text: "Helle Metallkappe mit feinem Schliff quer, Fase oben hell, unten dunkel. Dunkle Symbole, klassisches HiFi-Gerät." },
    { id: "lack", name: "Klavierlack", text: "Tiefschwarzer Hochglanz mit weichem Lichtband oben, dünne Kante. Helle Symbole, ruhig und edel." },
    { id: "gummi", name: "Softtouch", text: "Matt gummiert, ohne Glanz, stärker gerundet. Die Kappe sitzt leicht in der Fläche, wie eine Fernbedienung." },
    { id: "elfenbein", name: "Elfenbein", text: "Warme helle Kappe mit Sockel nach unten, wie Geräte der Siebziger. Braune Symbole." },
    { id: "fase", name: "Anthrazit mit Fase", text: "Dunkles Metall mit breiter, gefräster Fase rundum, kantig. Technisch, kräftige Plastizität." },
    { id: "rauch", name: "Rauchglas", text: "Durchscheinendes dunkles Acryl mit Tiefe nach unten, helle Kante oben. Leicht, modern." },
  ];

  // eine Taste der Steuerung; an, gedrückt und gesperrt als Zustand; rolle setzt in der Auswahl Symbol- und Lichtfarbe
  const taste = (symbol, farbe, led, hilfe, { an = false, gedrueckt = false, gesperrt = false, rolle = "" } = {}) => {
    const klassen = [gedrueckt ? "gedrueckt" : "", rolle ? `tw-${rolle}` : ""].filter(Boolean).join(" ");
    return `<ak-taster art="glas" symbol="${symbol}" farbe="${farbe}" led="${led}" modus="tasten" hilfe="${hilfe}"${an ? " an" : ""}${gesperrt ? " gesperrt" : ""}${klassen ? ` class="${klassen}"` : ""}></ak-taster>`;
  };
  const steuerung = () => `<div class="tv-reihe">
      <div class="tv-gruppe">
        ${taste("fa-backward-step", "weiss", "bernstein", "Zurück")}
        ${taste("fa-stop", "weiss", "weiss", "Stopp")}
        ${taste("fa-play", "gruen", "gruen", "Abspielen", { an: true })}
        ${taste("fa-circle", "rot", "rot", "Aufnahme")}
        ${taste("fa-forward-step", "weiss", "bernstein", "Vor")}
      </div>
      <div class="tv-gruppe">
        ${taste("fa-location-crosshairs", "weiss", "blau", "Fokus", { an: true })}
        ${taste("fa-wave-square", "weiss", "weiss", "Original oder Zeitversatz")}
        ${taste("fa-arrow-right", "weiss", "weiss", "Reihenfolge")}
      </div></div>`;
  const zustaende = () => `<div class="tv-zustaende">
      <figure>${taste("fa-circle", "rot", "rot", "Aufnahme, aus")}<figcaption>aus</figcaption></figure>
      <figure>${taste("fa-circle", "rot", "rot", "Aufnahme, an", { an: true })}<figcaption>an</figcaption></figure>
      <figure>${taste("fa-play", "gruen", "gruen", "Abspielen, gedrückt", { an: true, gedrueckt: true })}<figcaption>gedrückt</figcaption></figure>
      <figure>${taste("fa-forward-step", "weiss", "bernstein", "Vor, gesperrt", { gesperrt: true })}<figcaption>gesperrt</figcaption></figure>
    </div>`;
  const tafel = (art, thema, inhalt) => `<div class="tv-tafel ${art}" data-theme="${thema}"><span class="ak-etikett">${thema === "dunkel" ? "Dunkel" : "Hell"}</span>${inhalt}</div>`;
  const block = (nr, v, inhalt) => `<div class="rh-rahmen-block rp-breit"><p class="rh-rahmen-titel"><span class="pille">${nr}</span><span>${v.name}</span><span>${v.text}</span></p>
      <div class="tv-paar">${inhalt}</div></div>`;

  // Gewählt (Nutzer 22.11.): Klavierlack Schwarz im dunklen, Elfenbein im hellen Thema. Jede Taste hat eine feste
  // Symbolfarbe, die in keinem Zustand wechselt; den Zustand zeigt nur das Tastenlicht. Stopp leuchtet reinweiß,
  // Fokus, Moduswechsel und Reihenfolge weißblau; Abspielen und Aufnahme tragen satte, dunklere Symbolfarben.
  const steuerungGewaehlt = () => `<div class="tv-reihe">
      <div class="tv-gruppe">
        ${taste("fa-backward-step", "weiss", "bernstein", "Zurück", { rolle: "blatt" })}
        ${taste("fa-stop", "weiss", "reinweiss", "Stopp", { rolle: "stopp" })}
        ${taste("fa-play", "gruen", "gruen", "Abspielen", { an: true, rolle: "spielen" })}
        ${taste("fa-circle", "rot", "rot", "Aufnahme", { rolle: "aufnahme" })}
        ${taste("fa-forward-step", "weiss", "bernstein", "Vor", { rolle: "blatt" })}
      </div>
      <div class="tv-gruppe">
        ${taste("fa-location-crosshairs", "weiss", "eisblau", "Fokus", { an: true, rolle: "betrieb" })}
        ${taste("fa-wave-square", "weiss", "eisblau", "Original oder Zeitversatz", { an: true, rolle: "betrieb" })}
        ${taste("fa-arrow-right", "weiss", "eisblau", "Reihenfolge", { rolle: "betrieb" })}
      </div></div>`;
  const zustaendeGewaehlt = () => `<div class="tv-zustaende">
      <figure>${taste("fa-circle", "rot", "rot", "Aufnahme, aus", { rolle: "aufnahme" })}<figcaption>Aufnahme aus</figcaption></figure>
      <figure>${taste("fa-circle", "rot", "rot", "Aufnahme, an", { an: true, rolle: "aufnahme" })}<figcaption>Aufnahme an</figcaption></figure>
      <figure>${taste("fa-stop", "weiss", "reinweiss", "Stopp, gedrückt", { an: true, gedrueckt: true, rolle: "stopp" })}<figcaption>Stopp gedrückt</figcaption></figure>
      <figure>${taste("fa-play", "gruen", "gruen", "Abspielen, aus", { rolle: "spielen" })}<figcaption>Abspielen aus</figcaption></figure>
      <figure>${taste("fa-location-crosshairs", "weiss", "eisblau", "Fokus, aus", { rolle: "betrieb" })}<figcaption>Fokus aus</figcaption></figure>
      <figure>${taste("fa-forward-step", "weiss", "bernstein", "Vor, gesperrt", { gesperrt: true, rolle: "blatt" })}<figcaption>gesperrt</figcaption></figure>
    </div>`;
  const gewaehlt = (thema, name) => `<div class="tv-tafel tw-tafel ${thema === "dunkel" ? "tv-lack" : "tv-elfenbein"} lf-glimmen" data-theme="${thema}">
      <span class="ak-etikett">${name}</span>${steuerungGewaehlt()}${zustaendeGewaehlt()}</div>`;
  const wahl = document.querySelector("[data-wahl]");
  wahl.innerHTML = `<div class="rh-rahmen-block rp-breit"><p class="rh-rahmen-titel"><span class="pille">Gewählt</span><span>Klavierlack Schwarz und Elfenbein</span>
      <span>Dunkel Klavierlack, hell Elfenbein; feste Symbolfarben, Licht nur im Schlitz</span></p>
      <div class="tw-toene">${gewaehlt("dunkel", "Dunkel · Klavierlack Schwarz")}${gewaehlt("hell", "Hell · Elfenbein")}</div></div>`;

  const tasten = document.querySelector("[data-tasten]");
  tasten.innerHTML = TASTEN.map((v, i) => block(String.fromCharCode(65 + i), v,
    ["dunkel", "hell"].map((th) => tafel(`tv-${v.id}`, th, steuerung() + zustaende())).join(""))).join("");

  customElements.whenDefined("ak-taster").then(() => {
    window.RH?.tastenlicht?.(document);
    // gedrückt: die Klasse ist nach dem Aufbau des Tasters gesetzt, damit sie bleibt
    document.querySelectorAll("ak-taster.gedrueckt").forEach((t) => t.classList.add("gedrueckt"));
  });
})();
