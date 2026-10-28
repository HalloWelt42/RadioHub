/** Wecker und Ort aus dem Backend, einmal geladen und von Weckerliste, Weckeransicht und Einstellungen geteilt. */
import { api } from '../api.js';

export const weckerdaten = $state({ liste: [], ort: { name: '', breite: null, laenge: null }, geladen: false });

export async function weckerLaden() {
  try {
    const [w, o] = await Promise.all([api.getWecker(), api.getOrt()]);
    weckerdaten.liste = w.wecker || [];
    weckerdaten.ort = o;
    weckerdaten.geladen = true;
  } catch {
    weckerdaten.geladen = false;
  }
}

export async function weckerSpeichern(wecker) {
  const gespeichert = await api.saveWecker(wecker);
  const rest = weckerdaten.liste.filter((w) => w.id !== gespeichert.id);
  weckerdaten.liste = [...rest, gespeichert].sort((a, b) => a.zeit.localeCompare(b.zeit));
  return gespeichert;
}

export async function weckerLoeschen(id) {
  await api.deleteWecker(id);
  weckerdaten.liste = weckerdaten.liste.filter((w) => w.id !== id);
}

export async function ortSpeichern(ort) {
  weckerdaten.ort = await api.saveOrt(ort);
}
