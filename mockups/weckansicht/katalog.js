// Gesamtkatalog der Weckansicht (RAD-15): zehn Gestaltungen aus einem Zustand gezeichnet. Beim Klingeln ordnet sich jede
// Gestaltung neu an (nichts überdeckt etwas) und bietet immer den Wechsel Radio oder Weckton; Schlummern zeigt die
// Weckzeit und "Wecker aus".
import { zeichnen, breite } from "./matrix.js";
import { roehre, glimmpunkte } from "./nixie.js";

const D = { datum: "FR 20.11.", wecker: "Mo 06:30", weck: "06:30", bis: "06:39", sender: "Deutschlandfunk", kurz: "DLF", auf: "07:58", unter: "16:21" };
const ZUSTAENDE = [
  { modus: "hell", lage: "ruhe", zeit: "06:42", titel: "Hell" },
  { modus: "dunkel", lage: "ruhe", zeit: "06:42", titel: "Dunkel" },
  { modus: "nacht", lage: "ruhe", zeit: "02:17", titel: "Nacht" },
  { modus: "dunkel", lage: "klingelt", quelle: "radio", zeit: "06:30", titel: "Klingelt mit Radio (dunkel)" },
  { modus: "hell", lage: "klingelt", quelle: "weckton", zeit: "06:30", titel: "Klingelt mit Weckton (hell)" },
  { modus: "nacht", lage: "klingelt", quelle: "radio", zeit: "06:30", titel: "Klingelt nachts" },
  { modus: "dunkel", lage: "schlummert", zeit: "06:33", titel: "Schlummert bis 06:39" },
];

const farbe = (el, n) => getComputedStyle(el).getPropertyValue(n).trim();
const i = (n, extra = "") => `<i class="fa-solid ${n}${extra}"></i>`;
const quelleWahl = (z, klasse = "quelle") => `<div class="${klasse}"><button class="${z.quelle === "radio" ? "an" : ""}">${i("fa-radio")}Radio</button>
  <button class="${z.quelle === "weckton" ? "an" : ""}">${i("fa-bell")}Weckton</button></div>`;
const ruheKnoepfe = (k = "rund") => `<div class="reihe"><button class="${k} an">${i("fa-pause")}</button><button class="${k}">${i("fa-comment-dots")}</button><button class="${k}">${i("fa-moon")}</button></div>`;
const weckText = (z) => (z.lage === "klingelt" ? `Wecker ${D.weck}` : z.lage === "schlummert" ? `Schlummert bis ${D.bis}` : D.wecker);
const weckSymbol = (z) => (z.lage === "klingelt" ? i("fa-bell", " fa-shake") : z.lage === "schlummert" ? i("fa-bed") : i("fa-bell"));

// ----- U: Uhr vollflächig (bisherig) ---------------------------------------------------------------------------------
function uhr(tel, z) {
  const unten = z.lage === "klingelt"
    ? `<div class="u-klingeln">${quelleWahl(z)}<button class="gross-taste schlummern">${i("fa-bed")}Schlummern</button><button class="gross-taste aus">${i("fa-power-off")}Aus</button></div>`
    : `<div class="u-leiste"><span>${i("fa-radio")} ${D.sender}</span><span class="w">${weckSymbol(z)} ${weckText(z)}</span>
       ${z.lage === "schlummert" ? `<button class="gross-taste aus" style="min-height:48px">${i("fa-power-off")}Wecker aus</button>` : `<span>${i("fa-sun")} ${D.auf} ${i("fa-moon")} ${D.unter}</span>`}</div>`;
  tel.innerHTML = `<div class="innen"><div class="u-flaeche"><div class="u-uhr" style="${z.lage === "klingelt" ? "font-size:160px" : ""}">${z.zeit}</div>${unten}</div></div>`;
}

