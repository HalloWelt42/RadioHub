// Anmeldung (RAD-6): nur eine Abweisung mit dem Kennzeichen der Sitzung beendet sie; Codes zum Koppeln.
import { describe, expect, it } from 'vitest';
import { antwortPruefen, codeNormal, kopf, sitzung } from '../src/lib/sitzung.svelte.js';

const antwort = (status, kennzeichen) => ({ status, headers: new Headers(kennzeichen ? { 'www-authenticate': kennzeichen } : {}) });

describe('Sitzung', () => {
  it('endet nur bei einer Abweisung mit dem Kennzeichen der Kellerwolke-Sitzung', () => {
    sitzung.angemeldet = true;
    antwortPruefen(antwort(401));                         // etwa von einem anderen Dienst weitergereicht
    antwortPruefen(antwort(403, 'Kellerwolke-Sitzung'));
    expect(sitzung.angemeldet).toBe(true);
    antwortPruefen(antwort(401, 'Kellerwolke-Sitzung'));
    expect(sitzung.angemeldet).toBe(false);
  });

  it('schickt ohne gespeicherten Token keinen leeren Kopf', () => {
    expect(kopf({ 'Content-Type': 'application/json' })).toEqual({ 'Content-Type': 'application/json' });
  });

  it('liest Codes ohne Trenner und in Großbuchstaben', () => {
    expect(codeNormal('ab3d-ef7h')).toBe('AB3DEF7H');
    expect(codeNormal('abcdefghijk')).toBe('ABCDEFGH');
  });
});
