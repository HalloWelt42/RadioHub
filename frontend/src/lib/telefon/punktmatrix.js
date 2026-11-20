// Punktmatrix der Weckansicht (RAD-15, aus mockups/weckansicht): Zeichensätze 5 x 7 und 3 x 5, gezeichnet auf ein Canvas
// mit allen Punkten (unbeleuchtet gedämpft, beleuchtet in der Leuchtfarbe). Ebenen: Text an Punktposition mit Vergrößerung,
// Umrisse, Pixelbilder; runde Punkte oder eckige Leuchtquadrate. Ohne Svelte, ohne Zustand.
// @ts-nocheck: Zeichentabellen und Canvas-Zugriffe sind bewusst schlicht gehalten

const Z = {
  "0": ["01110", "10001", "10011", "10101", "11001", "10001", "01110"],
  "1": ["00100", "01100", "00100", "00100", "00100", "00100", "01110"],
  "2": ["01110", "10001", "00001", "00010", "00100", "01000", "11111"],
  "3": ["11110", "00001", "00001", "01110", "00001", "00001", "11110"],
  "4": ["00010", "00110", "01010", "10010", "11111", "00010", "00010"],
  "5": ["11111", "10000", "11110", "00001", "00001", "10001", "01110"],
  "6": ["00110", "01000", "10000", "11110", "10001", "10001", "01110"],
  "7": ["11111", "00001", "00010", "00100", "01000", "01000", "01000"],
  "8": ["01110", "10001", "10001", "01110", "10001", "10001", "01110"],
  "9": ["01110", "10001", "10001", "01111", "00001", "00010", "01100"],
  ":": ["0", "1", "1", "0", "1", "1", "0"],
  ".": ["0", "0", "0", "0", "0", "0", "1"],
  "-": ["000", "000", "000", "111", "000", "000", "000"],
  "/": ["00001", "00010", "00010", "00100", "01000", "01000", "10000"],
  " ": ["000", "000", "000", "000", "000", "000", "000"],
  "A": ["01110", "10001", "10001", "11111", "10001", "10001", "10001"],
  "B": ["11110", "10001", "10001", "11110", "10001", "10001", "11110"],
  "C": ["01110", "10001", "10000", "10000", "10000", "10001", "01110"],
  "D": ["11100", "10010", "10001", "10001", "10001", "10010", "11100"],
  "E": ["11111", "10000", "10000", "11110", "10000", "10000", "11111"],
  "F": ["11111", "10000", "10000", "11110", "10000", "10000", "10000"],
  "G": ["01110", "10001", "10000", "10111", "10001", "10001", "01111"],
  "H": ["10001", "10001", "10001", "11111", "10001", "10001", "10001"],
  "I": ["111", "010", "010", "010", "010", "010", "111"],
  "J": ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
  "K": ["10001", "10010", "10100", "11000", "10100", "10010", "10001"],
  "L": ["10000", "10000", "10000", "10000", "10000", "10000", "11111"],
  "M": ["10001", "11011", "10101", "10101", "10001", "10001", "10001"],
  "N": ["10001", "10001", "11001", "10101", "10011", "10001", "10001"],
  "O": ["01110", "10001", "10001", "10001", "10001", "10001", "01110"],
  "P": ["11110", "10001", "10001", "11110", "10000", "10000", "10000"],
  "Q": ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
  "R": ["11110", "10001", "10001", "11110", "10100", "10010", "10001"],
  "S": ["01111", "10000", "10000", "01110", "00001", "00001", "11110"],
  "T": ["11111", "00100", "00100", "00100", "00100", "00100", "00100"],
  "U": ["10001", "10001", "10001", "10001", "10001", "10001", "01110"],
  "V": ["10001", "10001", "10001", "10001", "10001", "01010", "00100"],
  "W": ["10001", "10001", "10001", "10101", "10101", "10101", "01010"],
  "X": ["10001", "10001", "01010", "00100", "01010", "10001", "10001"],
  "Y": ["10001", "10001", "01010", "00100", "00100", "00100", "00100"],
  "Z": ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
  "Ä": ["01010", "00000", "01110", "10001", "11111", "10001", "10001"],
  "Ö": ["01010", "00000", "01110", "10001", "10001", "10001", "01110"],
  "Ü": ["01010", "00000", "10001", "10001", "10001", "10001", "01110"],
  // Zeichen der Ansicht: Glocke, Sonne, Mond, Note, Bett
  "@": ["00100", "01110", "01110", "01110", "11111", "00000", "00100"],
  "*": ["10101", "01110", "11011", "01110", "10101", "00000", "00000"],
  ")": ["00110", "01100", "11000", "11000", "11000", "01100", "00110"],
  "#": ["00011", "00101", "01001", "01001", "01011", "11011", "11000"],
  "~": ["10000", "10000", "10111", "11111", "11111", "10001", "00000"],
  "|": ["11011", "11011", "11011", "11011", "11011", "11011", "11011"],
  ">": ["10000", "11000", "11100", "11110", "11100", "11000", "10000"],
  "!": ["1", "1", "1", "1", "1", "0", "1"],
};

