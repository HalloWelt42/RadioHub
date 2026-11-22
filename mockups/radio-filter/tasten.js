// Tasten und LEDs (Entwurf RAD-58). Tasten: jede Fassung mit der ganzen Steuerung der Kanzel (Zurück, Stopp,
// Abspielen, Aufnahme, Vor, Fokus, Moduswechsel, Reihenfolge) und den Zuständen aus, an, gedrückt, gesperrt, dunkel und
// hell nebeneinander. Das Tastenlicht (Schlitz oben in der Kappe), die Größe und die Lage der Symbole sind in allen
// Fassungen gleich; die Fassung setzt nur Material, Plastizität und Farbe (tasten.css, Klasse tv-<name>).
// LEDs: jede Form (Klasse lf-<name>) in jeder Farbe, aus und an, atmend und blinkend, klein (Listen) und mittel.
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
  const LEDS = [
    { id: "heute", name: "Heute", text: "Flache Kuppel in schmaler Metallfassung." },
    { id: "versenkt", name: "Versenkt", text: "Ohne Fassung, in ein dunkles Loch der Fläche eingelassen; das Licht sitzt tiefer." },
    { id: "chrom", name: "Breiter Chromring", text: "Kräftige, polierte Fassung mit Fase, wie Kontrollleuchten an Messgeräten." },
    { id: "ring", name: "Leuchtring", text: "Das Licht ist ein Ring um eine dunkle Mitte." },
    { id: "smd", name: "Quadratisch", text: "Kleines Quadrat mit gerundeten Ecken, wie eine Bauteil-LED auf der Platine." },
    { id: "linse", name: "Streulinse", text: "Matte Linse, das Licht verteilt sich weich bis zum Rand, ohne Fassung." },
    { id: "flach", name: "Flach", text: "Nur eine Farbfläche, ohne Fassung und ohne Tiefe; am ruhigsten." },
  ];
  const FARBEN = [["rot", "Rot"], ["bernstein", "Bernstein"], ["gelb", "Gelb"], ["gruen", "Grün"], ["blau", "Blau"], ["violett", "Violett"], ["weiss", "Weiß"]];

  // eine Taste der Steuerung; an, gedrückt und gesperrt als Zustand
  const taste = (symbol, farbe, led, hilfe, { an = false, gedrueckt = false, gesperrt = false } = {}) =>
    `<ak-taster art="glas" symbol="${symbol}" farbe="${farbe}" led="${led}" modus="tasten" hilfe="${hilfe}"${an ? " an" : ""}${gesperrt ? " gesperrt" : ""}${gedrueckt ? ' class="gedrueckt"' : ""}></ak-taster>`;
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

  // LEDs: je Farbe aus und an (mittel), darunter klein; am Ende atmend und blinkend
  const led = (farbe, zustand, groesse = "") => `<ak-led farbe="${farbe}" zustand="${zustand}"${groesse ? ` groesse="${groesse}"` : ""}></ak-led>`;
  const ledTafel = () => `<div class="lf-raster">
      ${FARBEN.map(([f, n]) => `<figure class="lf-farbe"><div class="lf-paar">${led(f, "aus")}${led(f, "an")}</div><div class="lf-paar klein">${led(f, "aus", "klein")}${led(f, "an", "klein")}</div><figcaption>${n}</figcaption></figure>`).join("")}
      <figure class="lf-farbe"><div class="lf-paar">${led("gruen", "atmet")}${led("rot", "blinkt")}</div><div class="lf-paar klein">${led("gruen", "atmet", "klein")}${led("rot", "blinkt", "klein")}</div><figcaption>atmet, blinkt</figcaption></figure>
      <div class="lf-zeilen">${["Prince Ital Joe - United", "Werbung", "Ace of Base - Wheel of Fortune"].map((t, i) =>
        `<div class="lf-zeile">${led(i === 0 ? "rot" : i === 1 ? "gelb" : "blau", i === 0 ? "atmet" : i === 1 ? "aus" : "an", "klein")}<span>${t}</span></div>`).join("")}</div>
    </div>`;

  const tasten = document.querySelector("[data-tasten]");
  tasten.innerHTML = TASTEN.map((v, i) => block(String.fromCharCode(65 + i), v,
    ["dunkel", "hell"].map((th) => tafel(`tv-${v.id}`, th, steuerung() + zustaende())).join(""))).join("");
  const leds = document.querySelector("[data-leds]");
  leds.innerHTML = LEDS.map((v, i) => block(String(i + 1), v,
    ["dunkel", "hell"].map((th) => tafel(`lf-${v.id}`, th, ledTafel())).join(""))).join("");

  customElements.whenDefined("ak-taster").then(() => {
    window.RH?.tastenlicht?.(document);
    // gedrückt: die Klasse ist nach dem Aufbau des Tasters gesetzt, damit sie bleibt
    document.querySelectorAll("ak-taster.gedrueckt").forEach((t) => t.classList.add("gedrueckt"));
  });
})();
