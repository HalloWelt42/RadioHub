import { describe, expect, it } from 'vitest';
import { sonnenzeiten, istNacht } from '../src/lib/sonne.js';
import { naechsterZeitpunkt, naechsterWecker, faelligInMinute } from '../src/lib/wecker.js';
import { parsePath, pfadAusAlterAdresse } from '../src/lib/router.js';

const minuten = (d) => d.getUTCHours() * 60 + d.getUTCMinutes();

describe('Sonnenzeiten', () => {
  it('Berlin Sommer- und Winteranfang (UTC, auf 3 Minuten)', () => {
    const sommer = sonnenzeiten(new Date(2026, 5, 21, 12), 52.52, 13.405);
    expect(Math.abs(minuten(sommer.aufgang) - (2 * 60 + 43))).toBeLessThanOrEqual(3);
    expect(Math.abs(minuten(sommer.untergang) - (19 * 60 + 33))).toBeLessThanOrEqual(3);
    const winter = sonnenzeiten(new Date(2026, 11, 21, 12), 52.52, 13.405);
    expect(Math.abs(minuten(winter.aufgang) - (7 * 60 + 15))).toBeLessThanOrEqual(3);
    expect(Math.abs(minuten(winter.untergang) - (14 * 60 + 54))).toBeLessThanOrEqual(3);
  });
  it('Polartag und ohne Ort', () => {
    expect(sonnenzeiten(new Date(2026, 5, 21, 12), 78.2, 15.6).polar).toBe('tag');
    expect(istNacht(new Date(), null, null)).toBeNull();
  });
});

describe('Wecker', () => {
  const werktags = { aktiv: true, zeit: '06:30', tage: [1, 2, 3, 4, 5] };
  it('nächster Zeitpunkt überspringt das Wochenende', () => {
    const freitagAbend = new Date(2026, 9, 30, 20, 0); // Freitag
    expect(naechsterZeitpunkt(werktags, freitagAbend)).toEqual(new Date(2026, 10, 2, 6, 30));
    expect(naechsterZeitpunkt({ ...werktags, aktiv: false }, freitagAbend)).toBeNull();
  });
  it('der früheste aktive gewinnt, fällig genau in seiner Minute', () => {
    const sonntag = { aktiv: true, zeit: '09:00', tage: [7] };
    const n = naechsterWecker([werktags, sonntag], new Date(2026, 9, 31, 12, 0)); // Samstag
    expect(n.wecker).toBe(sonntag);
    expect(faelligInMinute(werktags, new Date(2026, 9, 29, 6, 30, 40))).toBe(true);
    expect(faelligInMinute(werktags, new Date(2026, 10, 1, 6, 30))).toBe(false);
  });
});

describe('Pfade', () => {
  it('sprechende Pfade und alte Adressen', () => {
    expect(parsePath('/podcasts/3/77')).toMatchObject({ tab: 'podcasts', segments: ['3', '77'] });
    expect(parsePath('/gibt-es-nicht')).toMatchObject({ tab: 'radio', path: '/radio' });
    expect(parsePath('/wecker').tab).toBe('wecker');
    expect(pfadAusAlterAdresse('#/tuner/abc')).toBe('/radio/abc');
    expect(pfadAusAlterAdresse('#/setup/radio/filter')).toBe('/einstellungen/radio/filter');
    expect(pfadAusAlterAdresse('')).toBeNull();
  });
});
