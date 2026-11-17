// Anfragen der Senderquelle ans eigene Backend: JSON hin und zurück, mit dem Kopf der Sitzung (lib/sitzung.ts), Fehler
// als `Netzfehler` mit Status und dem Text des Servers. Der Abruf selbst ist austauschbar (Tests stellen ihn nach).
import { antwortPruefen, kopf } from "../sitzung";

export type Abruf = (weg: string, init: RequestInit) => Promise<Response>;

export class Netzfehler extends Error {
  constructor(public status: number, text: string) {
    super(text);
    this.name = "Netzfehler";
  }
}

export interface Optionen {
  methode?: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  daten?: unknown;
  signal?: AbortSignal;
}

/** Ein Netz für Anfragen; `abruf` ist ohne Angabe das fetch des Browsers. */
export function netz(abruf: Abruf = (weg, init) => fetch(weg, init)) {
  return async function anfrage<T>(weg: string, { methode = "GET", daten, signal }: Optionen = {}): Promise<T> {
    const init: RequestInit = { method: methode, signal, headers: kopf(daten === undefined ? {} : { "Content-Type": "application/json" }) };
    if (daten !== undefined) init.body = JSON.stringify(daten);
    const antwort = await abruf(weg, init);
    antwortPruefen(antwort);
    if (!antwort.ok) {
      let text = `Fehler ${antwort.status}`;
      try {
        const inhalt = await antwort.json();
        if (inhalt?.detail) text = typeof inhalt.detail === "string" ? inhalt.detail : JSON.stringify(inhalt.detail);
      } catch {
        /* ohne Inhalt bleibt der Status */
      }
      throw new Netzfehler(antwort.status, text);
    }
    if (antwort.status === 204) return undefined as T;
    return (await antwort.json()) as T;
  };
}

export type Anfrage = ReturnType<typeof netz>;
