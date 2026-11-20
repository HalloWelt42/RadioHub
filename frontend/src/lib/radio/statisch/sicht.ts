// Sichtbarkeit je Sender aus Bestand und eigenen Angaben (wie backend/app/services/senderquelle/sichtbarkeit.py):
// ein Favorit ist immer sichtbar (als Ausnahme, wenn eine Regel ihn trifft); eine Freigabe hebt Regeln auf; sonst ist
// sichtbar, wen keine eingeschaltete Regel trifft. Je Gruppe von Varianten ist der beste sichtbare Sender der
// Vertreter (Favoriten zuerst). Die Sicht wird nach jeder Änderung als Ganzes neu gerechnet (wenige Millisekunden).
import type { Bestand, Bewertung, Grund, Regel } from "../typen";
import type { EigeneAngaben, GespeicherteRegel } from "./angaben";
import type { Senderbestand } from "./format";
import { ERKLAERUNG, titel, treffer } from "./regeln";
import { vergleichen } from "./text";

export interface Regeltreffer {
  regel: GespeicherteRegel;
  titel: string;
  /** getroffene Sender, aufsteigend */
  sender: Int32Array;
  /** 1 an jeder getroffenen Stelle */
  maske: Uint8Array;
}

function maskeVon(anzahl: number, sender: Int32Array): Uint8Array {
  const m = new Uint8Array(anzahl);
  for (const i of sender) m[i] = 1;
  return m;
}

export class Sicht {
  readonly favorit: Uint8Array;
  readonly freigegeben: Uint8Array;
  /** Zahl der eingeschalteten Regeln, die den Sender treffen */
  readonly getroffen: Uint16Array;
  readonly sichtbar: Uint8Array;
  readonly vertreter: Uint8Array;
  /** sichtbare Varianten der Gruppe (bei unsichtbaren 0) */
  readonly varianten: Int32Array;
  readonly sichtbarAnzahl: number;
  /** je Regel ihre Treffer; eingeschaltete in der Reihenfolge ihres Anlegens (Reihenfolge der Gründe) */
  readonly regeln: Map<string, Regeltreffer>;
  /** eigene Bewertungen je Sender (Zeilennummer) */
  readonly bewertungen: Map<number, Bewertung[]>;
  private readonly aktive: Regeltreffer[];

  constructor(private readonly b: Senderbestand, private readonly a: EigeneAngaben) {
    const n = b.anzahl;
    this.favorit = maskeVon(n, this.stellen(a.favoriten));
    this.freigegeben = maskeVon(n, this.stellen(a.freigaben));
    this.bewertungen = new Map();
    for (const [uuid, liste] of Object.entries(a.bewertungen)) {
      const i = b.nachUuid.get(uuid);
      if (i !== undefined) this.bewertungen.set(i, liste);
    }
    this.regeln = new Map(a.regeln.map((r) => {
      const sender = treffer(b, a, r.art, r.entwurf);
      return [r.id, { regel: r, titel: titel(b, r.art, r.entwurf), sender, maske: maskeVon(n, sender) }];
    }));
    this.aktive = [...this.regeln.values()].filter((t) => t.regel.an)
      .sort((x, y) => vergleichen(x.regel.angelegt_am, y.regel.angelegt_am));
    this.getroffen = new Uint16Array(n);
    for (const t of this.aktive) for (const i of t.sender) this.getroffen[i]++;
    this.sichtbar = new Uint8Array(n);
    let sichtbar = 0;
    for (let i = 0; i < n; i++) {
      this.sichtbar[i] = this.favorit[i] || this.freigegeben[i] || !this.getroffen[i] ? 1 : 0;
      sichtbar += this.sichtbar[i];
    }
    this.sichtbarAnzahl = sichtbar;
    this.vertreter = new Uint8Array(n);
    this.varianten = new Int32Array(n);
    for (const glieder of b.glieder.values()) this.gruppeRechnen(glieder);
  }