// Winzige Pixelschrift 3 x 5 für ganz grobe Raster (RGB-Pixeluhr)
const K = {
  "0": ["111", "101", "101", "101", "111"], "1": ["010", "110", "010", "010", "111"], "2": ["111", "001", "111", "100", "111"],
  "3": ["111", "001", "111", "001", "111"], "4": ["101", "101", "111", "001", "001"], "5": ["111", "100", "111", "001", "111"],
  "6": ["111", "100", "111", "101", "111"], "7": ["111", "001", "010", "010", "010"], "8": ["111", "101", "111", "101", "111"],
  "9": ["111", "101", "111", "001", "111"], ":": ["0", "1", "0", "1", "0"], " ": ["00", "00", "00", "00", "00"],
  "A": ["010", "101", "111", "101", "101"], "U": ["101", "101", "101", "101", "111"], "S": ["111", "100", "111", "001", "111"],
  "D": ["110", "101", "101", "101", "110"], "L": ["100", "100", "100", "100", "111"], "F": ["111", "100", "110", "100", "100"],
  "R": ["110", "101", "110", "101", "101"], "T": ["111", "010", "010", "010", "010"], "O": ["111", "101", "101", "101", "111"],
  "N": ["101", "111", "111", "111", "101"], "Z": ["111", "001", "010", "100", "111"], "E": ["111", "100", "110", "100", "111"],
  "I": ["1", "1", "1", "1", "1"], ">": ["100", "110", "111", "110", "100"], "-": ["000", "000", "111", "000", "000"],
};
const satz = (schrift) => (schrift === "klein" ? K : Z);

/** Text für die Punktschrift: Großbuchstaben, Trennstriche "|" als "-" (der Strich ist das Zeichen für Pause), ß als SS
 * @param {string} text @returns {string} */
export function fuerMatrix(text) {
  return (text || "").replace(/\s*\|\s*/g, " - ").replace(/ß/g, "ss").toUpperCase();
}

/** Breite eines Textes in Punkten (Zeichen plus eine Spalte Abstand); schrift "klein" ist die 3 x 5
 * @param {string} text @param {number} [mass] @param {string} [schrift] @returns {number} */
export function breite(text, mass = 1, schrift) {
  const s = satz(schrift);
  let b = 0;
  for (const z of text.toUpperCase()) b += ((s[z] ?? s[" "])[0].length + 1) * mass;
  return Math.max(0, b - mass);
}

