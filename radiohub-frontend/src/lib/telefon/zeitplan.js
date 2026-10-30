/**
 * Wann die Weckeransicht von selbst die Zeit ansagt, rein rechnend. Eingestellt wird unabhängig vom Wecker:
 * an oder aus, Abstand in Minuten, ein Zeitraum (von, bis; leer = immer, auch über Mitternacht) und ob nur bei
 * scharfem Wecker oder immer. Beim Wecken gilt der Wecker, bis er aus ist: während er klingelt keine Ansage,
 * beim Schlummern alle SCHLUMMER_ABSTAND_MIN Minuten, gleich welcher Zeitraum, Abstand oder welche Bedingung.
 */

export const ABSTAENDE_MIN = [5, 10, 15, 30, 60];
export const BEDINGUNGEN = ['wecker', 'immer'];
export const SCHLUMMER_ABSTAND_MIN = 5;
export const ZEITRAUM_SCHRITT_MIN = 30;
export const PLAN_VORGABE = Object.freeze({ abstand: 5, von: '', bis: '', bedingung: 'wecker' });

const UHRZEIT = /^([01]\d|2[0-3]):[0-5]\d$/;

/** Gespeicherten Plan prüfen: Unbekanntes fällt auf die Vorgabe zurück. */
export function planPruefen(roh) {
  const p = roh && typeof roh === 'object' ? roh : {};
  return {
    abstand: ABSTAENDE_MIN.includes(p.abstand) ? p.abstand : PLAN_VORGABE.abstand,
    von: UHRZEIT.test(p.von) ? p.von : '',
    bis: UHRZEIT.test(p.bis) ? p.bis : '',
    bedingung: BEDINGUNGEN.includes(p.bedingung) ? p.bedingung : PLAN_VORGABE.bedingung
  };
}

/** Wählbare Grenzen des Zeitraums: 00:00, 00:30 ... 23:30. */
export function zeitraumZeiten(schritt = ZEITRAUM_SCHRITT_MIN) {
  const zwei = (n) => String(n).padStart(2, '0');
  return Array.from({ length: (24 * 60) / schritt }, (_, i) => `${zwei(Math.floor((i * schritt) / 60))}:${zwei((i * schritt) % 60)}`);
}

function minuteAmTag(uhrzeit) {
  const [h, m] = uhrzeit.split(':').map(Number);
  return h * 60 + m;
}

/** Liegt `jetzt` im Zeitraum (Grenzen eingeschlossen)? Ohne von oder bis immer. */
export function imZeitraum(plan, jetzt) {
  if (!plan.von || !plan.bis) return true;
  const x = jetzt.getHours() * 60 + jetzt.getMinutes();
  const von = minuteAmTag(plan.von);
  const bis = minuteAmTag(plan.bis);
  return von <= bis ? x >= von && x <= bis : x >= von || x <= bis;
}

/**
 * Soll in der Minute von `jetzt` angesagt werden?
 * einstellung: { an, abstand, von, bis, bedingung }; lage: { weckerScharf, schlummert, klingelt }
 */
export function ansageFaellig(einstellung, jetzt, { weckerScharf = false, schlummert = false, klingelt = false } = {}) {
  if (!einstellung.an || klingelt) return false;
  const minute = jetzt.getHours() * 60 + jetzt.getMinutes();
  if (schlummert) return minute % SCHLUMMER_ABSTAND_MIN === 0;
  if (einstellung.bedingung === 'wecker' && !weckerScharf) return false;
  return imZeitraum(einstellung, jetzt) && minute % einstellung.abstand === 0;
}
