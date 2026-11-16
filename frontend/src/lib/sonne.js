/**
 * Sonnenaufgang und -untergang, lokal berechnet (Näherung der NOAA, Genauigkeit etwa eine Minute in unseren
 * Breiten). Keine Anfrage an fremde Dienste.
 */

const RAD = Math.PI / 180;

function julianischerTag(datum) {
  return datum.getTime() / 86400000 + 2440587.5;
}

/**
 * @param {Date} tag - irgendein Zeitpunkt des gewünschten Tages (Ortszeit)
 * @param {number} breite - Grad Nord positiv
 * @param {number} laenge - Grad Ost positiv
 * @returns {{ aufgang: Date|null, untergang: Date|null, polar: null|'tag'|'nacht' }}
 */
export function sonnenzeiten(tag, breite, laenge) {
  const mittag = new Date(tag.getFullYear(), tag.getMonth(), tag.getDate(), 12, 0, 0);
  const n = Math.round(julianischerTag(mittag) - 2451545.0 + 0.0008);
  const mittlererMittag = n - laenge / 360;
  const anomalie = (357.5291 + 0.98560028 * mittlererMittag) % 360;
  const m = anomalie * RAD;
  const mittelpunkt = 1.9148 * Math.sin(m) + 0.02 * Math.sin(2 * m) + 0.0003 * Math.sin(3 * m);
  const ekliptik = ((anomalie + mittelpunkt + 180 + 102.9372) % 360) * RAD;
  const transit = 2451545.0 + mittlererMittag + 0.0053 * Math.sin(m) - 0.0069 * Math.sin(2 * ekliptik);
  const deklination = Math.asin(Math.sin(ekliptik) * Math.sin(23.44 * RAD));
  const cosStunde = (Math.sin(-0.833 * RAD) - Math.sin(breite * RAD) * Math.sin(deklination))
    / (Math.cos(breite * RAD) * Math.cos(deklination));
  if (cosStunde > 1) return { aufgang: null, untergang: null, polar: 'nacht' };
  if (cosStunde < -1) return { aufgang: null, untergang: null, polar: 'tag' };
  const stunde = Math.acos(cosStunde) / RAD;
  const zuDatum = (jd) => new Date((jd - 2440587.5) * 86400000);
  return { aufgang: zuDatum(transit - stunde / 360), untergang: zuDatum(transit + stunde / 360), polar: null };
}

/** Ist es zum Zeitpunkt Nacht (nach Untergang oder vor Aufgang)? Ohne Ort: null. */
export function istNacht(jetzt, breite, laenge) {
  if (breite == null || laenge == null) return null;
  const z = sonnenzeiten(jetzt, breite, laenge);
  if (z.polar) return z.polar === 'nacht';
  return jetzt < z.aufgang || jetzt >= z.untergang;
}