// ----- A: Matrix voll ------------------------------------------------------------------------------------------------
function matrix(tel, z) {
  tel.innerHTML = `<div class="innen"><canvas class="matrix"></canvas></div>`;
  const an = farbe(tel, "--an"), aus = farbe(tel, "--aus"), ak = farbe(tel, "--akzent");
  const S = 120, Z = 48, e = [], r = [];
  if (z.lage === "klingelt") {
    e.push({ text: `@ ${D.weck}   ${D.kurz}`, y: 0, mitte: true, farbe: ak });
    e.push({ text: z.zeit, y: 9, mass: 3, mitte: true, farbe: an });
    const felder = [["~ 9 MIN", ak, 0, 40], ["AUS", an, 42, 36], [z.quelle === "radio" ? "RADIO" : "TON", an, 80, 40]];
    // Punktgrafik hat nie Rahmen (Nutzer 20.11.2026): die Tastenflächen sind unsichtbar, nur ihre Schrift leuchtet
    for (const [t, f, x, b] of felder) e.push({ text: t, x: x + Math.round((b - breite(t)) / 2), y: 37, farbe: f });
  } else {
    e.push({ text: D.datum, x: 0, y: 0, farbe: an });
    const w = z.lage === "schlummert" ? `~ ${D.bis}` : `@ MO ${D.weck}`;
    e.push({ text: w, x: S - breite(w), y: 0, farbe: ak });
    e.push({ text: z.zeit, y: 10, mass: 4, mitte: true, farbe: an });
    e.push({ text: D.kurz, x: 0, y: 41, farbe: an });
    const rechts = z.lage === "schlummert" ? "AUS" : `*${D.auf} )${D.unter}`;
    e.push({ text: rechts, x: z.lage === "schlummert" ? S - 30 + Math.round((30 - breite("AUS")) / 2) : S - breite(rechts), y: 40 + (z.lage === "schlummert" ? 0 : 1), farbe: z.lage === "schlummert" ? ak : an });
  }
  zeichnen(tel.querySelector("canvas"), { spalten: S, zeilen: Z, aus, ebenen: e, rahmen: r, glanz: z.modus !== "hell" });
}

// ----- B: HiFi-Gerät -------------------------------------------------------------------------------------------------
function hifi(tel, z) {
  const nacht = z.modus === "nacht";
  let rechts;
  if (z.lage === "klingelt") {
    rechts = `<div class="spalte"><button class="taste gross licht" style="--l:#ffb21f">${i("fa-bed")}<span>SCHLUMMERN 9</span></button>
      <button class="taste gross licht" style="--l:#ff3b30">${i("fa-power-off")}<span>AUS</span></button>
      <div class="tasten"><button class="taste klein${z.quelle === "radio" ? " licht" : ""}">${i("fa-radio")}<span>RADIO</span></button>
      <button class="taste klein${z.quelle === "weckton" ? " licht" : ""}" style="--l:#ffb21f">${i("fa-bell")}<span>WECKTON</span></button></div></div>`;
  } else {
    const w = z.lage === "schlummert" ? `~ BIS ${D.bis}` : `@ MO ${D.weck}`;
    rechts = `<div class="spalte"><div class="glas"><canvas data-t="${w}" data-f="--akzent"></canvas></div>
      <div class="glas"><canvas data-t="${D.kurz}  LIVE"></canvas></div><div class="glas"><canvas data-t="*${D.auf} )${D.unter}"></canvas></div>
      <div class="tasten">${z.lage === "schlummert" ? `<button class="taste licht" style="--l:#ff3b30">${i("fa-power-off")}<span>WECKER AUS</span></button>`
        : `<button class="taste licht">${i("fa-pause")}</button><button class="taste${nacht ? "" : " licht"}">${i("fa-comment-dots")}</button>
        <button class="taste licht" style="--l:${nacht ? "#ff3a28" : "#3d8bff"}">${i("fa-moon")}</button>`}</div></div>`;
  }
  tel.innerHTML = `<div class="innen"><div class="geraet"><div class="glas gross"><canvas class="matrix haupt"></canvas><canvas class="matrix zeile"></canvas></div>${rechts}</div></div>`;
  const an = farbe(tel, "--an"), aus = farbe(tel, "--aus"), ak = farbe(tel, "--akzent");
  zeichnen(tel.querySelector(".haupt"), { spalten: 80, zeilen: 26, aus, ebenen: [{ text: z.zeit, y: 2, mass: 3, mitte: true, farbe: an }] });
  const zeile = z.lage === "klingelt" ? `@ WECKER ${D.weck}   ${D.kurz}` : `${D.datum}   ${D.sender}`;
  zeichnen(tel.querySelector(".zeile"), { spalten: breite(zeile) + 8, zeilen: 9, aus, ebenen: [{ text: zeile, y: 1, mitte: true, farbe: z.lage === "klingelt" ? ak : an }] });
  const kleine = [...tel.querySelectorAll(".spalte canvas")];
  if (kleine.length) {
    const st = Math.max(...kleine.map((c) => breite(c.dataset.t))) + 6;
    kleine.forEach((c) => zeichnen(c, { spalten: st, zeilen: 9, aus, ebenen: [{ text: c.dataset.t, y: 1, mitte: true, farbe: c.dataset.f ? farbe(tel, c.dataset.f) : an }] }));
  }
}

