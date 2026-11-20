// Ziffernröhren mit Glimmdraht (RAD-15, Entwurf H2): jede Ziffer ist ein einzelner Draht (Mittellinie), die übrigen
// neun Ziffern stehen ungeglüht dahinter, davor das Anodengitter, außen der Glaskolben mit Spiegelung und der Sockel.

/** Mittellinien der Ziffern in einem Feld 60 x 100 */
export const DRAHT = {
  0: "M30 8 C48 8 52 30 52 50 C52 72 48 92 30 92 C12 92 8 72 8 50 C8 30 12 8 30 8 Z",
  1: "M22 18 L32 8 L32 92",
  2: "M10 28 C10 4 50 4 50 28 C50 48 12 62 10 92 L52 92",
  3: "M10 16 C22 4 50 6 48 26 C47 40 36 46 26 48 C44 48 52 60 52 70 C52 92 20 98 8 84",
  4: "M42 92 L42 8 L8 66 L54 66",
  5: "M50 8 L16 8 L12 44 C24 36 52 38 52 64 C52 90 22 96 9 84",
  6: "M46 11 C26 4 9 26 9 60 C9 82 20 92 31 92 C45 92 52 80 52 66 C52 52 44 42 31 42 C19 42 11 50 9 60",
  7: "M8 8 L52 8 C40 30 28 60 24 92",
  8: "M30 8 C42 8 48 16 48 27 C48 38 40 46 30 46 C20 46 12 38 12 27 C12 16 18 8 30 8 Z M30 46 C44 46 52 56 52 69 C52 83 42 92 30 92 C18 92 8 83 8 69 C8 56 16 46 30 46 Z",
  9: "M51 40 C49 52 41 58 30 58 C18 58 9 48 9 34 C9 18 19 8 30 8 C45 8 52 22 52 40 C52 70 40 92 16 89",
};
// Reihenfolge von vorn nach hinten wie in echten Röhren (die vorderste verdeckt am wenigsten)
const STAPEL = [1, 6, 2, 7, 5, 0, 4, 9, 8, 3];

/** Eine Röhre als SVG; `farbe`: { glut, kern, kalt } */
export function roehre(ziffer, farbe, kennung) {
  const hinten = STAPEL.filter((z) => z !== Number(ziffer)).reverse()
    .map((z, i) => `<path d="${DRAHT[z]}" transform="translate(${0.6 * (i % 3) - 0.6} ${0.4 * (i % 2)})" stroke="${farbe.kalt}" stroke-width="1.6" opacity="${0.35 + i * 0.04}"/>`).join("");
  const id = `g${kennung}`;
  return `<svg viewBox="-34 -40 128 190" class="nixie">
    <defs>
      <radialGradient id="${id}-glas" cx="50%" cy="35%" r="75%"><stop offset="0" stop-color="#ffffff" stop-opacity=".07"/><stop offset=".6" stop-color="#ffffff" stop-opacity=".02"/><stop offset="1" stop-color="#000" stop-opacity=".35"/></radialGradient>
      <linearGradient id="${id}-licht" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".18" stop-color="#fff" stop-opacity=".22"/><stop offset=".26" stop-color="#fff" stop-opacity="0"/><stop offset=".84" stop-color="#fff" stop-opacity=".07"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <radialGradient id="${id}-hof" cx="50%" cy="50%" r="50%"><stop offset="0" stop-color="${farbe.glut}" stop-opacity=".35"/><stop offset="1" stop-color="${farbe.glut}" stop-opacity="0"/></radialGradient>
      <pattern id="${id}-gitter" width="5" height="8.66" patternUnits="userSpaceOnUse"><path d="M0 0 L2.5 4.33 L0 8.66 M5 0 L2.5 4.33 L5 8.66" fill="none" stroke="#9a8a78" stroke-width=".35"/></pattern>
      <filter id="${id}-glimm" x="-40%" y="-40%" width="180%" height="180%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="1.2" result="nah"/><feGaussianBlur in="SourceGraphic" stdDeviation="5" result="fern"/>
        <feMerge><feMergeNode in="fern"/><feMergeNode in="fern"/><feMergeNode in="nah"/><feMergeNode in="SourceGraphic"/></feMerge>
      </filter>
    </defs>
    <!-- Kolben -->
    <path d="M-24 -10 C-24 -36 84 -36 84 -10 L84 128 L-24 128 Z" fill="url(#${id}-glas)" stroke="#d8c8b0" stroke-opacity=".22" stroke-width="1"/>
    <ellipse cx="30" cy="50" rx="44" ry="62" fill="url(#${id}-hof)"/>
    <g fill="none" stroke-linecap="round" stroke-linejoin="round">${hinten}
      <path d="${DRAHT[ziffer]}" stroke="${farbe.glut}" stroke-width="3.2" filter="url(#${id}-glimm)"/>
      <path d="${DRAHT[ziffer]}" stroke="${farbe.kern}" stroke-width="1.1"/>
    </g>
    <!-- Anodengitter vor den Ziffern, Halterungen -->
    <rect x="-14" y="-4" width="88" height="108" fill="url(#${id}-gitter)" opacity=".55"/>
    <path d="M-14 -4 L-14 104 M74 -4 L74 104" stroke="#8d7c68" stroke-width="1.2" opacity=".6"/>
    <!-- Spiegelung, Sockel, Stifte -->
    <path d="M-24 -10 C-24 -36 84 -36 84 -10 L84 128 L-24 128 Z" fill="url(#${id}-licht)"/>
    <rect x="-26" y="126" width="112" height="16" rx="3" fill="#1a1410" stroke="#4a3a2a" stroke-width="1"/>
    <path d="M-10 142 v6 M8 142 v6 M26 142 v6 M44 142 v6 M62 142 v6" stroke="#8d7c68" stroke-width="2"/>
  </svg>`;
}

/** Glimmlampe für den Doppelpunkt */
export function glimmpunkte(farbe) {
  const punkt = (y) => `<g><ellipse cx="10" cy="${y}" rx="7" ry="10" fill="#ffffff" fill-opacity=".05" stroke="#d8c8b0" stroke-opacity=".2"/>
    <circle cx="10" cy="${y}" r="3.2" fill="${farbe.glut}" style="filter: drop-shadow(0 0 4px ${farbe.glut}) drop-shadow(0 0 10px ${farbe.glut})"/></g>`;
  return `<svg viewBox="0 0 20 150" class="glimm">${punkt(50)}${punkt(92)}</svg>`;
}
