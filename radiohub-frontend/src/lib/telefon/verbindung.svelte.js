/**
 * Wächter der Wiedergabe in der Weckeransicht: ist nichts zu hören, obwohl etwas laufen soll (Fehler, Abbruch, kein
 * Ton), wird neu verbunden, in wachsenden Abständen. Beim Wecken ohne Ende und ab dem dritten Versuch zusätzlich mit
 * Weckton aus dem Gerät, damit niemand verschläft; sonst mit Grenze. Sobald etwas zu hören ist: alles zurück.
 *
 * Getaktet wird von außen (`takt`, jede Sekunde), so lässt sich der Plan ohne echte Zeit prüfen.
 */

export const PLAN_S = [2, 5, 10, 20];      // Abstände der ersten Versuche
export const DANACH_S = 30;                // danach so oft
export const GNADE_MS = 6000;              // so lange darf ein Sender zum Anlaufen brauchen
export const ERSATZTON_AB = 3;             // ab diesem Versuch beim Wecken zusätzlich der Weckton
export const GRENZE_OHNE_WECKER = 6;       // ohne Wecker höchstens so viele Versuche

/** Ob gerade etwas laufen soll: Wiedergabe gestartet ja, Pause oder Stopp durch den Menschen nein. Unterscheidet einen
 * gewollten Halt von einem Abbruch. */
export const wunsch = $state({ spielen: false });

/** Wartezeit vor dem Versuch Nummer `versuch` (ab 1). */
export function wartezeit(versuch) {
  return versuch <= PLAN_S.length ? PLAN_S[versuch - 1] : DANACH_S;
}

/** Läuft am Audio-Element Ton? Die Zeit muss in den letzten Sekunden weitergelaufen sein (auch leise gezogen oder
 * stumm während der Zeitansage, dann läuft sie weiter). */
export function hoerbarMesser(element, jetzt = () => Date.now(), frist_ms = 3000) {
  const holen = typeof element === 'function' ? element : () => element;   // das Element kann später kommen
  let zuletzt = -1;
  let seit = 0;
  return () => {
    const el = holen();
    if (!el || el.paused) return false;
    const t = el.currentTime;
    if (t !== zuletzt) { zuletzt = t; seit = jetzt(); }
    return t > 0 && jetzt() - seit <= frist_ms;
  };
}

export class Waechter {
  zustand = $state('aus');        // 'aus' | 'ok' | 'verbindet' | 'gestoert'
  versuche = $state(0);
  ersatzton = $state(false);

  /** hoerbar(): bool; starten(ziel): Promise; ton: { an(), aus() } */
  constructor({ hoerbar, starten, ton }) {
    this._hoerbar = hoerbar;
    this._starten = starten;
    this._ton = ton;
    this._ziel = null;
    this._wecker = false;
    this._stummSeit = null;
    this._naechster = null;
  }

  /** Ab jetzt soll `ziel` (Sender oder Folge) zu hören sein. */
  bewachen(ziel, { wecker = false } = {}) {
    this._ziel = ziel;
    this._wecker = wecker;
    this._zuruecksetzen();
    this.zustand = 'verbindet';
  }

  /** Nichts soll mehr laufen (Pause, Aus, Ansicht verlassen). */
  lassen() {
    this._ziel = null;
    this._zuruecksetzen();
    this.zustand = 'aus';
  }

  get ziel() { return this._ziel; }

  _zuruecksetzen() {
    this.versuche = 0;
    this._stummSeit = null;
    this._naechster = null;
    if (this.ersatzton) { this._ton.aus(); this.ersatzton = false; }
  }

  takt(jetzt) {
    if (!this._ziel) return;
    if (this._hoerbar()) {
      this._zuruecksetzen();
      this.zustand = 'ok';
      return;
    }
    this._stummSeit ??= jetzt;
    if (jetzt - this._stummSeit < GNADE_MS) return;
    const grenze = this._wecker ? Infinity : GRENZE_OHNE_WECKER;
    if (this.versuche >= grenze) { this.zustand = 'gestoert'; return; }
    this.zustand = this.versuche ? 'gestoert' : 'verbindet';
    this._naechster ??= jetzt + wartezeit(1) * 1000;
    if (jetzt < this._naechster) return;
    this.versuche += 1;
    this._naechster = jetzt + wartezeit(this.versuche + 1) * 1000;
    Promise.resolve(this._starten(this._ziel)).catch(() => {});
    if (this._wecker && this.versuche >= ERSATZTON_AB && !this.ersatzton) {
      this._ton.an();
      this.ersatzton = true;
    }
  }
}
