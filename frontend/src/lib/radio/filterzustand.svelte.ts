// Zustand der Schnellfilter als eine Wahrheit für Rechner und Telefon, abgeglichen mit der Adresse (Vorgabe 1): beim
// Start und bei Zurück und Vor gilt die Adresse, danach schreibt jede Änderung sie neu (ohne neuen Eintrag im Verlauf;
// nur das Aufklappen eines Senders legt einen an, wie bisher /radio/<uuid>). Der Ort (Adresse lesen und schreiben) ist
// austauschbar, damit der Abgleich ohne Browser prüfbar bleibt.
import { ausOrt, gleich, leer, radioPfad, type Schnellfilter } from "./schnellfilter";

export interface Ort {
  pfad(): string;
  abfrage(): string;
  /** Adresse ersetzen (kein neuer Eintrag im Verlauf) */
  ersetzen(pfad: string): void;
  /** neuer Eintrag im Verlauf */
  neu(pfad: string): void;
}

export class Filterzustand {
  filter = $state<Schnellfilter>(leer());
  /** aufgeklappter Sender (/radio/<uuid>) */
  offen = $state<string | null>(null);
  /** die Adresse wurde schon einmal gelesen (danach gilt der Zustand, bis Zurück oder Vor sie ändert) */
  gelesen = false;

  constructor(private readonly ort: Ort) {}

  /** Adresse lesen (Start, Zurück und Vor); eine frühere Form /radio/search/<suche> wird umgeschrieben */
  ausAdresse(): void {
    this.gelesen = true;
    const { filter, offen } = ausOrt(this.ort.pfad(), this.ort.abfrage());
    this.filter = filter;
    this.offen = offen;
    if (this.ort.pfad().startsWith("/radio/search/")) this.schreiben();
  }

  /** Filter setzen; die Adresse folgt */
  setzen(neu: Schnellfilter): void {
    if (gleich(neu, this.filter)) return;
    this.filter = neu;
    this.schreiben();
  }

  aendern(arbeit: (f: Schnellfilter) => Schnellfilter): void {
    this.setzen(arbeit(this.filter));
  }

  /** Sender auf- oder zuklappen: neuer Eintrag im Verlauf (Zurück schließt wieder) */
  oeffnen(uuid: string | null): void {
    if (uuid === this.offen) return;
    this.offen = uuid;
    this.ort.neu(radioPfad(this.filter, uuid));
  }

  /** Beim Öffnen der Ansicht: beim ersten Mal gilt die Adresse, danach der Zustand (Rückkehr über die Navigation) */
  ansicht(): void {
    if (this.gelesen) this.schreiben();
    else this.ausAdresse();
  }

  /** Adresse aus dem Zustand schreiben (etwa nach dem Wechsel zurück in den Bereich Radio) */
  schreiben(): void {
    const pfad = radioPfad(this.filter, this.offen);
    const jetzt = this.ort.pfad() + (this.ort.abfrage() ? `?${this.ort.abfrage().replace(/^\?/, "")}` : "");
    if (pfad !== jetzt) this.ort.ersetzen(pfad);
  }
}
