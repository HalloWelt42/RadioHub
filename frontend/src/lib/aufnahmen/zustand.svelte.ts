// Zustand der Aufnahmen (RAD-17): Liste seitenweise (neue Abfrage bricht die laufende ab, verspätete Antworten
// ändern nichts), Ordner, und die Ansicht als eine Wahrheit, abgeglichen mit der Adresse:
//   /aufnahmen                      alle Aufnahmen        ?ordner=ohne|<id>  ?suche=  ?sort=sender|dauer|groesse  ?auf=1
//   /aufnahmen/<id>                 eine Aufnahme mit ihren Titeln
//   /aufnahmen/<id>/schnitt         Schnitt dieser Aufnahme
//   /aufnahmen/wolke?pfad=...       Ordner der Kellerwolke
//   /aufnahmen/wolke/schnitt?pfad=  Schnitt einer Datei der Kellerwolke
import type { Ort } from "../radio/filterzustand.svelte";
import type { Aufnahmequelle } from "./quelle";
import { AUFNAHMESORTIERUNG, type Aufnahme, type Aufnahmeabfrage, type Aufnahmeordner, type Aufnahmesortierung } from "./typen";

export const SEITE = 50;

export class Aufnahmeliste {
  aufnahmen = $state<Aufnahme[]>([]);
  gesamt = $state<number | null>(null);
  titelGesamt = $state(0);
  laedt = $state(false);
  fehler = $state("");
  geladen = $state(false);
  private abfrage: Aufnahmeabfrage | null = null;
  private lauf = 0;

  constructor(private readonly quelle: Aufnahmequelle, private readonly seite = SEITE) {}

  get mehr(): boolean {
    return this.gesamt !== null && this.aufnahmen.length < this.gesamt;
  }

  async laden(abfrage: Aufnahmeabfrage): Promise<void> {
    this.abfrage = abfrage;
    const lauf = ++this.lauf;
    this.laedt = true;
    try {
      const s = await this.quelle.aufnahmen(abfrage, 0, this.seite);
      if (lauf !== this.lauf) return;
      this.aufnahmen = s.aufnahmen;
      this.gesamt = s.gesamt;
      this.titelGesamt = s.titelGesamt;
      this.fehler = "";
    } catch (f) {
      if (lauf === this.lauf) this.fehler = (f as Error).message;
    } finally {
      if (lauf === this.lauf) { this.laedt = false; this.geladen = true; }
    }
  }

  async nachladen(): Promise<void> {
    if (!this.abfrage || this.laedt || !this.mehr) return;
    const lauf = this.lauf;
    this.laedt = true;
    try {
      const s = await this.quelle.aufnahmen(this.abfrage, this.aufnahmen.length, this.seite);
      if (lauf !== this.lauf) return;
      const da = new Set(this.aufnahmen.map((a) => a.id));
      this.aufnahmen = [...this.aufnahmen, ...s.aufnahmen.filter((a) => !da.has(a.id))];
      this.gesamt = s.gesamt;
    } finally {
      if (lauf === this.lauf) this.laedt = false;
    }
  }

  /** ohne Netz entfernen (nach Löschen), die Gesamtzahl zieht mit */
  entfernen(id: string): void {
    this.aufnahmen = this.aufnahmen.filter((a) => a.id !== id);
    if (this.gesamt !== null) this.gesamt = Math.max(0, this.gesamt - 1);
  }
}

export class Ordnerliste {
  ordner = $state<Aufnahmeordner[]>([]);

  constructor(private readonly quelle: Aufnahmequelle) {}

  get ziel(): Aufnahmeordner | null {
    return this.ordner.find((o) => o.ziel) ?? null;
  }

  name(id: number | null): string | null {
    return id === null ? null : this.ordner.find((o) => o.id === id)?.name ?? null;
  }

  async laden(): Promise<void> {
    this.ordner = await this.quelle.ordner();
  }

  async zielSetzen(id: number | null): Promise<void> {
    await this.quelle.zielSetzen(id);
    this.ordner = this.ordner.map((o) => ({ ...o, ziel: o.id === id }));
  }

  async anlegen(name: string): Promise<void> {
    await this.quelle.ordnerAnlegen(name);
    await this.laden();
  }

  async umbenennen(id: number, name: string): Promise<void> {
    await this.quelle.ordnerUmbenennen(id, name);
    this.ordner = this.ordner.map((o) => (o.id === id ? { ...o, name } : o));
  }

  async loeschen(id: number): Promise<void> {
    await this.quelle.ordnerLoeschen(id);
    this.ordner = this.ordner.filter((o) => o.id !== id);
  }
}

// ----- Ansicht und Adresse ----------------------------------------------------------------------------------------

export type Aufnahmequellwahl = "aufnahmen" | "wolke";

