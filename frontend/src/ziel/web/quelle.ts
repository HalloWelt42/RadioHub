// Bauziel Webversion (RAD-4): die statische Senderliste (web/daten/sender.json, beim Bau unter daten/ der Seite),
// eigene Angaben im Speicher des Browsers.
import { browserSpeicher, StatischeQuelle } from "../../lib/radio/statisch";
import type { Senderquelle } from "../../lib/radio/quelle";

async function laden(): Promise<unknown> {
  const antwort = await fetch(`${import.meta.env.BASE_URL}daten/sender.json`);
  if (!antwort.ok) throw new Error(`Senderliste nicht geladen (${antwort.status})`);
  return antwort.json();
}

// erst beim Lesen und Schreiben auf localStorage zugreifen: in privaten Fenstern kann schon der Zugriff scheitern,
// und der Speicher fängt das dort ab
const ablage = { getItem: (k: string) => localStorage.getItem(k), setItem: (k: string, w: string) => localStorage.setItem(k, w) };

export const senderquelle: Senderquelle = new StatischeQuelle({ laden, speicher: browserSpeicher(ablage) });