// ----- C: Segment-Uhr ------------------------------------------------------------------------------------------------
const SEG = { a: "8,0 52,0 44,8 16,8", b: "54,2 60,8 60,46 54,50 50,46 50,10", c: "54,52 60,56 60,94 54,100 50,92 50,56",
  d: "16,94 44,94 52,102 8,102", e: "6,52 10,56 10,92 6,100 0,94 0,56", f: "6,2 10,10 10,46 6,50 0,46 0,8", g: "10,47 50,47 54,51 50,55 10,55 6,51" };
const ZIFFER = { 0: "abcdef", 1: "bc", 2: "abged", 3: "abgcd", 4: "fgbc", 5: "afgcd", 6: "afgedc", 7: "abc", 8: "abcdefg", 9: "abcdfg" };
function segmente(text) {
  let x = 0, s = "";
  for (const c of text) {
    if (c === ":") { s += `<circle class="seg" cx="${x + 8}" cy="34" r="5"/><circle class="seg" cx="${x + 8}" cy="70" r="5"/>`; x += 20; continue; }
    for (const [n, p] of Object.entries(SEG)) {
      const pts = p.split(" ").map((xy) => { const [a, b] = xy.split(","); return `${+a + x},${b}`; }).join(" ");
      s += `<polygon class="${ZIFFER[c].includes(n) ? "seg" : "geist"}" points="${pts}" transform="skewX(-6)"/>`;
    }
    x += 76;
  }
  return `<svg viewBox="-8 -4 ${x + 4} 110">${s}</svg>`;
}
function segment(tel, z) {
  const kl = z.lage === "klingelt";
  const unten = kl
    ? `<div class="reihe">${quelleWahl(z)}<button class="gross-taste schlummern" style="flex:1">${i("fa-bed")}Schlummern</button><button class="gross-taste aus" style="flex:1">${i("fa-power-off")}Aus</button></div>`
    : `<div class="unten"><canvas class="matrix"></canvas>${z.lage === "schlummert" ? `<button class="gross-taste aus" style="min-height:52px">${i("fa-power-off")}Wecker aus</button>` : ruheKnoepfe()}</div>`;
  tel.innerHTML = `<div class="innen"><div class="segment"><div class="uhrfeld" style="${kl ? "flex:0 0 58%" : ""}">${segmente(z.zeit)}</div>
    ${kl ? `<div class="unten"><canvas class="matrix"></canvas></div>` : ""}${unten}</div></div>`;
  const an = farbe(tel, "--an"), aus = farbe(tel, "--aus"), ak = farbe(tel, "--akzent");
  const lauf = kl ? `@ WECKER ${D.weck}   ${D.sender}` : z.lage === "schlummert" ? `~ SCHLUMMERT BIS ${D.bis}   ${D.kurz}` : `${D.kurz}   @ MO ${D.weck}   *${D.auf} )${D.unter}`;
  zeichnen(tel.querySelector("canvas"), { spalten: breite(lauf) + 4, zeilen: 9, aus, glanz: z.modus !== "hell", ebenen: [{ text: lauf, x: 2, y: 1, farbe: kl || z.lage === "schlummert" ? ak : an }] });
}

