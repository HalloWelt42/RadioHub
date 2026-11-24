// Der Nachbar in einer Reihe (Folgen eines Podcasts, Titel einer Aufnahme) nach der gewählten Reihenfolge. Eine Regel für die
// Tasten Zurück und Vor, ihre Beschriftung und das Ende eines Stücks: linear endet an den Rändern, rückwärts dreht die Richtung
// um, die Schleife läuft rundum, Zufall wählt irgendeinen anderen.

/**
 * @param {number} laenge
 * @param {number} stelle jetzige Stelle, -1 wenn unbekannt
 * @param {-1 | 1} schritt
 * @param {string} reihenfolge linear, reverse, loop oder shuffle
 * @returns {number | null} die Stelle des Nachbarn; null, wenn es keinen gibt
 */
export function nachbarstelle(laenge, stelle, schritt, reihenfolge) {
  if (laenge < 2 || stelle < 0) return null;
  if (reihenfolge === 'shuffle') return (stelle + 1 + Math.floor(Math.random() * (laenge - 1))) % laenge;
  const ziel = stelle + (reihenfolge === 'reverse' ? -schritt : schritt);
  if (reihenfolge === 'loop') return (ziel + laenge) % laenge;
  return ziel >= 0 && ziel < laenge ? ziel : null;
}
