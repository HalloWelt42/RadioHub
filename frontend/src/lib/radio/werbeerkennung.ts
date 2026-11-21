// Werbeerkennung des Backends (Einstellungen > Radio > Werbeerkennung): Stand, Verdächtige, Entscheidungen, Einstellungen
// und der Scan als Strom von Ereignissen. Nur in der vollen App (die Webversion hat keinen Dienst, der Ströme öffnet);
// der Scan liest den Strom über fetch mit dem Kopf der Sitzung, immer am eigenen Ursprung (früher localhost:9091).
import { netz, type Anfrage } from "./netz";
import { kopf, antwortPruefen } from "../sitzung";

export interface WerbeStand {
  total_checked: number;
  clean: number;
  suspect: number;
  confirmed_ad: number;
  auto_blocked: number;
  manual_blocked: number;
  remaining: number;
}

export interface Verdaechtiger {
  uuid: string;
  name: string;
  status: string;
  confidence: number;
}

export type Pruefart = "url_check" | "header_check";

export interface WerbeEinstellungen {
  an: boolean;
  arten: Pruefart[];
  /** ab diesem Anteil gilt ein Sender als verdächtig (0,4 bis 1) */
  schwelle: number;
}

/** Fortschritt des Scans */
export interface ScanStand {
  geprueft: number;
  gesamt: number;
  aktuell: string;
}

export interface ScanErgebnis {
  geprueft: number;
  neuVerdaechtig: number;
  uebrig: number;
}

const VORGABE: WerbeEinstellungen = { an: true, arten: ["url_check", "header_check"], schwelle: 0.8 };

function liste(wert: unknown): unknown {
  if (typeof wert !== "string") return wert;
  try { return JSON.parse(wert); } catch { return wert; }
}

export class Werbeerkennung {
  constructor(private readonly a: Anfrage = netz(), private readonly abruf: typeof fetch = (w, i) => fetch(w, i)) {}

  stand(): Promise<WerbeStand> {
    return this.a("/api/ad-detection/summary/overview");
  }

  async verdaechtige(schwelle: number): Promise<Verdaechtiger[]> {
    const r = await this.a<Verdaechtiger[]>(`/api/ad-detection/suspects?min_confidence=${schwelle}`);
    return r.map((v) => ({ uuid: v.uuid, name: (v.name ?? "").trim() || v.uuid, status: v.status, confidence: v.confidence }));
  }

  /** sperren blendet aus (eigene Entscheidung), erlauben nimmt den Verdacht zurück */
  async entscheiden(uuid: string, aktion: "block" | "allow"): Promise<void> {
    await this.a("/api/ad-detection/decide", { methode: "POST", daten: { uuid, action: aktion } });
  }

  async einstellungen(): Promise<WerbeEinstellungen> {
    const c = await this.a<Record<string, unknown>>("/api/config");
    const an = c.ad_detection_enabled;
    const arten = liste(c.ad_detection_methods);
    const schwelle = Number(c.ad_detection_threshold) / 100;           // auf dem Server in Prozent (RAD-11)
    return {
      an: an === undefined || an === null ? VORGABE.an : an === true || an === "true",
      arten: Array.isArray(arten) ? arten.filter((x): x is Pruefart => x === "url_check" || x === "header_check") : VORGABE.arten,
      schwelle: Number.isFinite(schwelle) && schwelle > 0 ? schwelle : VORGABE.schwelle,
    };
  }

  async speichern(e: WerbeEinstellungen): Promise<void> {
    await this.a("/api/config", { methode: "PUT", daten: { updates: {
      ad_detection_enabled: e.an, ad_detection_methods: e.arten, ad_detection_threshold: Math.round(e.schwelle * 100),
    } } });
  }

  /** Eine Runde des Scans (bis zu `menge` ungeprüfte sichtbare Sender); meldet den Fortschritt je Sender */
  async runde(menge: number, fortschritt: (s: ScanStand) => void, signal?: AbortSignal): Promise<ScanErgebnis> {
    const antwort = await this.abruf(`/api/ad-detection/scan-stream?batch_size=${menge}`, { headers: kopf(), signal });
    antwortPruefen(antwort);
    if (!antwort.ok || !antwort.body) throw new Error(`Fehler ${antwort.status}`);
    const leser = antwort.body.pipeThrough(new TextDecoderStream()).getReader();
    let rest = "";
    let ende: ScanErgebnis = { geprueft: 0, neuVerdaechtig: 0, uebrig: 0 };
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
        if (d.done) ende = { geprueft: d.checked, neuVerdaechtig: d.new_suspects, uebrig: d.remaining };
        else fortschritt({ geprueft: d.progress, gesamt: d.total, aktuell: d.current });
      }
    }
    return ende;
  }
}