// ----- D: Ruhig ------------------------------------------------------------------------------------------------------
function ruhig(tel, z) {
  const kl = z.lage === "klingelt";
  const rechts = kl
    ? `<div class="knopfspalte"><button class="gross-taste schlummern">${i("fa-bed")}Schlummern</button><button class="gross-taste aus">${i("fa-power-off")}Aus</button>${quelleWahl(z)}</div>`
    : `<div class="info"><div>${i("fa-radio")}<b>${D.sender}</b></div><div class="w">${weckSymbol(z)}${weckText(z)}</div>
       <div class="leise">${i("fa-sun")}${D.auf} ${i("fa-moon")}${D.unter}</div>
       ${z.lage === "schlummert" ? `<button class="gross-taste aus" style="min-height:54px">${i("fa-power-off")}Wecker aus</button>` : ruheKnoepfe()}</div>`;
  const unter = kl ? `<div class="info" style="flex-direction:row;justify-content:center;gap:24px;font-size:20px"><div class="w">${i("fa-bell", " fa-shake")}${D.weck}</div><div>${i("fa-radio")}<b>${D.sender}</b></div></div>` : `<div class="band"></div>`;
  tel.innerHTML = `<div class="innen"><div class="ruhig"><div class="links"><div class="ziffern" style="${kl ? "font-size:140px" : ""}">${z.zeit}</div>${unter}</div>${rechts}</div></div>`;
}

// ----- E: Sternenzeit ------------------------------------------------------------------------------------------------
function himmel(canvas, modus) {
  if (modus === "hell") return;
  const p = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * p; canvas.height = h * p;
  const g = canvas.getContext("2d"); g.scale(p, p);
  let s = 7; const zu = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let k = 0; k < 260; k++) {
    const r = zu() ** 3 * 1.8 + 0.3;
    g.beginPath(); g.arc(zu() * w, zu() * h, r, 0, Math.PI * 2);
    g.fillStyle = modus === "nacht" ? `rgba(200,30,20,${0.25 + zu() * 0.5})` : `rgba(${200 + zu() * 55},${210 + zu() * 45},255,${0.35 + zu() * 0.65})`;
    g.shadowColor = g.fillStyle; g.shadowBlur = r * 4; g.fill();
  }
}
function mond(modus) {
  const phase = ((((new Date(2026, 10, 20) - Date.UTC(2000, 0, 6, 18, 14)) / 86400000 / 29.530588) % 1) + 1) % 1;
  const r = 44, hell = modus === "nacht" ? "#7e1210" : modus === "hell" ? "#fffdf4" : "#f3ecd2", dunkel = modus === "nacht" ? "#140203" : modus === "hell" ? "#9fb8de" : "#1a1838";
  const zu = phase < 0.5, k = Math.cos(phase * 2 * Math.PI) * r;
  const bogen = `M 50 ${50 - r} A ${r} ${r} 0 0 ${zu ? 1 : 0} 50 ${50 + r} A ${Math.abs(k)} ${r} 0 0 ${(k > 0) === zu ? 0 : 1} 50 ${50 - r}`;
  const name = phase < 0.47 ? "zunehmender Mond" : phase < 0.53 ? "Vollmond" : "abnehmender Mond";
  return `<svg viewBox="0 0 100 100" width="96" height="96"><circle cx="50" cy="50" r="${r}" fill="${dunkel}"/><path d="${bogen}" fill="${hell}" style="filter:drop-shadow(0 0 8px ${hell})"/></svg><span>${name}</span>`;
}
function sterne(tel, z) {
  const kl = z.lage === "klingelt";
  const rechts = kl
    ? `<div class="kugeln"><button class="kugel sonne">${i("fa-bed")}9 min</button><button class="kugel still">${i("fa-power-off")}Aus</button></div>`
    : `<div class="mond">${mond(z.modus)}<span>${i("fa-sun")} ${D.auf} ${i("fa-moon")} ${D.unter}</span>${z.lage === "schlummert" ? `<button class="gross-taste aus" style="min-height:50px;font-size:17px">${i("fa-power-off")}Wecker aus</button>` : ""}</div>`;
  tel.innerHTML = `<div class="innen"><div class="sterne${kl ? " klingelt" : ""}"><canvas class="himmel"></canvas>
    <div><div class="zeit" style="${kl ? "font-size:124px" : ""}">${z.zeit}</div><div class="unter"><span class="w">${weckSymbol(z)} ${weckText(z)}</span><span>${i("fa-radio")} ${D.sender}</span></div>
    ${kl ? `<div style="display:flex;justify-content:center;margin-top:14px">${quelleWahl(z)}</div>` : ""}</div>${rechts}</div></div>`;
  if (!kl) himmel(tel.querySelector(".himmel"), z.modus);
}

