// Zustand des Schnitt-Arbeitsplatzes (RAD-17, Entwurf aufnahmen.html): Marker, Stücke zwischen ihnen (Name, behalten
// oder verwerfen, Werbung aus den Sendedaten), Ausschnitt der Wellenform, Abspielkopf. Rein rechnend bis auf die Quelle; die Ansicht zeichnet nur.
import type { Schnittinfo, StueckWahl, Werbestelle } from "./quelle";

export interface Stueck extends StueckWahl {
  nr: number;
  /** ein Stück der Art Werbung: fällt beim Schneiden weg wie ein verworfenes (RAD-33, Entwurf aus RAD-32) */
  werbung: boolean;
}

/** kürzester sichtbarer Ausschnitt in Sekunden */
export const KLEINSTER_AUSSCHNITT = 5;
/** Marker näher als das an einem anderen gelten als derselbe */
const NAEHE = 0.05;

const runden = (t: number) => Math.round(t * 10) / 10;

export class Arbeitsplatz {
  dauer = $state(0);
  marker = $state<number[]>([]);
  /** Name je Startzeit eines Stücks; ohne Eintrag gilt der vorgeschlagene */
  namen = $state<Record<string, string>>({});
  /** verworfene Stücke, nach Startzeit */
  verworfen = $state<Set<string>>(new Set());
  /** Stücke der Art Werbung, nach Startzeit */
  werbung = $state<Set<string>>(new Set());
  von = $state(0);
  bis = $state(0);
  kopf = $state(0);
  mitlaufen = $state(true);
  /** Höhe der Wellenform als Vielfaches (nur Darstellung) */
  hoehe = $state(1);
  private vorschlaege: { start: number; titel: string }[] = [];

  /** aus der Info des Servers: die bisherigen Stücke werden Marker und Namen */
  uebernehmen(info: Schnittinfo): void {
    this.dauer = info.dauer;
    this.marker = info.stuecke.slice(1).map((s) => runden(s.von)).filter((t) => t > 0 && t < info.dauer);
    this.vorschlaege = info.stuecke.map((s) => ({ start: runden(s.von), titel: s.name }));
    this.namen = {};
    this.verworfen = new Set();
    this.werbung = new Set();
    this.von = 0;
    this.bis = info.dauer;
    this.kopf = 0;
  }

  get stuecke(): Stueck[] {
    const grenzen = [0, ...this.marker, this.dauer];
    return grenzen.slice(0, -1).map((von, i) => {
      const schluessel = von.toFixed(1);
      const vorschlag = [...this.vorschlaege].reverse().find((v) => v.start <= von + NAEHE)?.titel ?? `Teil ${i + 1}`;
      const werbung = this.werbung.has(schluessel);
      return { nr: i + 1, von, bis: grenzen[i + 1], name: this.namen[schluessel] ?? vorschlag, werbung,
               behalten: !werbung && !this.verworfen.has(schluessel) };
    });
  }

  get behalten(): number {
    return this.stuecke.filter((s) => s.behalten).length;
  }

  markerSetzen(t: number): void {
    const z = runden(Math.min(Math.max(t, 0), this.dauer));
    if (z <= 0 || z >= this.dauer || this.marker.some((m) => Math.abs(m - z) < NAEHE)) return;
    this.marker = [...this.marker, z].sort((a, b) => a - b);
  }

  markerEntfernen(i: number): void {
    this.marker = this.marker.filter((_, j) => j !== i);
  }

  markerVerschieben(i: number, t: number): void {
    const z = runden(Math.min(Math.max(t, 0.1), this.dauer - 0.1));
    this.marker = this.marker.map((m, j) => (j === i ? z : m)).sort((a, b) => a - b);
  }

  /** Marker an die beim Aufnehmen erkannten Titelwechsel; deren Titel werden die Namen */
  ausTitelwechseln(wechsel: { start: number; titel: string }[]): void {
    this.vorschlaege = wechsel.map((w) => ({ start: runden(w.start), titel: w.titel }));
    this.marker = [...new Set(wechsel.map((w) => runden(w.start)).filter((t) => t > 0 && t < this.dauer))].sort((a, b) => a - b);
    this.namen = {};
    this.verworfen = new Set();
    this.werbung = new Set();
  }

  /** Werbestellen als Stücke der Art Werbung: Marker an Anfang und Ende jeder Stelle (die übrigen Marker bleiben),
   *  das Stück dazwischen heißt nach dem Werbenden und fällt beim Schneiden weg */
  werbestellenUebernehmen(stellen: Werbestelle[], name: (s: Werbestelle) => string): void {
    const innen = (t: number) => t > 0 && t < this.dauer;
    const neu = stellen.map((s) => ({ ...s, von: runden(Math.max(0, s.von)), bis: runden(Math.min(this.dauer, s.bis)) })).filter((s) => s.bis > s.von);
    let marker = [...this.marker];
    for (const s of neu) for (const t of [s.von, s.bis]) if (innen(t) && !marker.some((m) => Math.abs(m - t) < NAEHE)) marker.push(t);
    marker = marker.filter((m) => !neu.some((s) => m > s.von + NAEHE && m < s.bis - NAEHE));    // keine Marker mitten in der Werbung
    this.marker = marker.sort((a, b) => a - b);
    const werbung = new Set(this.werbung), namen = { ...this.namen };
    for (const s of neu) {
      const k = s.von.toFixed(1);
      werbung.add(k);
      namen[k] = name(s);
    }
    this.werbung = werbung;
    this.namen = namen;
  }

  leeren(): void {
    this.marker = [];
    this.namen = {};
    this.verworfen = new Set();
    this.werbung = new Set();
  }

  /** Schalter eines Stücks: Werbung wird wieder ein gewöhnliches Stück (Irrtum), sonst behalten oder verwerfen */
  umschalten(s: Stueck): void {
    const k = s.von.toFixed(1);
    if (s.werbung) {
      const neu = new Set(this.werbung);
      neu.delete(k);
      this.werbung = neu;
      return;
    }
    const neu = new Set(this.verworfen);
    neu.has(k) ? neu.delete(k) : neu.add(k);
    this.verworfen = neu;
  }

  benennen(s: Stueck, name: string): void {
    this.namen = { ...this.namen, [s.von.toFixed(1)]: name };
  }

  /** Ausschnitt um seine Mitte verkleinern (faktor < 1) oder vergrößern (> 1) */
  zoomen(faktor: number, mitte = (this.von + this.bis) / 2): void {
    const breite = Math.min(this.dauer, Math.max(KLEINSTER_AUSSCHNITT, (this.bis - this.von) * faktor));
    const von = Math.min(Math.max(0, mitte - breite / 2), Math.max(0, this.dauer - breite));
    this.von = von;
    this.bis = von + breite;
  }

  alles(): void {
    this.von = 0;
    this.bis = this.dauer;
  }

  /** Ausschnitt so verschieben, dass `t` sichtbar ist (Mitlaufen: bei 70 Prozent) */
  zeigen(t: number): void {
    const breite = this.bis - this.von;
    if (t >= this.von && t <= this.bis - breite * 0.3) return;
    const von = Math.min(Math.max(0, t - breite * 0.7), Math.max(0, this.dauer - breite));
    this.von = von;
    this.bis = von + breite;
  }

  wahl(): StueckWahl[] {
    return this.stuecke.map(({ von, bis, name, behalten }) => ({ von, bis, name, behalten }));
  }
}
