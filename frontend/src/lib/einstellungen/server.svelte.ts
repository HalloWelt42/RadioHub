// Einstellungen für alle Geräte (RAD-11): die Felder des Servermodells über die Einstellungsschicht des Appkerns
// (GET und PATCH /api/v1/einstellungen, Entwurf bis Speichern). Dazu Teil-Entwürfe mit eigenem Weg (etwa der Ort über
// die Weckerablage, in Basic im Browser), die wie Server-Werte in der Leiste Speichern warten. Die Leiste fragt nur
// diese Schicht. In Basic gibt es keine Server-Felder (Bauziel: EINSTELLUNGEN.server).
import {
  einstellungen, einstellungenLaden, einstellungenSpeichern, einstellungenVerwerfen, einstellungsAngebot,
  einstellungsFeld, einstellungSetzen, einstellungsWert,
} from "appkern-oberflaeche";
import { EINSTELLUNGEN } from "$ziel/einstellungen";
import { anzeigeeinheit, wahlwert, zeileAusFeld } from "./aus-feld";
import type { Teilentwurf, Wahlwert, Zeile } from "./typen";
import { wirkungen } from "./wirkung";

export const amServer: boolean = EINSTELLUNGEN.server;

const teile = $state<Record<string, Teilentwurf>>({});
let geladen = $state(false);
let ladeFehler = $state("");

export const serverstand = {
  get geladen() { return geladen; },
  get fehler() { return ladeFehler; },
};

export async function laden(): Promise<void> {
  if (!amServer) return;
  try {
    await einstellungenLaden();
    ladeFehler = "";
    geladen = true;
  } catch (f) {
    ladeFehler = (f as Error).message;
  }
}

/** Die Zeile eines Server-Felds, null, wenn es das Feld (noch) nicht gibt */
export function zeile(name: string): Zeile | null {
  const feld = einstellungsFeld(name);
  return feld ? zeileAusFeld(feld, einstellungsWert(name), name in einstellungen.entwurf) : null;
}

/** Wert in den Entwurf; Wahlen kommen als Text und bekommen den Typ des Felds */
export function setzen(name: string, wert: unknown): void {
  const feld = einstellungsFeld(name);
  if (typeof wert === "number" && feld) wert = Math.round(wert * anzeigeeinheit(feld).faktor * 1000) / 1000;
  einstellungSetzen(name, typeof wert === "string" ? wahlwert(feld, wert) : wert);
}

/** Vorgabe in den Entwurf (Knopf "Vorgabe", fragt vorher) */
export function aufVorgabe(name: string): void {
  einstellungSetzen(name, einstellungsFeld(name)?.vorgabe);
}

export async function angebot(name: string): Promise<{ optionen: Wahlwert[]; stand: string }> {
  const a = await einstellungsAngebot(name);
  return { optionen: a.optionen.map((o) => ({ wert: o.wert, titel: o.titel, hinweis: o.hinweis })), stand: a.stand ?? "" };
}

// ----- Teil-Entwürfe ----------------------------------------------------------------------------------------------

export function teilMelden(id: string, teil: Teilentwurf): void {
  teile[id] = teil;
}

export function teilZurueck(id: string): void {
  delete teile[id];
}

// ----- Leiste Speichern -------------------------------------------------------------------------------------------

/** Was in der Leiste wartet: Titel der geänderten Felder und Teile */
export function wartend(): string[] {
  const felder = Object.keys(einstellungen.entwurf).map((n) => einstellungsFeld(n)?.titel ?? n);
  return [...felder, ...Object.values(teile).map((t) => t.titel)];
}

/** Speichert erst die Server-Felder (alles oder nichts), dann die Teile; liefert die Zahl; wirft mit dem Grund */
export async function speichern(): Promise<number> {
  let n = 0;
  if (Object.keys(einstellungen.entwurf).length) {
    n += await einstellungenSpeichern();
    wirkungen(Object.fromEntries(einstellungen.felder.map((f) => [f.name, f.wert])));
  }
  for (const [id, teil] of Object.entries(teile)) {
    await teil.speichern();
    delete teile[id];
    n += 1;
  }
  return n;
}

export function verwerfen(): void {
  einstellungenVerwerfen();
  for (const [id, teil] of Object.entries(teile)) {
    teil.verwerfen();
    delete teile[id];
  }
}
