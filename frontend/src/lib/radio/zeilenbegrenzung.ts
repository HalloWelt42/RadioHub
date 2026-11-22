// Labels in höchstens `zeilen` Zeilen (RAD-59): alle stehen in voller Länge, so weit Platz ist; passt nicht alles, nimmt
// das letzte sichtbare Label den Rest auf und kürzt sich mit ... (CSS). Die Aktion misst die Zeilen der gezeigten
// Kinder und meldet, wie viele Einträge vor dem Rest-Label stehen; bei neuer Breite misst sie von vorn.
import type { Action } from "svelte/action";

export interface Zeilenbegrenzung {
  zeilen: number;
  /** Anzahl aller Einträge; ändert sie sich, misst die Aktion neu */
  anzahl: number;
  /** null: alle zeigen (zum Messen); n: die ersten n - 1 Einträge und ein Rest-Label ab Eintrag n - 1 */
  setzen: (bis: number | null) => void;
}

export const zeilenbegrenzung: Action<HTMLElement, Zeilenbegrenzung> = (el, anfang) => {
  let stand = anfang;
  let breite = el.clientWidth;

  /** Index des ersten Kinds jenseits der erlaubten Zeilen, sonst null */
  function ueberlauf(): number | null {
    const kinder = [...el.children] as HTMLElement[];
    const oben = [...new Set(kinder.map((k) => k.offsetTop))].sort((a, b) => a - b);
    if (oben.length <= stand.zeilen) return null;
    const grenze = oben[stand.zeilen];
    return kinder.findIndex((k) => k.offsetTop >= grenze);
  }

  /** nach dem Zeichnen der Einträge (vor dem Anzeigen) messen und so lange kürzen, bis alles in die Zeilen passt */
  let bis: number | null = null;
  function messen() {
    queueMicrotask(() => {
      const erste = ueberlauf();
      if (erste === null) return;
      const neu = Math.max(1, erste);
      if (neu === bis) return;                     // kürzer geht es nicht: das Rest-Label steht allein
      bis = neu;
      stand.setzen(bis);
      messen();
    });
  }

  function vonVorn() {
    bis = null;
    stand.setzen(null);
    messen();
  }

  const beobachter = new ResizeObserver(() => {
    if (el.clientWidth === breite) return;
    breite = el.clientWidth;
    vonVorn();
  });
  beobachter.observe(el);
  vonVorn();

  return {
    update(neu) {
      const anders = neu.anzahl !== stand.anzahl || neu.zeilen !== stand.zeilen;
      stand = neu;
      if (anders) vonVorn();
    },
    destroy() {
      beobachter.disconnect();
    },
  };
};
