// Sitzung der alten Datenschicht (RAD-6): nur eine Abweisung mit dem Kennzeichen der Sitzung meldet sie der Schale;
// der Kopf trägt den Token, den die Schale verbindet, und ohne Token keinen leeren.
import { describe, expect, it } from 'vitest';
import { antwortPruefen, kopf, sitzungVerbinden } from '../src/lib/sitzung';

const antwort = (status, kennzeichen) => ({ status, headers: new Headers(kennzeichen ? { 'www-authenticate': kennzeichen } : {}) });

describe('Sitzung', () => {
  it('meldet nur eine Abweisung mit dem Kennzeichen der Kellerwolke-Sitzung', () => {
    let abgewiesen = 0;
    sitzungVerbinden({ token: () => 't', abgewiesen: () => abgewiesen++ });
    antwortPruefen(antwort(401));                         // etwa von einem anderen Dienst weitergereicht
    antwortPruefen(antwort(403, 'Kellerwolke-Sitzung'));
    antwortPruefen(antwort(200));
    expect(abgewiesen).toBe(0);
    antwortPruefen(antwort(401, 'Kellerwolke-Sitzung'));
    expect(abgewiesen).toBe(1);
  });

  it('schickt ohne gespeicherten Token keinen leeren Kopf', () => {
    sitzungVerbinden({ token: () => '', abgewiesen: () => {} });
    expect(kopf({ 'Content-Type': 'application/json' })).toEqual({ 'Content-Type': 'application/json' });
  });

  it('trägt den Token der Schale im Kopf der Sitzung', () => {
    sitzungVerbinden({ token: () => 'abc', abgewiesen: () => {} });
    expect(kopf()).toEqual({ 'X-Kellerwolke-Sitzung': 'abc' });
  });
});
