// Sender, die Werbung in ihren Sendedaten ankündigen (RAD-33): einmal geladen und für Liste, Steckbrief und
// Einstellungen geteilt; ein Fund reicht, damit ein Sender als werbend gilt. Nur mit Dienst (faehig.werbung).
import { currentLanguage } from "../i18n.js";
import { sendewerbung, type SenderWerbung, type Steckbrief } from "./sendewerbung";

/** so oft wird nachgeladen, solange jemand liest (neue Spots kommen beim Hören dazu) */
const FRISCH_MS = 60_000;

class Werbende {
  sender = $state<Map<string, SenderWerbung>>(new Map());
  private geladen = 0;

  /** lädt, wenn der letzte Stand älter als eine Minute ist (oder `immer`) */
  async laden(immer = false): Promise<void> {
    if (!immer && Date.now() - this.geladen < FRISCH_MS) return;
    this.geladen = Date.now();
    try {
      this.sender = new Map((await sendewerbung.werbende()).map((s) => [s.uuid, s]));
    } catch {
      this.geladen = 0;            // beim nächsten Mal wieder versuchen
    }
  }

  von(uuid: string): SenderWerbung | undefined {
    return this.sender.get(uuid);
  }

  /** nach einer Änderung am Steckbrief eines Senders */
  merken(s: Steckbrief): void {
    const neu = new Map(this.sender);
    if (s.spots) neu.set(s.uuid, { uuid: s.uuid, name: s.name, spots: s.spots, zuletzt: s.zuletzt, ueberspringen: s.ueberspringen, ausgenommen: s.ausgenommen, marke: s.marke });
    else neu.delete(s.uuid);
    this.sender = neu;
  }
}

export const werbende = new Werbende();

/** Zeitpunkt des Servers (SQLite, UTC ohne Zone) als kurzes Datum mit Uhrzeit in der Sprache der Oberfläche */
export function wann(zeit: string | null): string {
  if (!zeit) return "";
  const d = new Date(zeit.includes("T") || zeit.endsWith("Z") ? zeit : `${zeit.replace(" ", "T")}Z`);
  if (Number.isNaN(d.getTime())) return zeit;
  return d.toLocaleString(currentLanguage() || "de", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });
}
