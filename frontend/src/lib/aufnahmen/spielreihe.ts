// Aufnahmen als Spielreihe der Engine (RAD-17, RAD-134): ein Eintrag je Titel oder die ganze Aufnahme, für Rechner, Telefon und die
// Übergabe an ein anderes Gerät. Alles liegt zentral; ein Eintrag trägt, was zum Hören, Anzeigen und Laden gebraucht wird.
import { schnittquelle } from "../schnitt";
import type { Aufnahmequelle } from "./quelle";
import type { Aufnahme, Titel } from "./typen";

export interface Spieleintrag {
  path: string;
  name: string;
  session_id?: string;
  station_name: string;
  station_uuid?: string;
  date?: string;
  duration: number;
  playUrl: string;
  /** Adresse zum Herunterladen, leer ohne */
  ladeUrl?: string;
  source: "recording";
}

export const ganzeAufnahme = (q: Aufnahmequelle, a: Aufnahme): Spieleintrag => ({ path: `sitzung:${a.id}`, name: a.sender, session_id: a.id,
  station_name: a.sender, station_uuid: a.senderUuid, date: a.beginn, duration: a.dauer, playUrl: schnittquelle.ton({ art: "sitzung", kennung: a.id }),
  ladeUrl: q.alsEineDatei(a.id), source: "recording" });

export const titelEintrag = (q: Aufnahmequelle, a: Aufnahme, x: Titel): Spieleintrag => ({ path: x.pfad, name: x.titel || a.sender, session_id: a.id,
  station_name: a.sender, station_uuid: a.senderUuid, duration: x.dauer, playUrl: q.titelTon(x.id), ladeUrl: q.titelDatei(x.id), source: "recording" });

/** Die Titel einer Aufnahme der Reihe nach, ohne Titel die ganze */
export const reiheAus = (q: Aufnahmequelle, a: Aufnahme, titel: Titel[]): Spieleintrag[] =>
  titel.length ? titel.map((x) => titelEintrag(q, a, x)) : [ganzeAufnahme(q, a)];

export async function reiheVon(q: Aufnahmequelle, kennung: string): Promise<Spieleintrag[]> {
  const [a, titel] = await Promise.all([q.aufnahme(kennung), q.titel(kennung)]);
  return reiheAus(q, a, titel);
}