// ----- F: Astrolabium ------------------------------------------------------------------------------------------------
const pkt = (st, r) => { const a = (st / 24) * 2 * Math.PI - Math.PI / 2; return [181 + Math.cos(a) * r, 181 + Math.sin(a) * r]; };
const std = (t) => { const [h, m] = t.split(":").map(Number); return h + m / 60; };
function astro(tel, z) {
  const kl = z.lage === "klingelt";
  const gold = "currentColor", tag = farbe(tel, "--tagbogen"), punkt = farbe(tel, "--punkt");
  const [ax, ay] = pkt(std(D.auf), 160), [ux, uy] = pkt(std(D.unter), 160);
  let striche = "";
  for (let s = 0; s < 24; s++) {
    const [x1, y1] = pkt(s, s % 3 ? 150 : 144), [x2, y2] = pkt(s, 156);
    striche += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${gold}" stroke-width="${s % 3 ? 1 : 2}"/>`;
    if (s % 3 === 0) { const [tx, ty] = pkt(s, 130); striche += `<text class="klein" x="${tx}" y="${ty + 4}">${s}</text>`; }
  }
  const min = Number(z.zeit.split(":")[1]);
  for (let m = 0; m < 60; m++) {
    const a = (m / 60) * 2 * Math.PI - Math.PI / 2, r1 = m === min ? 92 : 100;
    striche += `<line x1="${181 + Math.cos(a) * r1}" y1="${181 + Math.sin(a) * r1}" x2="${181 + Math.cos(a) * 106}" y2="${181 + Math.sin(a) * 106}" stroke="${gold}" stroke-width="${m === min ? 3 : 1}" opacity="${m === min ? 1 : 0.45}"/>`;
  }
  const [jx, jy] = pkt(std(z.zeit), 166), [wx, wy] = pkt(std(z.lage === "schlummert" ? D.bis : D.weck), 160);
  const svg = `<svg viewBox="0 0 362 362"><circle cx="181" cy="181" r="174" fill="none" stroke="${gold}" opacity=".5"/><circle class="puls" cx="181" cy="181" r="160" fill="none" stroke="${gold}" opacity=".35"/>
    <path d="M ${ax} ${ay} A 160 160 0 0 1 ${ux} ${uy}" fill="none" stroke="${tag}" stroke-width="8" stroke-linecap="round" opacity=".85"/>${striche}
    <circle class="puls" cx="${wx}" cy="${wy}" r="${kl ? 11 : 8}" fill="${punkt}" style="filter:drop-shadow(0 0 8px ${punkt})"/>
    <line x1="181" y1="181" x2="${jx}" y2="${jy}" stroke="${gold}" stroke-width="2" opacity=".6"/><circle cx="${jx}" cy="${jy}" r="5" fill="${gold}"/>
    <text class="zahl" x="181" y="204">${z.zeit}</text><text class="klein" x="181" y="232">FR 20. NOVEMBER</text></svg>`;
  const seite = kl
    ? `<div class="seite"><span class="w">${i("fa-bell", " fa-shake")} ${D.weck}</span><span>${D.sender}</span>
       <button class="siegel voll">${i("fa-bed")}Schlummern</button><button class="siegel">${i("fa-power-off")}Aus</button>${quelleWahl(z)}</div>`
    : `<div class="seite"><span class="w">${weckSymbol(z)} ${weckText(z)}</span><span>${i("fa-radio")} ${D.sender}</span>
       <span class="leise">Tag von ${D.auf} bis ${D.unter}, der goldene Bogen; der helle Punkt ist der Wecker</span>
       ${z.lage === "schlummert" ? `<button class="siegel">${i("fa-power-off")}Wecker aus</button>` : ruheKnoepfe()}</div>`;
  tel.innerHTML = `<div class="innen"><div class="astro${kl ? " klingelt" : ""}">${svg}${seite}</div></div>`;
}

