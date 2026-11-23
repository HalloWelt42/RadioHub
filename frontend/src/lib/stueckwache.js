// Wache über das Laden der Tonstücke (RAD-130): lädt hls.js dasselbe Stück immer wieder, ohne dass es weitergeht (gesehen am Telefon
// mit bis zu 68 Anfragen je Sekunde), hört man Aussetzer. Reine Regel ohne Ton: sie sagt, was zu tun ist.
//   'weiter'  nichts
//   'vor'     kurz ruhen und weiter
//   'neu'     es half nicht: Wiedergabe neu ansetzen
export const WIEDERHOLT = 5;            // so oft dasselbe Stück in kurzer Zeit gilt als Schleife
export const FENSTER_MS = 4000;
export const RUHE_MS = 15000;           // so lange nach dem Vorsprung noch eine Schleife: neu ansetzen

export class Stueckwache {
  constructor() {
    this.nummer = null;
    this.zeiten = [];
    this.vorAm = -Infinity;
  }

  geladen(nummer, jetzt) {
    if (nummer !== this.nummer) {
      this.nummer = nummer;
      this.zeiten = [];
    }
    this.zeiten = [...this.zeiten.filter((t) => jetzt - t < FENSTER_MS), jetzt];
    if (this.zeiten.length < WIEDERHOLT) return 'weiter';
    this.zeiten = [];
    const neu = jetzt - this.vorAm < RUHE_MS;
    this.vorAm = neu ? -Infinity : jetzt;
    return neu ? 'neu' : 'vor';
  }
}
