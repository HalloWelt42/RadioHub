// Darstellung vor dem Einhängen (RAD-6): Vorgaben, Übernahme des früheren Themas, Wahl merken, ungültige Werte.
import { beforeEach, describe, expect, it } from 'vitest';
import { DARSTELLUNG, darstellungVorab } from '../src/lib/darstellung-vorab';

let speicher;
let systemDunkel = false;
const wurzel = { dataset: {} };

beforeEach(() => {
  speicher = new Map();
  wurzel.dataset = {};
  systemDunkel = false;
  globalThis.localStorage = {
    getItem: (k) => (speicher.has(k) ? speicher.get(k) : null),
    setItem: (k, v) => speicher.set(k, String(v)),
  };
  globalThis.matchMedia = () => ({ matches: systemDunkel });
  globalThis.document = { documentElement: wurzel };
});

describe('Darstellung', () => {
  it('beginnt mit HiFi, Schrift normal und dem Thema des Systems', () => {
    systemDunkel = true;
    expect(darstellungVorab(DARSTELLUNG)).toEqual({ thema: 'system', schrift: 'mittel', vorlage: 'hifi' });
    expect(wurzel.dataset).toEqual({ theme: 'dunkel', schrift: 'mittel', vorlage: 'hifi' });
  });

  it('übernimmt das Thema von vor RAD-6 (dark, light)', () => {
    speicher.set('radiohub-theme', 'light');
    expect(darstellungVorab(DARSTELLUNG).thema).toBe('hell');
    expect(wurzel.dataset.theme).toBe('hell');
  });

  it('merkt eine Wahl und setzt Klassisch ohne Merkmal der Vorlage', () => {
    darstellungVorab(DARSTELLUNG, { schrift: 'sehr-gross', vorlage: 'klassisch', thema: 'dunkel' });
    expect(speicher.get('radiohub_schrift')).toBe('sehr-gross');
    expect(wurzel.dataset).toEqual({ theme: 'dunkel', schrift: 'sehr-gross' });
    expect(darstellungVorab(DARSTELLUNG)).toEqual({ thema: 'dunkel', schrift: 'sehr-gross', vorlage: 'klassisch' });
  });

  it('nimmt unbekannte Stufen und Themen als Vorgabe', () => {
    speicher.set('radiohub_schrift', 'riesig');
    speicher.set('radiohub_thema', 'bunt');
    const stand = darstellungVorab(DARSTELLUNG);
    expect(stand.schrift).toBe('mittel');
    expect(stand.thema).toBe('system');
  });
});
