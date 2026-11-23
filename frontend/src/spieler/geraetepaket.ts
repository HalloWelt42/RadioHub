// Zustand und Paket der Übergabe im Radio (RAD-18), ohne Oberfläche und Verbindung: was dieses Fenster meldet und was
// bei Holen und Dorthin mitreist. Die Modelle im Backend dazu stehen in backend/app/geraete.py.
import type { AppZustand } from "./app";

export type Quellart = "sender" | "folge" | "aufnahme";

export interface RadioZustand {
  art: Quellart;
  titel: string;
  untertitel: string;
  laeuft: boolean;
  /** uuid des Senders, sonst leer (Auge und Stern am steuernden Gerät, RAD-96) */
  kennung: string;
  /** Bild der Quelle, so wie es das steuernde Gerät lädt; leer ohne */
  bild: string;
  lautstaerke: number | null;
}

/** Was ein Gerät an einem anderen auslöst (RAD-96); unbekannte Aktionen übergeht das andere */
export type Fernaktion = "umschalten" | "stopp" | "weiter" | "vorher" | "vor" | "zurueck" | "lautstaerke";

type Verweis = Record<string, unknown>;

export interface RadioPaket {
  art: Quellart;
  sender?: Verweis;
  folge?: Verweis;
  podcast?: Verweis;
  aufnahme?: Verweis;
  stelle: number;
}

/** längere Texte (Beschreibungen, Notizen) reisen nicht mit; das Paket bleibt klein */
const LANG = 500;

export function kompakt(wert: unknown): Verweis | undefined {
  if (!wert || typeof wert !== "object") return undefined;
  const aus: Verweis = {};
  for (const [k, v] of Object.entries(wert as Verweis)) {
    if (typeof v === "string" && v.length > LANG) continue;
    if (v !== null && typeof v === "object") continue;        // verschachtelte Teile (etwa das Abo an der Folge) einzeln
    aus[k] = v;
  }
  return aus;
}

const kurz = (s: unknown) => String(s ?? "").slice(0, 300);

/** was hier gerade spielt, für die anderen Geräte; null: nichts. `bild`: das Bild der Quelle, wie die Oberfläche es zeigt */
export function zustandJetzt(s: AppZustand, bild: string | null = null): RadioZustand | null {
  const laeuft = !!s.isPlaying && !s.isPaused;
  const rest = { laeuft, kennung: "", bild: String(bild ?? "").slice(0, 2000), lautstaerke: Math.round(s.volume) };
  if (s.currentEpisode) return { art: "folge", titel: kurz(s.currentEpisode.title), untertitel: kurz(s.currentEpisode.podcast?.title), ...rest };
  if (s.currentRecording) return { art: "aufnahme", titel: kurz(s.currentRecording.name), untertitel: kurz(s.currentRecording.station_name), ...rest };
  if (s.currentStation && (s.isPlaying || s.isPaused)) {
    return { art: "sender", titel: kurz(s.currentStation.name), untertitel: kurz(s.streamTitle), ...rest, kennung: String(s.currentStation.uuid ?? "").slice(0, 64) };
  }
  return null;
}

/** die eigene Wiedergabe als Paket; null: nichts abzugeben */
export function paketJetzt(s: AppZustand, stelle = 0): RadioPaket | null {
  if (!s.isPlaying && !s.isPaused) return null;
  if (s.currentEpisode) {
    const { podcast, ...folge } = s.currentEpisode;
    return { art: "folge", folge: kompakt(folge), podcast: kompakt(podcast), stelle };
  }
  if (s.currentRecording) return { art: "aufnahme", aufnahme: kompakt(s.currentRecording), stelle };
  if (s.currentStation) return { art: "sender", sender: kompakt(s.currentStation), stelle: 0 };
  return null;
}