// ----- G: Polarlicht -------------------------------------------------------------------------------------------------
function aurora(tel, z) {
  const kl = z.lage === "klingelt";
  const unten = kl
    ? `<div style="display:grid;gap:10px"><div class="pillen"><span class="pille w">${i("fa-bell", " fa-shake")}Wecker ${D.weck}</span><span class="pille">${i("fa-radio")}${D.sender}</span></div>
       <div class="pillen"><button class="pille gross voll">${i("fa-bed")}Schlummern 9 min</button><button class="pille gross">${i("fa-power-off")}Aus</button>
       <button class="pille gross${z.quelle === "radio" ? " voll" : ""}">${i("fa-radio")}</button><button class="pille gross${z.quelle === "weckton" ? " voll" : ""}">${i("fa-bell")}</button></div></div>`
    : `<div class="pillen"><span class="pille">${i("fa-radio")}${D.sender}</span><span class="pille w">${weckSymbol(z)}${weckText(z)}</span>
       ${z.lage === "schlummert" ? `<button class="pille">${i("fa-power-off")}Wecker aus</button>` : `<span class="pille">${i("fa-sun")}${D.auf} ${i("fa-moon")}${D.unter}</span>`}</div>`;
  tel.innerHTML = `<div class="innen" style="overflow:hidden"><div class="aurora${kl ? " klingelt" : ""}"><div class="licht"></div><div class="zeit">${z.zeit}</div>${unten}</div></div>`;
}

// ----- H: Röhren -----------------------------------------------------------------------------------------------------
let roehrenNr = 0;
function roehren(tel, z) {
  const [a, b] = z.zeit.split(":");
  const f = z.modus === "nacht" ? { glut: "#ff3a28", kern: "#ffb09a", kalt: "#3a1a14" } : { glut: "#ff7a1a", kern: "#ffe2b0", kalt: "#5a4a3c" };
  const r = (c) => `<div class="roehre-svg">${roehre(c, f, `k${roehrenNr++}`)}</div>`;
  const sockel = z.lage === "klingelt"
    ? `<div class="sockel"><span class="w">${i("fa-bell", " fa-shake")} ${D.weck}</span><span style="display:flex;gap:10px">${quelleWahl(z)}
       <button class="hebel">${i("fa-bed")}Schlummern</button><button class="hebel voll">${i("fa-power-off")}Aus</button></span></div>`
    : `<div class="sockel"><span>${i("fa-radio")} ${D.sender}</span><span style="display:flex;gap:14px;align-items:center"><b>${weckSymbol(z)} ${weckText(z)}</b>
       ${z.lage === "schlummert" ? `<button class="hebel voll">${i("fa-power-off")}Wecker aus</button>` : ""}</span></div>`;
  tel.innerHTML = `<div class="innen"><div class="roehren"><div class="reihe2">${r(a[0])}${r(a[1])}<div class="glimm-feld">${glimmpunkte(f)}</div>${r(b[0])}${r(b[1])}</div>${sockel}</div></div>`;
}

