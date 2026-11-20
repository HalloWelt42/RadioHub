// Wecker, Ort und Zeitansage von Basic (RAD-15): Wecker und Ort im Speicher des Browsers, die Sender aus den
// Favoriten der Senderquelle, die Bausteine der Zeitansage fertig aus dem Repo (web/daten/zeitansage, Katalogstimme).
// Prüft beim Speichern dasselbe wie das Backend (routers/wecker.py).
import type { Senderquelle } from "../radio/quelle";
import type { Speicher } from "../radio/statisch/speicher";
import type { Bausteinstand, Fundort, Ort, Wecker, WeckerEntwurf, Weckerablage, WeckSender, Zeitbausteine } from "./weckerablage";

export const SCHLUESSEL_WECKER = "radiohub_wecker";
export const SCHLUESSEL_ORT = "radiohub_wecker_ort";
const ZEIT = /^([01]\d|2[0-3]):[0-5]\d$/;
const SEITE = 200;   // so viele liefert die Senderquelle je Seite höchstens

function lesen<T>(speicher: Speicher, schluessel: string, vorgabe: T): T {
  try {
    const roh = speicher.lesen(schluessel);
    return roh ? (JSON.parse(roh) as T) : vorgabe;
  } catch {
    return vorgabe;
  }
}

/** wie WeckerDaten im Backend: Uhrzeit, Wochentage 1 bis 7 (sortiert, ohne Doppel), Grenzen der Regler */
export function geprueft(w: WeckerEntwurf, id: Wecker["id"]): Wecker {
  if (!ZEIT.test(w.zeit)) throw new Error("Zeit als HH:MM");
  if (w.tage.some((t) => t < 1 || t > 7)) throw new Error("Wochentage 1 bis 7");
  if (w.quelle !== "sender") throw new Error("Podcast fehlt");
  if (!w.sender?.uuid) throw new Error("Sender fehlt");
  const zahl = (wert: number, von: number, bis: number) => Math.min(bis, Math.max(von, Math.round(Number(wert))));
  return {
    id, aktiv: !!w.aktiv, zeit: w.zeit, tage: [...new Set(w.tage)].sort((a, b) => a - b), quelle: "sender",
    sender: w.sender, podcast_id: null, lautstaerke: zahl(w.lautstaerke, 5, 100), anstieg_s: zahl(w.anstieg_s, 0, 600),
    schlummern_min: zahl(w.schlummern_min, 1, 60), weckton: w.weckton,
  };
}

export class BrowserWeckerablage implements Weckerablage {
  readonly faehig = { ortssuche: false, podcast: false };

  constructor(private readonly speicher: Speicher, private readonly senderquelle: Senderquelle,
              private readonly neueKennung: () => string = () => crypto.randomUUID()) {}

  private alle(): Wecker[] {
    return lesen<Wecker[]>(this.speicher, SCHLUESSEL_WECKER, []);
  }

  private ablegen(liste: Wecker[]): void {
    this.speicher.schreiben(SCHLUESSEL_WECKER, JSON.stringify(liste));
  }

  async liste(): Promise<Wecker[]> {
    return this.alle().sort((a, b) => a.zeit.localeCompare(b.zeit));
  }

  async speichern(w: WeckerEntwurf): Promise<Wecker> {
    const alle = this.alle();
    if (w.id != null && !alle.some((x) => x.id === w.id)) throw new Error("Wecker nicht gefunden");
    const neu = geprueft(w, w.id ?? this.neueKennung());
    this.ablegen([...alle.filter((x) => x.id !== neu.id), neu]);
    return neu;
  }

  async loeschen(id: Wecker["id"]): Promise<void> {
    const alle = this.alle();
    if (!alle.some((x) => x.id === id)) throw new Error("Wecker nicht gefunden");
    this.ablegen(alle.filter((x) => x.id !== id));
  }

  async ort(): Promise<Ort> {
    return lesen<Ort>(this.speicher, SCHLUESSEL_ORT, { name: "", breite: null, laenge: null });
  }

  async ortSetzen(o: Ort): Promise<Ort> {
    const gueltig = (w: number | null, grenze: number) => (w == null || Number.isNaN(w) || Math.abs(w) > grenze ? null : w);
    const ort = { name: o.name.trim(), breite: gueltig(o.breite, 90), laenge: gueltig(o.laenge, 180) };
    this.speicher.schreiben(SCHLUESSEL_ORT, JSON.stringify(ort));
    return ort;
  }

  async orteSuchen(): Promise<Fundort[]> {
    return [];
  }

  async sender(): Promise<WeckSender[]> {
    const eintraege = [];
    let nach: string | null = null;
    do {
      const r = await this.senderquelle.abfragen({ nur_favoriten: true, anzahl: SEITE, mit_facetten: false, sortierung: "name", nach });
      eintraege.push(...r.eintraege);
      nach = r.weiter;
    } while (nach);
    return Promise.all(eintraege.map(async (e) => {
      const w = await this.senderquelle.wiedergabe(e);
      return { uuid: w.uuid, name: w.name, url: w.url, url_resolved: w.url_resolved, favicon: w.favicon };
    }));
  }
}

/** alle Bausteine wie im Backend (services/zeitansage.bausteine): "Es ist", die Stunden 00 bis 23, die Minuten 01 bis 59 */
export function alleBausteine(): string[] {
  const zwei = (n: number) => String(n).padStart(2, "0");
  return ["es-ist", ...Array.from({ length: 24 }, (_, h) => `stunde-${zwei(h)}`),
          ...Array.from({ length: 59 }, (_, m) => `minute-${zwei(m + 1)}`)];
}

/** fertige Bausteine einer Katalogstimme unter `basis` (Ordner zeitansage der Seite) */
export class StatischeZeitbausteine implements Zeitbausteine {
  readonly faehig = { erzeugen: false };

  constructor(private readonly basis: string, private readonly stimme: string) {}

  async stand(): Promise<Bausteinstand> {
    return { stimme: this.stimme, bausteine: alleBausteine(), fehlend: [] };
  }

  adresse(_stimme: string, name: string): string {
    return `${this.basis}${name}.mp3`;
  }

  async erzeugen(): Promise<void> {
    throw new Error("Basic spricht keine Bausteine");
  }
}
