import { describe, expect, it } from 'vitest';
import { geste } from '../src/lib/telefon/geste.js';
import { Waechter, wartezeit, GNADE_MS, GRENZE_OHNE_WECKER } from '../src/lib/telefon/verbindung.svelte.js';

describe('Gesten', () => {
  const p = (x, y, t) => ({ x, y, t });
  it('Wischen, Antippen, langer Druck sauber getrennt', () => {
    expect(geste(p(300, 200, 0), p(150, 210, 300))).toBe('links');
    expect(geste(p(150, 200, 0), p(320, 190, 300))).toBe('rechts');
    expect(geste(p(150, 200, 0), p(154, 203, 120))).toBe('tippen');
    expect(geste(p(150, 200, 0), p(152, 201, 700))).toBe('lang');
    expect(geste(p(150, 200, 0), p(200, 300, 300))).toBeNull();     // eher senkrecht
    expect(geste(p(150, 200, 0), p(300, 200, 1500))).toBeNull();    // zu langsam für ein Wischen
    expect(geste(p(150, 200, 0), p(180, 200, 200))).toBeNull();     // zu kurz, aber kein Antippen
  });
});

function aufbau({ wecker }) {
  let hoerbar = false;
  const starts = [];
  const ton = { an: () => { ton.laeuft = true; }, aus: () => { ton.laeuft = false; }, laeuft: false };
  const w = new Waechter({ hoerbar: () => hoerbar, starten: (z) => { starts.push(z); }, ton });
  w.bewachen('sender', { wecker });
  return { w, ton, starts, setzeHoerbar: (h) => { hoerbar = h; } };
}

function lauf(w, bisMs, schritt = 1000, ab = 0) {
  for (let t = ab; t <= bisMs; t += schritt) w.takt(t);
}

describe('Wiederverbinden', () => {
  it('Plan 2, 5, 10, 20, dann 30 Sekunden', () => {
    expect([1, 2, 3, 4, 5, 6].map(wartezeit)).toEqual([2, 5, 10, 20, 30, 30]);
  });

  it('nach der Gnadenfrist Versuche im Plan, beim Wecken ab dem dritten mit Weckton', () => {
    const { w, ton, starts } = aufbau({ wecker: true });
    const versuchZeiten = [];
    for (let t = 0; t <= GNADE_MS + 200000; t += 1000) {
      const vorher = starts.length;
      w.takt(t);
      if (starts.length > vorher) versuchZeiten.push(t);
    }
    const abstaende = versuchZeiten.slice(1).map((t, i) => (t - versuchZeiten[i]) / 1000);
    expect(versuchZeiten[0]).toBe(GNADE_MS + 2000);
    expect(abstaende.slice(0, 5)).toEqual([5, 10, 20, 30, 30]);
    expect(ton.laeuft).toBe(true);
    expect(w.zustand).toBe('gestoert');
  });

  it('kommt der Sender, ist der Weckton weg und alles zurückgesetzt', () => {
    const { w, ton, setzeHoerbar } = aufbau({ wecker: true });
    lauf(w, 60000);
    expect(ton.laeuft).toBe(true);
    setzeHoerbar(true);
    w.takt(61000);
    expect(ton.laeuft).toBe(false);
    expect(w.zustand).toBe('ok');
    expect(w.versuche).toBe(0);
  });

  it('ohne Wecker kein Weckton und eine Grenze', () => {
    const { w, ton, starts } = aufbau({ wecker: false });
    lauf(w, 600000);
    expect(ton.laeuft).toBe(false);
    expect(starts.length).toBe(GRENZE_OHNE_WECKER);
    w.lassen();
    expect(w.zustand).toBe('aus');
  });
});

import { hoerbarMesser } from '../src/lib/telefon/verbindung.svelte.js';

describe('Hörbar', () => {
  it('nur wenn die Zeit am Element weiterläuft, auch wenn es später kommt', () => {
    let uhr = 0;
    let el = null;
    const hoerbar = hoerbarMesser(() => el, () => uhr);
    expect(hoerbar()).toBe(false);
    el = { paused: false, currentTime: 1 };
    expect(hoerbar()).toBe(true);
    uhr = 5000;                       // Zeit steht seit 5 s: kein Ton
    expect(hoerbar()).toBe(false);
    el.currentTime = 2;
    expect(hoerbar()).toBe(true);
    el.paused = true;
    expect(hoerbar()).toBe(false);
  });
});