// ----- I: RGB-Pixel (ganz grobes Raster, Nutzer 20.11.2026) ---------------------------------------------------------
const SONNE = [".y.y.", "..y..", "yyyyy", "..y..", ".y.y."];
const MONDBILD = [".mm..", "mm...", "mm...", "mm...", ".mm.."];
const WOLKE = [".ww..", "wwwww", ".www."];
const GLOCKE = ["..g..", ".ggg.", ".ggg.", "ggggg", "..g.."];
const NOTE = [".nn", ".n.", ".n.", "nn.", "nn."];
const BETT = ["b....", "b....", "bbbbb", "b...b"];
function hsl(h, s, l) { return `hsl(${((h % 360) + 360) % 360} ${s}% ${l}%)`; }
// Farben stehen still: kein Lauflicht (Nutzer 20.11.2026)
function pixel(tel, z) {
  // ein RGB-Leuchtfeld ist immer dunkel, auch im Hellmodus (Nutzer 20.11.2026: "Whitemode ist Unsinn bei RGB-Matrix")
  const kl = z.lage === "klingelt", nacht = z.modus === "nacht", hell = false;
  if (!tel.querySelector("canvas")) tel.innerHTML = `<div class="innen" style="background:${hell ? "#e9ebf2" : "#000"};padding:10px 16px 8px 46px"><canvas class="matrix"></canvas></div>`;
  const S = 44, Z = 23, aus = hell ? "#d9dce6" : "#0d0d14";
  const bunt = (x, y) => (nacht ? hsl(2 + y * 1.2, 85, 40) : hsl(x * 8 + y * 6, 95, hell ? 47 : 58));
  const farben = { y: nacht ? "#7a1008" : "#ffd21f", m: nacht ? "#a3140c" : "#cfd8ff", w: nacht ? "#300404" : hell ? "#9aa6bd" : "#6b7690",
    g: nacht ? "#ff3a28" : "#ffb21f", n: nacht ? "#ff3a28" : "#2ef0c8", b: nacht ? "#ff3a28" : "#a78bfa" };
  const e = [], r = [], bilder = [];
  const klein = (text, x, y, farbe) => e.push({ text, x, y, farbe, schrift: "klein" });
  if (kl) {
    bilder.push({ x: 0, y: 0, pixel: GLOCKE, farben }, { x: S - 5, y: 0, pixel: GLOCKE, farben });
    klein(D.weck, Math.round((S - breite(D.weck, 1, "klein")) / 2), 0, farben.g);
    e.push({ text: z.zeit, y: 6, mass: 2, mitte: true, farbe: bunt, schrift: "klein" });
    const felder = [["ZZZ", 0], ["AUS", 15], [z.quelle === "radio" ? "RAD" : "TON", 30]];
    for (const [t, x] of felder) klein(t, x + Math.round((14 - breite(t, 1, "klein")) / 2), 17, bunt);   // ohne Rahmen, die Schrift leuchtet bunt
  } else {
    bilder.push(nacht ? { x: 0, y: 0, pixel: MONDBILD, farben } : { x: 0, y: 0, pixel: SONNE, farben }, { x: 6, y: 1, pixel: WOLKE, farben });
    const w = z.lage === "schlummert" ? D.bis : D.weck;
    bilder.push(z.lage === "schlummert" ? { x: S - breite(w, 1, "klein") - 7, y: 1, pixel: BETT, farben } : { x: S - breite(w, 1, "klein") - 7, y: 0, pixel: GLOCKE, farben });
    klein(w, S - breite(w, 1, "klein"), 0, farben.g);
    e.push({ text: z.zeit, y: 6, mass: 2, mitte: true, farbe: bunt, schrift: "klein" });
    bilder.push({ x: 0, y: 17, pixel: NOTE, farben });
    klein("DLF", 4, 17, farben.n);
    if (z.lage === "schlummert") klein("AUS", S - breite("AUS", 1, "klein"), 17, bunt);
    else klein(D.auf, S - breite(D.auf, 1, "klein"), 17, farben.y);
  }
  zeichnen(tel.querySelector("canvas"), { spalten: S, zeilen: Z, aus, ebenen: e, rahmen: r, bilder, form: "quadrat", glanz: !hell });
}