/**
 * Zeichnet ein Punktfeld. `ebenen`: { text, x, y, mass, farbe, mitte } (x, y in Punkten; mitte: waagrecht zentriert;
 * farbe auch als Funktion (x, y) für Verläufe); `rahmen`: { x, y, b, h, farbe } als Umriss aus Punkten (Tastenfelder);
 * `bilder`: { x, y, pixel: ["..ab..", ...], farben: { a: "#f00" } } als Pixelbilder; `form`: "rund" (Vorgabe) oder
 * "quadrat" (RGB-Leuchtfeld mit schmalen Fugen); `glanz`: Leuchthof um beleuchtete Punkte (Vorgabe ja).
 * @param {HTMLCanvasElement} canvas
 * @param {{ spalten: number, zeilen: number, aus: string, ebenen?: any[], rahmen?: any[], bilder?: any[], form?: string, glanz?: boolean }} feld
 */
export function zeichnen(canvas, { spalten, zeilen, aus, ebenen = [], rahmen = [], bilder = [], form = "rund", glanz = true }) {
  const pixel = window.devicePixelRatio || 1;
  const w = canvas.clientWidth, h = canvas.clientHeight;
  canvas.width = w * pixel; canvas.height = h * pixel;
  const g = canvas.getContext("2d");
  g.scale(pixel, pixel);
  const schritt = Math.min(w / spalten, h / zeilen);
  const ox = (w - schritt * spalten) / 2, oy = (h - schritt * zeilen) / 2;
  const feld = Array.from({ length: zeilen }, () => Array(spalten).fill(null));
  const setzen = (x, y, f) => { if (x >= 0 && y >= 0 && x < spalten && y < zeilen) feld[y][x] = f; };
  const farbeAn = (f, x, y) => (typeof f === "function" ? f(x, y) : f);
  for (const r of rahmen) {
    for (let i = 0; i < r.b; i++) { setzen(r.x + i, r.y, farbeAn(r.farbe, r.x + i, r.y)); setzen(r.x + i, r.y + r.h - 1, farbeAn(r.farbe, r.x + i, r.y + r.h - 1)); }
    for (let j = 0; j < r.h; j++) { setzen(r.x, r.y + j, farbeAn(r.farbe, r.x, r.y + j)); setzen(r.x + r.b - 1, r.y + j, farbeAn(r.farbe, r.x + r.b - 1, r.y + j)); }
  }
  for (const b of bilder) b.pixel.forEach((reihe, y) => [...reihe].forEach((z, x) => { if (b.farben[z]) setzen(b.x + x, b.y + y, b.farben[z]); }));
  for (const e of ebenen) {
    const m = e.mass ?? 1;
    const s = satz(e.schrift);
    let x = e.mitte ? Math.round((spalten - breite(e.text, m, e.schrift)) / 2) + (e.x ?? 0) : e.x;
    for (const z of e.text.toUpperCase()) {
      const glyphe = s[z] ?? s[" "];
      glyphe.forEach((reihe, gy) => [...reihe].forEach((p, gx) => {
        if (p === "1") for (let a = 0; a < m; a++) for (let b = 0; b < m; b++) {
          const px = x + gx * m + a, py = e.y + gy * m + b;
          setzen(px, py, farbeAn(e.farbe, px, py));
        }
      }));
      x += (glyphe[0].length + 1) * m;
    }
  }
  const radius = schritt * 0.38, kante = schritt * 0.84;
  for (let y = 0; y < zeilen; y++) for (let x = 0; x < spalten; x++) {
    const f = feld[y][x];
    g.beginPath();
    if (form === "quadrat") g.roundRect(ox + x * schritt + (schritt - kante) / 2, oy + y * schritt + (schritt - kante) / 2, kante, kante, schritt * 0.12);
    else g.arc(ox + (x + 0.5) * schritt, oy + (y + 0.5) * schritt, radius, 0, Math.PI * 2);
    g.fillStyle = f ?? aus;
    if (f && glanz) { g.shadowColor = f; g.shadowBlur = schritt * 0.9; } else g.shadowBlur = 0;
    g.fill();
  }
}
