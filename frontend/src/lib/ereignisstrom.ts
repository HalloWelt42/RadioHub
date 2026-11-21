// Ereignisstrom des Backends lesen (routers/ereignisstrom.py): start, progress (Schritt, Gesamt, Text), done mit dem
// Ergebnis unter einem Namen, error mit der Meldung. Für Schnitt (RAD-17) und Werbestellen (RAD-32).
import { antwortPruefen } from "./sitzung";

export interface Fortschritt {
  schritt: number;
  gesamt: number;
  text: string;
}

export async function fehlerText(antwort: Response): Promise<string> {
  try {
    const d = await antwort.json();
    return typeof d.detail === "string" ? d.detail : `Fehler ${antwort.status}`;
  } catch {
    return `Fehler ${antwort.status}`;
  }
}

/** progress meldet, done liefert den Wert unter `feld`, error wirft mit der Meldung des Servers */
export async function ereignisse<T>(antwort: Response, melden: (f: Fortschritt) => void, feld = "count"): Promise<T> {
  antwortPruefen(antwort);
  if (!antwort.ok || !antwort.body) throw new Error(await fehlerText(antwort));
  const leser = antwort.body.pipeThrough(new TextDecoderStream()).getReader();
  let rest = "";
  for (;;) {
    const { value, done } = await leser.read();
    if (done) break;
    rest += value;
    const bloecke = rest.split("\n\n");
    rest = bloecke.pop() ?? "";
    for (const block of bloecke) {
      const zeile = block.split("\n").find((z) => z.startsWith("data:"));
      if (!zeile) continue;
      const d = JSON.parse(zeile.slice(5));
      if (d.type === "progress") melden({ schritt: d.step, gesamt: d.total, text: d.message });
      if (d.type === "error") throw new Error(d.message);
      if (d.type === "done") return d[feld] as T;
    }
  }
  throw new Error("Verbindung abgebrochen, bevor die Arbeit fertig war");
}
