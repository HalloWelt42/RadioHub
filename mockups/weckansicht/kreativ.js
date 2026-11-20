// Kreative Entwürfe E bis H der Weckansicht (RAD-15), gleiche Beispieldaten wie A bis D.

const innen = (tel, html) => { tel.innerHTML = `<div class="innen">${html}</div>`; };
const KNOPF = (i, text, klasse) => `<button class="${klasse}"><i class="fa-solid ${i}"></i>${text}</button>`;

// ----- E: Sternenzeit ------------------------------------------------------------------------------------------------
function himmel(canvas, nacht) {
  const p = window.devicePixelRatio || 1, w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * p; canvas.height = h * p;
  const g = canvas.getContext("2d"); g.scale(p, p);
  let s = 7;
  const zufall = () => ((s = (s * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 260; i++) {
    const r = zufall() ** 3 * 1.8 + 0.3;
    g.beginPath(); g.arc(zufall() * w, zufall() * h, r, 0, Math.PI * 2);
    g.fillStyle = nacht ? `rgba(200,30,20,${0.25 + zufall() * 0.5})` : `rgba(${200 + zufall() * 55},${210 + zufall() * 45},255,${0.35 + zufall() * 0.65})`;
    g.shadowColor = g.fillStyle; g.shadowBlur = r * 4; g.fill();
  }
}
/** Mondphase am Tag (0 Neumond, 0,5 Vollmond) und als SVG */
function mondphase(d) {
  const neumond = Date.UTC(2000, 0, 6, 18, 14);
  return (((d - neumond) / 86400000 / 29.530588) % 1 + 1) % 1;
}
function mond(phase, nacht) {
  const r = 46, hell = nacht ? "#7e1210" : "#f3ecd2", dunkel = nacht ? "#140203" : "#1a1838";
  const zu = phase < 0.5;                      // zunehmend: rechts hell
  const k = Math.cos(phase * 2 * Math.PI) * r; // Breite der Schattengrenze
  const bogen = `M 50 ${50 - r} A ${r} ${r} 0 0 ${zu ? 1 : 0} 50 ${50 + r} A ${Math.abs(k)} ${r} 0 0 ${(k > 0) === zu ? 0 : 1} 50 ${50 - r}`;
  return `<svg viewBox="0 0 100 100" width="104" height="104"><circle cx="50" cy="50" r="${r}" fill="${dunkel}"/>
    <path d="${bogen}" fill="${hell}" style="filter: drop-shadow(0 0 8px ${hell})"/></svg>`;
}
function sterneE(id, { zeit, klingelt = false }) {
  const tel = document.getElementById(id), nacht = tel.classList.contains("nacht");
  const phase = mondphase(new Date(2026, 10, 20));
  const name = phase < 0.03 || phase > 0.97 ? "Neumond" : phase < 0.47 ? "zunehmender Mond" : phase < 0.53 ? "Vollmond" : "abnehmender Mond";
  const rechts = klingelt
    ? `<div class="kugeln">${KNOPF("fa-bed", "9 min", "kugel sonne")}${KNOPF("fa-power-off", "Aus", "kugel still")}</div>`
    : `<div class="mond">${mond(phase, nacht)}<span>${name}</span><span><i class="fa-solid fa-sun"></i> 07:58 <i class="fa-solid fa-moon"></i> 16:21</span></div>`;
  innen(tel, `<div class="sterne${klingelt ? " klingelt" : ""}"><canvas class="himmel"></canvas>
    <div><div class="zeit">${zeit}</div><div class="unter"><span class="w"><i class="fa-solid fa-bell${klingelt ? " fa-shake" : ""}"></i> ${klingelt ? "Wecker 06:30" : "Mo 06:30"}</span>
    <span><i class="fa-solid fa-radio"></i> Deutschlandfunk</span></div></div>${rechts}</div>`);
  if (!klingelt) himmel(tel.querySelector("canvas"), nacht);
}

// ----- F: Astrolabium ------------------------------------------------------------------------------------------------
const punkt = (stunde, r) => { const a = (stunde / 24) * 2 * Math.PI - Math.PI / 2; return [181 + Math.cos(a) * r, 181 + Math.sin(a) * r]; };
const minuten = (hhmm) => { const [h, m] = hhmm.split(":").map(Number); return h + m / 60; };
function astroF(id, { zeit, klingelt = false }) {
  const tel = document.getElementById(id), nacht = tel.classList.contains("nacht");
  const gold = nacht ? "#b81f19" : "#e6cf93", tag = nacht ? "#3a0505" : "#f2b84a";
  const [ax, ay] = punkt(minuten("07:58"), 160), [ux, uy] = punkt(minuten("16:21"), 160);
  const groesser = minuten("16:21") - minuten("07:58") > 12 ? 1 : 0;
  let striche = "";
  for (let s = 0; s < 24; s++) {
    const [x1, y1] = punkt(s, s % 3 ? 150 : 144), [x2, y2] = punkt(s, 156);
    striche += `<line x1="${x1}" y1="${y1}" x2="${x2}" y2="${y2}" stroke="${gold}" stroke-width="${s % 3 ? 1 : 2}"/>`;
    if (s % 3 === 0) { const [tx, ty] = punkt(s, 130); striche += `<text class="klein" x="${tx}" y="${ty + 4}">${s}</text>`; }
  }
  let minutenring = "";
  const min = Number(zeit.split(":")[1]);
  for (let m = 0; m < 60; m++) {
    const a = (m / 60) * 2 * Math.PI - Math.PI / 2, r1 = m === min ? 92 : 100, r2 = 106;
    minutenring += `<line x1="${181 + Math.cos(a) * r1}" y1="${181 + Math.sin(a) * r1}" x2="${181 + Math.cos(a) * r2}" y2="${181 + Math.sin(a) * r2}"
      stroke="${gold}" stroke-width="${m === min ? 3 : 1}" opacity="${m === min ? 1 : 0.45}"/>`;
  }
  const [jx, jy] = punkt(minuten(zeit), 166), [wx, wy] = punkt(minuten("06:30"), 160);
  const svg = `<svg viewBox="0 0 362 362" style="color:${gold}">
    <circle class="ring" cx="181" cy="181" r="174" stroke-width="1" opacity=".5"/>
    <circle class="ring puls" cx="181" cy="181" r="160" stroke-width="1" opacity=".35"/>
    <path d="M ${ax} ${ay} A 160 160 0 ${groesser} 1 ${ux} ${uy}" fill="none" stroke="${tag}" stroke-width="8" stroke-linecap="round" opacity=".85"/>
    ${striche}${minutenring}
    <circle cx="${wx}" cy="${wy}" r="${klingelt ? 11 : 8}" fill="${nacht ? "#d4231c" : "#ffdf8c"}" class="puls" style="filter: drop-shadow(0 0 8px ${nacht ? "#d4231c" : "#ffdf8c"})"/>
    <line x1="181" y1="181" x2="${jx}" y2="${jy}" stroke="${gold}" stroke-width="2" opacity=".6"/>
    <circle cx="${jx}" cy="${jy}" r="5" fill="${gold}"/>
    <text class="zahl" x="181" y="204">${zeit}</text><text class="klein" x="181" y="232">FR 20. NOVEMBER</text></svg>`;
  const seite = klingelt
    ? `<div class="seite"><span class="w"><i class="fa-solid fa-bell fa-shake"></i> 06:30</span><span>Deutschlandfunk</span>
       ${KNOPF("fa-bed", "Schlummern", "siegel voll")}${KNOPF("fa-power-off", "Aus", "siegel")}</div>`
    : `<div class="seite"><span class="w"><i class="fa-solid fa-bell"></i> Mo 06:30</span><span><i class="fa-solid fa-radio"></i> Deutschlandfunk</span>
       <span class="leise">Tag von 07:58 bis 16:21, der goldene Bogen; der helle Punkt ist der Wecker</span></div>`;
  innen(tel, `<div class="astro${klingelt ? " klingelt" : ""}">${svg}${seite}</div>`);
}

// ----- G: Polarlicht -------------------------------------------------------------------------------------------------
function auroraG(id, { zeit, klingelt = false }) {
  const tel = document.getElementById(id);
  const unten = klingelt
    ? `<div style="display:grid;gap:10px"><div class="pillen"><span class="pille w"><i class="fa-solid fa-bell fa-shake"></i>Wecker 06:30</span>
       <span class="pille"><i class="fa-solid fa-radio"></i>Deutschlandfunk</span></div>
       <div class="pillen">${KNOPF("fa-bed", "Schlummern 9 min", "pille gross voll")}${KNOPF("fa-power-off", "Aus", "pille gross")}</div></div>`
    : `<div class="pillen"><span class="pille"><i class="fa-solid fa-radio"></i>Deutschlandfunk</span><span class="pille w"><i class="fa-solid fa-bell"></i>Mo 06:30</span>
       <span class="pille"><i class="fa-solid fa-sun"></i>07:58 <i class="fa-solid fa-moon"></i>16:21</span></div>`;
  innen(tel, `<div class="aurora${klingelt ? " klingelt" : ""}"><div class="licht"></div><div class="zeit">${zeit}</div>${unten}</div>`);
}

// ----- H: Röhren -----------------------------------------------------------------------------------------------------
function roehrenH(id, { zeit, klingelt = false }) {
  const tel = document.getElementById(id);
  const [a, b] = zeit.split(":");
  const roehre = (z) => `<div class="roehre"><b>${z}</b></div>`;
  const sockel = klingelt
    ? `<div class="sockel"><span class="w"><i class="fa-solid fa-bell fa-shake"></i> Wecker 06:30 · Deutschlandfunk</span>
       <span style="display:flex;gap:12px">${KNOPF("fa-bed", "Schlummern", "hebel")}${KNOPF("fa-power-off", "Aus", "hebel aus")}</span></div>`
    : `<div class="sockel"><span><i class="fa-solid fa-radio"></i> Deutschlandfunk</span><span class="w"><i class="fa-solid fa-bell"></i> Mo 06:30</span></div>`;
  innen(tel, `<div class="roehren"><div class="reihe2">${roehre(a[0])}${roehre(a[1])}<div class="punkt"><span></span><span></span></div>${roehre(b[0])}${roehre(b[1])}</div>${sockel}</div>`);
}

function alles() {
  for (const [f, k] of [[sterneE, "e"], [astroF, "f"], [auroraG, "g"], [roehrenH, "h"]]) {
    f(`${k}-tag`, { zeit: "06:42" }); f(`${k}-nacht`, { zeit: "02:17" }); f(`${k}-klingelt`, { zeit: "06:30", klingelt: true });
  }
}
document.fonts.ready.then(alles);
