// Zustand der Podcast-Ansicht (RAD-17) als eine Wahrheit, abgeglichen mit der Adresse wie die Schnellfilter des Radios:
//   /podcasts                     alle Abos
//   /podcasts/<abo>               ein Abo (mit Kopf); mehrere: /podcasts?abo=3,4
//   /podcasts/<abo>/<folge>       eine Folge aufgeklappt (auch vom Telefon)
//   ?wahl=ungehoert|gespeichert  ?suche=...  ?sort=alt|titel|laenge  ?verzeichnis=1 (Abonnieren); frühere /podcasts/search/<suche> gilt weiter
//   ?liste=abos                   Übersicht der Abos (Telefon; am Rechner stehen sie immer in der Seitenleiste)
// Beim Start und bei Zurück und Vor gilt die Adresse, danach schreibt jede Änderung sie neu (ohne neuen Eintrag; nur
// Aufklappen einer Folge legt einen an).
import type { Ort } from "../radio/filterzustand.svelte";
import { PODCASTSORTIERUNG, type Folgenabfrage, type Podcastsortierung } from "./typen";

export type Folgenwahl = "alle" | "ungehoert" | "gespeichert";
export const FOLGENWAHL: readonly Folgenwahl[] = ["alle", "ungehoert", "gespeichert"];
/** die Wahlen, die eine Quelle anbieten kann: "gespeichert" nur mit Ablage (Webversion ohne, RAD-102) */
export const angeboteneWahl = (speichern: boolean): Folgenwahl[] => FOLGENWAHL.filter((w) => w !== "gespeichert" || speichern);

export interface Podcastansicht {
  abos: number[];
  wahl: Folgenwahl;
  suche: string;
  sortierung: Podcastsortierung;
  /** aufgeklappte Folge */
  offen: number | null;
  /** Abonnieren: Suche im Verzeichnis statt der Liste */
  verzeichnis: boolean;
  /** Übersicht der Abos statt der Folgen (Telefon, RAD-14) */
  aboUebersicht: boolean;
}

export const leer = (): Podcastansicht => ({ abos: [], wahl: "alle", suche: "", sortierung: "neu", offen: null, verzeichnis: false, aboUebersicht: false });

const zahl = (t: string | undefined) => (t && /^\d+$/.test(t) ? Number(t) : null);

export function ausAdresse(pfad: string, abfrage: string): Podcastansicht {
  const a = leer();
  const teile = pfad.replace(/^\/podcasts\/?/, "").split("/").filter(Boolean);
  const q = new URLSearchParams(abfrage);
  const ein = zahl(teile[0]);
  const mehrere = (q.get("abo") ?? "").split(",").map((x) => zahl(x)).filter((x): x is number => x !== null);
  a.abos = ein !== null ? [ein] : [...new Set(mehrere)];
  a.offen = ein !== null ? zahl(teile[1]) : null;
  const wahl = q.get("wahl") as Folgenwahl | null;
  if (wahl && FOLGENWAHL.includes(wahl)) a.wahl = wahl;
  const sort = q.get("sort") as Podcastsortierung | null;
  if (sort && PODCASTSORTIERUNG.includes(sort)) a.sortierung = sort;
  a.suche = (q.get("suche") ?? (teile[0] === "search" && teile[1] ? decodeURIComponent(teile[1]) : "")).trim();   // frühere Form /podcasts/search/<suche>
  a.verzeichnis = q.get("verzeichnis") === "1";
  a.aboUebersicht = q.get("liste") === "abos";
  return a;
}

export function zuAdresse(a: Podcastansicht, offenAbo: number | null = null): string {
  const q = new URLSearchParams();
  let pfad = "/podcasts";
  const ein = a.abos.length === 1 ? a.abos[0] : null;
  if (a.offen !== null && (ein ?? offenAbo) !== null) pfad += `/${ein ?? offenAbo}/${a.offen}`;
  else if (ein !== null) pfad += `/${ein}`;
  if (a.abos.length > 1 || (a.offen !== null && ein === null && a.abos.length)) q.set("abo", a.abos.join(","));
  if (a.wahl !== "alle") q.set("wahl", a.wahl);
  if (a.suche) q.set("suche", a.suche);
  if (a.sortierung !== "neu") q.set("sort", a.sortierung);
  if (a.verzeichnis) q.set("verzeichnis", "1");
  if (a.aboUebersicht) q.set("liste", "abos");
  const text = q.toString();
  return text ? `${pfad}?${text}` : pfad;
}

/** die Abfrage der Folgenliste zu einer Ansicht */
export function zuAbfrage(a: Podcastansicht): Folgenabfrage {
  const sort = { neu: ["datum", true], alt: ["datum", false], titel: ["titel", false], laenge: ["dauer", false] } as const;
  const [sortierung, absteigend] = sort[a.sortierung];
  return { abos: a.abos, filter: a.wahl, sortierung, absteigend };
}

export class Podcastzustand {
  ansicht = $state<Podcastansicht>(leer());
  private gelesen = false;

  constructor(private readonly ort: Ort) {}

  ausAdresse(): void {
    this.gelesen = true;
    this.ansicht = ausAdresse(this.ort.pfad(), this.ort.abfrage());
  }

  /** beim Öffnen der Ansicht: beim ersten Mal gilt die Adresse, danach der Zustand */
  oeffnen(): void {
    if (this.gelesen) this.schreiben();
    else this.ausAdresse();
  }

  aendern(arbeit: (a: Podcastansicht) => Podcastansicht): void {
    this.ansicht = arbeit(this.ansicht);
    this.schreiben();
  }

  /** Orte mit eigenem Eintrag im Verlauf (Telefon: Abo öffnen, Abonnieren): Zurück geht zurück */
  gehen(arbeit: (a: Podcastansicht) => Podcastansicht): void {
    this.ansicht = arbeit(this.ansicht);
    const pfad = zuAdresse(this.ansicht);
    const jetzt = this.ort.pfad() + (this.ort.abfrage() ? `?${this.ort.abfrage().replace(/^\?/, "")}` : "");
    if (pfad !== jetzt) this.ort.neu(pfad);
  }

  /** Folge auf- oder zuklappen: ein neuer Eintrag im Verlauf (Zurück schließt wieder) */
  folge(id: number | null, aboId: number | null): void {
    if (this.ansicht.offen === id) return;
    this.ansicht = { ...this.ansicht, offen: id };
    this.ort.neu(zuAdresse(this.ansicht, aboId));
  }

  private schreiben(): void {
    const pfad = zuAdresse(this.ansicht);
    const jetzt = this.ort.pfad() + (this.ort.abfrage() ? `?${this.ort.abfrage().replace(/^\?/, "")}` : "");
    if (pfad !== jetzt) this.ort.ersetzen(pfad);
  }
}