  private stellen(uuids: Iterable<string>): Int32Array {
    const liste: number[] = [];
    for (const u of uuids) {
      const i = this.b.nachUuid.get(u);
      if (i !== undefined) liste.push(i);
    }
    return Int32Array.from(liste);
  }

  /** besser zuerst: Favorit, Qualität, Bitrate, erreichbar (alle), Stimmen, uuid */
  private besser = (x: number, y: number): number => {
    const b = this.b;
    return this.favorit[y] - this.favorit[x] || b.qualitaetRang[y] - b.qualitaetRang[x] || b.kbps[y] - b.kbps[x]
      || b.stimmen[y] - b.stimmen[x] || vergleichen(b.uuid[x], b.uuid[y]);
  };

  private gruppeRechnen(glieder: number[]): void {
    let bester = -1;
    let zahl = 0;
    for (const i of glieder) {
      if (!this.sichtbar[i]) continue;
      zahl++;
      if (bester < 0 || this.besser(i, bester) < 0) bester = i;
    }
    for (const i of glieder) this.varianten[i] = this.sichtbar[i] ? zahl : 0;
    if (bester >= 0) this.vertreter[bester] = 1;
  }

  /** eingeschaltete Regeln, die den Sender treffen */
  gruende(i: number): Grund[] {
    if (!this.getroffen[i]) return [];
    return this.aktive.filter((t) => t.maske[i]).map((t) => ({ regel: t.regel.id, art: t.regel.art, titel: t.titel }));
  }

  /** sichtbar trotz Regel (Favorit oder Freigabe) */
  ausnahme(i: number): boolean {
    return !!this.sichtbar[i] && this.getroffen[i] > 0;
  }

  /** trifft eine andere eingeschaltete Regel als `ohne`? */
  andereRegel(i: number, ohne: string): boolean {
    return this.aktive.some((t) => t.regel.id !== ohne && t.maske[i]);
  }

  /** würde sichtbar, wenn diese Regel nicht mehr gilt */
  wuerdeSichtbar(i: number, t: Regeltreffer): boolean {
    return !this.sichtbar[i] && this.getroffen[i] - (t.regel.an ? 1 : 0) === 0;
  }

  bestand(): Bestand {
    let ausnahmen = 0;
    for (let i = 0; i < this.b.anzahl; i++) if (this.ausnahme(i)) ausnahmen++;
    return { gesamt: this.b.anzahl, sichtbar: this.sichtbarAnzahl, ausgeblendet: this.b.anzahl - this.sichtbarAnzahl,
             verschwunden: 0, favoriten: this.a.favoriten.length, ausnahmen };
  }

  /** Regel mit ihren Zahlen: betroffen, davon Favoriten, allein durch sie ausgeblendet */
  regel(id: string): Regel | null {
    const t = this.regeln.get(id);
    if (!t) return null;
    let favoriten = 0;
    let nurDiese = 0;
    for (const i of t.sender) {
      favoriten += this.favorit[i];
      if (!this.favorit[i] && !this.freigegeben[i] && this.getroffen[i] - (t.regel.an ? 1 : 0) === 0) nurDiese++;
    }
    const r = t.regel;
    return { id: r.id, art: r.art, an: r.an, herkunft: r.herkunft, titel: t.titel, erklaerung: ERKLAERUNG[r.art],
             entwurf: r.entwurf, betroffen: t.sender.length, favoriten, nur_diese: nurDiese, angelegt_am: r.angelegt_am,
             geaendert_am: r.geaendert_am };
  }

  /** alle Regeln, neueste zuerst, die Einzelsperren am Ende */
  alleRegeln(): Regel[] {
    const reihe = [...this.regeln.values()].map((t) => t.regel).sort((x, y) =>
      Number(x.art === "einzeln") - Number(y.art === "einzeln") || vergleichen(y.angelegt_am, x.angelegt_am) || vergleichen(x.id, y.id));
    return reihe.map((r) => this.regel(r.id) as Regel);
  }
}
