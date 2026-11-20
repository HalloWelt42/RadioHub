/**
 * Wecktöne aus dem Gerät (RAD-15): jeder Ton wird beim Öffnen der Weckansicht rechnend erzeugt, ohne Netz und ohne Datei,
 * und läuft als Schleife, solange er weckt. Rein rechnend (Abtastwerte), ohne Web Audio: so prüfbar und überall gleich.
 * Die Namen stehen in den Sprachdateien (telefon.ton_<id>), die Reihenfolge hier ist die der Auswahl.
 */

/** Kennungen in der Reihenfolge der Auswahl; "doppelpiep" ist der bisherige Weckton und die Vorgabe */
export const WECKTOENE = ['doppelpiep', 'digital', 'glocke', 'glockenspiel', 'vogel', 'sanft', 'mechanisch', 'harfe', 'kuckuck'];
export const VORGABE = 'doppelpiep';

/** Gleichbleibender Zufall, damit ein Ton bei jedem Erzeugen gleich klingt */
function zufall(saat) {
  let s = saat;
  return () => ((s = (s * 16807) % 2147483647) / 2147483647);
}

/** Hüllkurve: weicher Einsatz, dann exponentiell abklingend */
const klang = (t, einsatz, abkling) => (t < 0 ? 0 : Math.min(1, t / einsatz) * Math.exp(-t / abkling));

/** Fügt einen Klang ab `start` Sekunden ein; was über das Ende hinausklingt, kommt am Anfang wieder (nahtlose Schleife) */
function einfuegen(daten, rate, start, dauer, wert) {
  const n = daten.length, von = Math.round(start * rate), bis = Math.round(dauer * rate);
  for (let i = 0; i < bis; i++) daten[(von + i) % n] += wert(i / rate);
}

function normalisieren(daten, spitze = 0.7) {
  let max = 0;
  for (const v of daten) max = Math.max(max, Math.abs(v));
  if (max > 0) for (let i = 0; i < daten.length; i++) daten[i] *= spitze / max;
  return daten;
}

const sinus = (f, t) => Math.sin(2 * Math.PI * f * t);

