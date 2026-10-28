/**
 * Wecker: nächster Zeitpunkt aus Uhrzeit und Wochentagen (1 = Montag bis 7 = Sonntag), rein rechnend.
 */

function wochentag(datum) {
  const t = datum.getDay();
  return t === 0 ? 7 : t;
}

/** Nächster Zeitpunkt eines Weckers ab `jetzt` (ausschließlich der laufenden Minute), sonst null. */
export function naechsterZeitpunkt(wecker, jetzt = new Date()) {
  if (!wecker?.aktiv || !wecker.tage?.length) return null;
  const [h, m] = wecker.zeit.split(':').map(Number);
  for (let i = 0; i <= 7; i++) {
    const kandidat = new Date(jetzt.getFullYear(), jetzt.getMonth(), jetzt.getDate() + i, h, m, 0, 0);
    if (kandidat > jetzt && wecker.tage.includes(wochentag(kandidat))) return kandidat;
  }
  return null;
}

/** Der Wecker, der als nächster klingelt: { wecker, zeitpunkt } oder null. */
export function naechsterWecker(liste, jetzt = new Date()) {
  let best = null;
  for (const w of liste || []) {
    const z = naechsterZeitpunkt(w, jetzt);
    if (z && (!best || z < best.zeitpunkt)) best = { wecker: w, zeitpunkt: z };
  }
  return best;
}

/** Klingelt ein Wecker in dieser Minute? (genau die Minute von Uhrzeit und Wochentag) */
export function faelligInMinute(wecker, jetzt = new Date()) {
  if (!wecker?.aktiv) return false;
  const [h, m] = wecker.zeit.split(':').map(Number);
  return jetzt.getHours() === h && jetzt.getMinutes() === m && wecker.tage.includes(wochentag(jetzt));
}

