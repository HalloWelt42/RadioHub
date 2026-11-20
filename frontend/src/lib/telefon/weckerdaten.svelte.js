/** Wecker und Ort, einmal geladen und von Weckerliste, Weckeransicht und Einstellungen geteilt; woher, sagt das Bauziel
 *  (volle App: Backend, Basic: Speicher des Browsers). */
import { weckerablage } from '$ziel/telefon';

export const weckerdaten = $state({ liste: [], ort: { name: '', breite: null, laenge: null }, geladen: false });

export async function weckerLaden() {
  try {
    const [w, o] = await Promise.all([weckerablage.liste(), weckerablage.ort()]);
    weckerdaten.liste = w;
    weckerdaten.ort = o;
    weckerdaten.geladen = true;
  } catch {
    weckerdaten.geladen = false;
  }
}

export async function weckerSpeichern(wecker) {
  const gespeichert = await weckerablage.speichern(wecker);
  const rest = weckerdaten.liste.filter((w) => w.id !== gespeichert.id);
  weckerdaten.liste = [...rest, gespeichert].sort((a, b) => a.zeit.localeCompare(b.zeit));
  return gespeichert;
}

export async function weckerLoeschen(id) {
  await weckerablage.loeschen(id);
  weckerdaten.liste = weckerdaten.liste.filter((w) => w.id !== id);
}

export async function ortSpeichern(ort) {
  weckerdaten.ort = await weckerablage.ortSetzen(ort);
}