const GESTALTUNGEN = [
  { id: "uhr", name: "Uhr vollflächig", klasse: "g-uhr", tun: uhr, text: "Die bisherige Gestaltung: die Uhr über die ganze Fläche, unten eine schmale Leiste. Beim Klingeln wird die Uhr kleiner, unten Radio oder Weckton, Schlummern und Aus." },
  { id: "matrix", name: "A Matrixanzeige", klasse: "g-matrix", tun: matrix, text: "Der ganze Bildschirm ist ein Punktfeld mit groben Punkten; hell wie ein Leuchtfeld aus Flüssigkristall, dunkel leuchtend. Beim Klingeln drei Tastenflächen ohne Rahmen (Punktgrafik hat nie Rahmen), nur ihre Schrift leuchtet: Schlummern, Aus, Radio oder Ton." },
  { id: "hifi", name: "B HiFi-Gerät", klasse: "g-hifi", tun: hifi, text: "Gehäuse wie die Abspielleiste, hell in Silber, dunkel in Anthrazit; das Glas bleibt dunkel. Beim Klingeln rechts zwei große Tasten und darunter Radio und Weckton mit Licht." },
  { id: "segment", name: "C Segment-Uhr", klasse: "g-segment", tun: segment, text: "Ziffern aus sieben Segmenten, gedämpfte Segmente dahinter, darunter ein Lauftext. Beim Klingeln eine Zeile mit Radio oder Weckton, Schlummern und Aus." },
  { id: "ruhig", name: "D Ruhig", klasse: "g-ruhig", tun: ruhig, text: "Die aufgeräumte Ansicht mit großer Uhr und Sonnenband; ersetzt die bisherige Sonnen-Ansicht. Beim Klingeln wird die rechte Spalte zu den Tasten." },
  { id: "sterne", name: "E Sternenzeit", klasse: "g-sterne", tun: sterne, text: "Hell ein Morgenhimmel, dunkel der Sternenhimmel mit der Mondphase des Tages. Beim Klingeln geht von unten die Sonne auf." },
  { id: "astro", name: "F Astrolabium", klasse: "g-astro", tun: astro, text: "Hell auf Pergament, dunkel in Gold auf Indigo: der Ring ist der Tag, der Bogen die Sonnenzeit, der helle Punkt der Wecker." },
  { id: "aurora", name: "G Polarlicht", klasse: "g-aurora", tun: aurora, text: "Wabernde Farbschleier, hell als Pastell auf Weiß. Beim Klingeln wogen die Farben schneller, unten Schlummern, Aus, Radio und Weckton als Pillen." },
  { id: "roehren", name: "H Röhren", klasse: "g-roehren", tun: roehren, text: "Glimmdraht-Röhren mit Glaskolben, Anodengitter und Kupferstiften; hell auf hellem Holz, dunkel auf dunklem. Beim Klingeln trägt der Sockel Radio oder Weckton und die Hebel." },
  { id: "pixel", name: "I RGB-Pixel", klasse: "g-pixel", tun: pixel, immerDunkel: true, text: "Verspielte Pixeluhr als ganz grobes Raster aus 44 x 23 großen Leuchtquadraten: Regenbogen über den Ziffern, ohne Lauflicht, kleine Pixelbilder (Sonne, Wolke, Mond, Glocke, Note, Bett). Beim Klingeln unten drei Tastenflächen ohne Rahmen: ZZZ (Schlummern), AUS, RAD oder TON." },
];

function aufbauen() {
  const main = document.querySelector("main"), nav = document.querySelector(".kopf nav");
  for (const g of GESTALTUNGEN) {
    nav.insertAdjacentHTML("beforeend", `<a href="#${g.id}">${g.name}</a>`);
    const felder = ZUSTAENDE.map((z, n) => `<figure><div class="rahmen"><div class="tel ${g.klasse} ${z.modus}" id="${g.id}-${n}"></div></div><figcaption><b>${z.titel}</b>${g.immerDunkel && z.modus === "hell" ? ": Leuchtfeld bleibt dunkel" : ""}</figcaption></figure>`).join("");
    main.insertAdjacentHTML("beforeend", `<h2 id="${g.id}">${g.name}<small>Wischen blättert zur nächsten Gestaltung</small></h2><p class="erkl">${g.text}</p><div class="raster">${felder}</div>`);
  }
  for (const g of GESTALTUNGEN) ZUSTAENDE.forEach((z, n) => g.tun(document.getElementById(`${g.id}-${n}`), z));
}
document.fonts.ready.then(aufbauen);
