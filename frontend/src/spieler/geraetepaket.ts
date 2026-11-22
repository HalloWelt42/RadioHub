// Zustand und Paket der Übergabe im Radio (RAD-18), ohne Oberfläche und Verbindung: was dieses Fenster meldet und was
// bei Holen und Dorthin mitreist. Die Modelle im Backend dazu stehen in backend/app/geraete.py.
import type { AppZustand } from "./app";

export type Quellart = "sender" | "folge" | "aufnahme";

export interface RadioZustand {
  art: Quellart;
  titel: string;
  untertitel: string;
  laeuft: boolean;
}

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

/** was hier gerade spielt, für die anderen Geräte; null: nichts */
export function zustandJetzt(s: AppZustand): RadioZustand | null {
  const laeuft = !!s.isPlaying && !s.isPaused;
  if (s.currentEpisode) return { art: "folge", titel: kurz(s.currentEpisode.title), untertitel: kurz(s.currentEpisode.podcast?.title), laeuft };
  if (s.currentRecording) return { art: "aufnahme", titel: kurz(s.currentRecording.name), untertitel: kurz(s.currentRecording.station_name), laeuft };
  if (s.currentStation && (s.isPlaying || s.isPaused)) return { art: "sender", titel: kurz(s.currentStation.name), untertitel: kurz(s.streamTitle), laeuft };
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

