import { describe, expect, it } from 'vitest';
import { ansageFaellig, imZeitraum, planPruefen, zeitraumZeiten, PLAN_VORGABE } from '../src/lib/telefon/zeitplan.js';

const um = (h, m) => new Date(2026, 9, 30, h, m);
const plan = (teil = {}) => ({ an: true, ...PLAN_VORGABE, ...teil });

describe('Zeitplan der Zeitansage', () => {
  it('prüft gespeicherte Pläne, Unbekanntes fällt auf die Vorgabe', () => {
    expect(planPruefen(null)).toEqual(PLAN_VORGABE);
    expect(planPruefen({ abstand: 7, von: '25:00', bis: '9:00', bedingung: 'nie' })).toEqual(PLAN_VORGABE);
    expect(planPruefen({ abstand: 15, von: '06:00', bis: '09:00', bedingung: 'immer' }))
      .toEqual({ abstand: 15, von: '06:00', bis: '09:00', bedingung: 'immer' });
  });

  it('Zeitraum mit Grenzen, über Mitternacht, leer = immer', () => {
    const morgens = { von: '06:00', bis: '09:00' };
    expect(imZeitraum(morgens, um(5, 59))).toBe(false);
    expect(imZeitraum(morgens, um(6, 0))).toBe(true);
    expect(imZeitraum(morgens, um(9, 0))).toBe(true);
    expect(imZeitraum(morgens, um(9, 1))).toBe(false);
    const nachts = { von: '22:00', bis: '06:00' };
    expect(imZeitraum(nachts, um(23, 30))).toBe(true);
    expect(imZeitraum(nachts, um(3, 0))).toBe(true);
    expect(imZeitraum(nachts, um(12, 0))).toBe(false);
    expect(imZeitraum({ von: '06:00', bis: '' }, um(12, 0))).toBe(true);
  });

  it('Abstand zählt ab Mitternacht', () => {
    const immer = plan({ bedingung: 'immer', abstand: 15 });
    expect(ansageFaellig(immer, um(7, 15))).toBe(true);
    expect(ansageFaellig(immer, um(7, 10))).toBe(false);
    expect(ansageFaellig(plan({ bedingung: 'immer', abstand: 60 }), um(7, 0))).toBe(true);
    expect(ansageFaellig(plan({ bedingung: 'immer', abstand: 60 }), um(7, 30))).toBe(false);
  });

  it('unabhängig vom Wecker oder nur mit scharfem Wecker', () => {
    expect(ansageFaellig(plan({ bedingung: 'immer' }), um(14, 5))).toBe(true);
    expect(ansageFaellig(plan({ bedingung: 'wecker' }), um(14, 5))).toBe(false);
    expect(ansageFaellig(plan({ bedingung: 'wecker' }), um(14, 5), { weckerScharf: true })).toBe(true);
    expect(ansageFaellig({ ...plan({ bedingung: 'immer' }), an: false }, um(14, 5))).toBe(false);
  });

  it('beim Wecken gilt der Wecker: klingelt keine Ansage, schlummert alle 5 Minuten', () => {
    const eng = plan({ bedingung: 'wecker', abstand: 30, von: '20:00', bis: '21:00' });
    expect(ansageFaellig(eng, um(6, 5), { weckerScharf: true, klingelt: true })).toBe(false);
    expect(ansageFaellig(eng, um(6, 5), { schlummert: true })).toBe(true);
    expect(ansageFaellig(eng, um(6, 7), { schlummert: true })).toBe(false);
    expect(ansageFaellig({ ...eng, an: false }, um(6, 5), { schlummert: true })).toBe(false);
  });

  it('wählbare Grenzen in halben Stunden', () => {
    const z = zeitraumZeiten();
    expect(z).toHaveLength(48);
    expect(z[0]).toBe('00:00');
    expect(z[13]).toBe('06:30');
    expect(z.at(-1)).toBe('23:30');
  });
});
