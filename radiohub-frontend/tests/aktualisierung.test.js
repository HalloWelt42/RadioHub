import { beforeEach, describe, expect, it } from 'vitest';

globalThis.document ??= { activeElement: null };
globalThis.window ??= { location: { origin: 'http://test', hostname: 'test', port: '', protocol: 'http:' } };

const { ruhig, sperren, freigeben } = await import('../src/lib/aktualisierung.svelte.js');
const { bausteineFuer } = await import('../src/lib/telefon/zeitansage.svelte.js');

describe('Selbst-Aktualisierung wartet auf einen ruhigen Moment', () => {
  const still = { isPlaying: false, isPaused: false, isRecording: false };
  beforeEach(() => { document.activeElement = null; freigeben('probe'); });

  it('nie während Wiedergabe, Aufnahme, Ansage, Sperre oder Eingabe', () => {
    expect(ruhig(still)).toBe(true);
    expect(ruhig({ ...still, isPlaying: true })).toBe(false);
    expect(ruhig({ ...still, isPlaying: true, isPaused: true })).toBe(true);
    expect(ruhig({ ...still, isRecording: true })).toBe(false);
    expect(ruhig(still, true)).toBe(false);
    sperren('probe');
    expect(ruhig(still)).toBe(false);
    freigeben('probe');
    document.activeElement = { tagName: 'INPUT' };
    expect(ruhig(still)).toBe(false);
  });
});

describe('Zeitansage', () => {
  it('setzt die Bausteine zusammen, zur vollen Stunde ohne Minuten', () => {
    expect(bausteineFuer(new Date(2026, 9, 28, 5, 34))).toEqual(['es-ist', 'stunde-05', 'minute-34']);
    expect(bausteineFuer(new Date(2026, 9, 28, 0, 0))).toEqual(['es-ist', 'stunde-00']);
  });
});