const ERZEUGER = {
  /** zwei kurze Pieptöne bei 1000 Hz, dann Ruhe (der bisherige Weckton) */
  doppelpiep(rate) {
    const d = new Float32Array(Math.round(rate * 1.6));
    for (const [von, bis] of [[0, 0.18], [0.28, 0.46]]) {
      einfuegen(d, rate, von, bis - von, (t) => Math.min(1, t / 0.01, (bis - von - t) / 0.01) * sinus(1000, t));
    }
    return d;
  },
  /** Digitalwecker: vier schnelle Pieptöne, Pause */
  digital(rate) {
    const d = new Float32Array(Math.round(rate * 1.3));
    for (let k = 0; k < 4; k++) {
      einfuegen(d, rate, k * 0.16, 0.08, (t) => Math.min(1, t / 0.004, (0.08 - t) / 0.004) * (sinus(2600, t) + 0.3 * sinus(7800, t)));
    }
    return d;
  },
  /** angeschlagene Glocke: Teiltöne einer echten Glocke, lang ausklingend */
  glocke(rate) {
    const d = new Float32Array(Math.round(rate * 2.6));
    const teile = [[1, 1, 2.2], [2.01, 0.6, 1.6], [2.76, 0.45, 1.2], [4.07, 0.3, 0.9], [5.4, 0.2, 0.6]];
    einfuegen(d, rate, 0, 2.6, (t) => teile.reduce((s, [r, a, z]) => s + a * klang(t, 0.003, z) * sinus(523 * r, t), 0));
    return d;
  },
  /** Glockenspiel: pentatonische Töne in ruhiger Folge */
  glockenspiel(rate) {
    const lang = 3.6, d = new Float32Array(Math.round(rate * lang));
    const toene = [523.25, 587.33, 659.25, 783.99, 880, 1046.5], z = zufall(11);
    for (let k = 0; k < 8; k++) {
      const f = toene[Math.floor(z() * toene.length)];
      einfuegen(d, rate, k * 0.42, 1.6, (t) => klang(t, 0.002, 0.5) * (sinus(f, t) + 0.25 * sinus(f * 4, t) * Math.exp(-t / 0.08)));
    }
    return d;
  },
  /** Vogelstimmen: kurze aufsteigende Rufe in Gruppen, dazu ein tieferer Vogel */
  vogel(rate) {
    const lang = 3.2, d = new Float32Array(Math.round(rate * lang)), z = zufall(5);
    const ruf = (f0, f1, dauer) => (t) => {
      const huelle = Math.sin(Math.PI * Math.min(1, t / dauer)) ** 2;
      const phase = 2 * Math.PI * (f0 * t + ((f1 - f0) * t * t) / (2 * dauer));
      return huelle * Math.sin(phase);
    };
    let zeit = 0.05;
    for (let g = 0; g < 3; g++) {
      const anzahl = 3 + Math.floor(z() * 3);
      for (let k = 0; k < anzahl; k++) { einfuegen(d, rate, zeit, 0.06, ruf(3200 + z() * 400, 4600 + z() * 500, 0.06)); zeit += 0.09; }
      zeit += 0.35 + z() * 0.3;
    }
    for (const s of [0.6, 1.9]) einfuegen(d, rate, s, 0.22, ruf(2100, 2700, 0.22));
    return d;
  },
  /** sanft: ein weicher Akkord, der an- und abschwillt */
  sanft(rate) {
    const lang = 6, d = new Float32Array(Math.round(rate * lang));
    const akkord = [220, 277.18, 329.63, 440];
    einfuegen(d, rate, 0, lang, (t) => Math.sin((Math.PI * t) / lang) ** 2 * akkord.reduce((s, f) => s + sinus(f, t) + 0.4 * sinus(f * 1.003, t), 0));
    return d;
  },
  /** mechanischer Wecker: schnell klöppelnde Glocke, Pause */
  mechanisch(rate) {
    const d = new Float32Array(Math.round(rate * 2.2)), z = zufall(3);
    for (let k = 0; k < 30; k++) {
      const s = k / 22;
      einfuegen(d, rate, s, 0.08, (t) => klang(t, 0.0005, 0.03) * (sinus(1900, t) + 0.7 * sinus(2650, t) + 0.4 * sinus(3810, t)) + klang(t, 0.0002, 0.004) * (z() * 2 - 1) * 0.6);
    }
    return d;
  },
  /** Harfe: gezupfte Saiten (Karplus-Strong) als aufsteigender Bogen */
  harfe(rate) {
    const lang = 3.4, d = new Float32Array(Math.round(rate * lang)), z = zufall(17);
    [220, 261.63, 329.63, 440, 523.25, 659.25].forEach((f, k) => {
      const periode = Math.round(rate / f), saite = new Float32Array(periode).map(() => z() * 2 - 1);
      const n = Math.round(rate * 1.8), ton = new Float32Array(n);
      for (let i = 0; i < n; i++) {
        const j = i % periode;
        ton[i] = saite[j];
        saite[j] = 0.996 * 0.5 * (saite[j] + saite[(j + 1) % periode]);
      }
      einfuegen(d, rate, k * 0.18, 1.8, (t) => ton[Math.min(n - 1, Math.round(t * rate))]);
    });
    return d;
  },
  /** Kuckuck: zwei weiche Töne, zweimal, dann Ruhe */
  kuckuck(rate) {
    const d = new Float32Array(Math.round(rate * 2.8));
    const ruf = (f) => (t) => Math.sin(Math.PI * Math.min(1, t / 0.3)) * (sinus(f, t) + 0.2 * sinus(f * 2, t));
    [[0, 659.25], [0.36, 523.25], [1.0, 659.25], [1.36, 523.25]].forEach(([s, f]) => einfuegen(d, rate, s, 0.3, ruf(f)));
    return d;
  },
};

/** Abtastwerte eines Wecktons (mono, eine Schleife), unbekannte Kennung: die Vorgabe */
export function wecktonDaten(id, rate) {
  const erzeugen = ERZEUGER[id] ?? ERZEUGER[VORGABE];
  return normalisieren(erzeugen(rate));
}