export interface Aufnahmeansicht {
  quelle: Aufnahmequellwahl;
  /** gewählte Aufnahme (Kopf und Titel) */
  aufnahme: string | null;
  /** Schnitt offen: der Aufnahme (quelle aufnahmen) oder der Datei unter `pfad` (quelle wolke) */
  schnitt: boolean;
  /** Ordner der Kellerwolke, im Schnitt die Datei */
  pfad: string;
  ordner: string;
  suche: string;
  sort: Aufnahmesortierung;
  absteigend: boolean;
}

export const leer = (): Aufnahmeansicht => ({ quelle: "aufnahmen", aufnahme: null, schnitt: false, pfad: "", ordner: "", suche: "", sort: "datum", absteigend: true });

/** natürliche Richtung je Spalte: Datum, Länge, Größe absteigend, Sender von A bis Z */
export const abwaerts = (s: Aufnahmesortierung) => s !== "sender";

export function ausAdresse(pfad: string, abfrage: string): Aufnahmeansicht {
  const a = leer();
  const teile = pfad.replace(/^\/aufnahmen\/?/, "").split("/").filter(Boolean).map(decodeURIComponent);
  const q = new URLSearchParams(abfrage);
  if (teile[0] === "wolke") {
    a.quelle = "wolke";
    a.schnitt = teile[1] === "schnitt";
    a.pfad = (q.get("pfad") ?? "").trim();
  } else if (teile[0] && !["files", "cutter", "search"].includes(teile[0])) {   // frühere Adressen fallen auf die Liste
    a.aufnahme = teile[0];
    a.schnitt = teile[1] === "schnitt";
  }
  const ordner = q.get("ordner") ?? "";
  if (ordner === "ohne" || /^\d+$/.test(ordner)) a.ordner = ordner;
  const sort = q.get("sort") as Aufnahmesortierung | null;
  if (sort && AUFNAHMESORTIERUNG.includes(sort)) a.sort = sort;
  a.absteigend = q.has("auf") ? false : q.has("ab") ? true : abwaerts(a.sort);
  a.suche = (q.get("suche") ?? (teile[0] === "search" && teile[1] ? teile[1] : "")).trim();
  return a;
}

export function zuAdresse(a: Aufnahmeansicht): string {
  const q = new URLSearchParams();
  let pfad = "/aufnahmen";
  if (a.quelle === "wolke") {
    pfad += a.schnitt ? "/wolke/schnitt" : "/wolke";
    if (a.pfad) q.set("pfad", a.pfad);
  } else if (a.aufnahme) {
    pfad += `/${encodeURIComponent(a.aufnahme)}${a.schnitt ? "/schnitt" : ""}`;
  }
  if (a.quelle === "aufnahmen") {
    if (a.ordner) q.set("ordner", a.ordner);
    if (a.suche) q.set("suche", a.suche);
    if (a.sort !== "datum") q.set("sort", a.sort);
    if (a.absteigend !== abwaerts(a.sort)) q.set(a.absteigend ? "ab" : "auf", "1");
  }
  const text = q.toString();
  return text ? `${pfad}?${text}` : pfad;
}

export class Aufnahmezustand {
  ansicht = $state<Aufnahmeansicht>(leer());
  private gelesen = false;

  constructor(private readonly ort: Ort) {}

  ausAdresse(): void {
    this.gelesen = true;
    this.ansicht = ausAdresse(this.ort.pfad(), this.ort.abfrage());
  }

  oeffnen(): void {
    if (this.gelesen) this.schreiben();
    else this.ausAdresse();
  }

  /** Änderungen ohne neuen Eintrag im Verlauf (Filter, Suche, Sortierung) */
  aendern(arbeit: (a: Aufnahmeansicht) => Aufnahmeansicht): void {
    this.ansicht = arbeit(this.ansicht);
    this.schreiben();
  }

  /** Orte mit eigenem Eintrag im Verlauf (Aufnahme wählen, Schnitt öffnen, Ordner wechseln): Zurück geht zurück */
  gehen(arbeit: (a: Aufnahmeansicht) => Aufnahmeansicht): void {
    this.ansicht = arbeit(this.ansicht);
    const pfad = zuAdresse(this.ansicht);
    if (pfad !== this.jetzt()) this.ort.neu(pfad);
  }

  abfrage(): Aufnahmeabfrage {
    const a = this.ansicht;
    return { suche: a.suche, ordner: a.ordner, sort: a.sort, absteigend: a.absteigend };
  }

  private jetzt(): string {
    return this.ort.pfad() + (this.ort.abfrage() ? `?${this.ort.abfrage().replace(/^\?/, "")}` : "");
  }

  private schreiben(): void {
    const pfad = zuAdresse(this.ansicht);
    if (pfad !== this.jetzt()) this.ort.ersetzen(pfad);
  }
}
