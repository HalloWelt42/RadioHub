import { describe, expect, it, vi } from 'vitest';

// Umgebung ohne Browser: die Seite trägt das gebaute Skript index-alt.js
let neugeladen = 0;
const speicher = new Map();
globalThis.document ??= {};
globalThis.window ??= { location: { origin: 'http://test', hostname: 'test', port: '', protocol: 'http:' } };
document.querySelectorAll = () => [{ src: 'http://test/assets/index-alt.js' }];
document.addEventListener = () => {};
globalThis.location = { href: 'http://test/', reload: () => { neugeladen += 1; } };
globalThis.sessionStorage = { getItem: (k) => speicher.get(k) ?? null, setItem: (k, w) => speicher.set(k, w), removeItem: (k) => speicher.delete(k) };
let ausgeliefert = 'index-alt.js';
globalThis.fetch = async () => ({ text: async () => `<script type="module" src="/assets/${ausgeliefert}"></script>` });
vi.stubGlobal('setInterval', () => 0);

const { aktualisierung, neuLaden, pruefen, spaeter, starten } = await import('../src/lib/aktualisierung.svelte.js');
const { bausteineFuer } = await import('../src/lib/telefon/zeitansage.svelte.js');

describe('Neue Fassung: Hinweis statt Selbstladen (RAD-20)', () => {
  const app = { currentStation: { uuid: 's-1', name: 'Testwelle' }, currentEpisode: null, isPlaying: true, isPaused: false };
  starten(app);

  it('meldet eine neue Fassung, lädt aber nie von selbst neu, auch nicht während der Wiedergabe', async () => {
    await pruefen();
    expect(aktualisierung.neu).toBe(false);
    ausgeliefert = 'index-neu.js';
    await pruefen();
    expect(aktualisierung.neu).toBe(true);
    expect(neugeladen).toBe(0);
  });

  it('Später blendet den Hinweis aus, bis eine noch neuere Fassung kommt', async () => {
    spaeter();
    await pruefen();
    expect(aktualisierung.spaeter).toBe(true);
    ausgeliefert = 'index-neuer.js';
    await pruefen();
    expect(aktualisierung.spaeter).toBe(false);
    expect(neugeladen).toBe(0);
  });

  it('Neu laden nur auf Wunsch, mit Übergabe des laufenden Senders', () => {
    neuLaden();
    expect(neugeladen).toBe(1);
    expect(JSON.parse(speicher.get('radiohub_nach_aktualisierung')).station.uuid).toBe('s-1');
  });
});

describe('Zeitansage', () => {
  it('setzt die Bausteine zusammen, zur vollen Stunde ohne Minuten', () => {
    expect(bausteineFuer(new Date(2026, 9, 28, 5, 34))).toEqual(['es-ist', 'stunde-05', 'minute-34']);
    expect(bausteineFuer(new Date(2026, 9, 28, 0, 0))).toEqual(['es-ist', 'stunde-00']);
  });
});
