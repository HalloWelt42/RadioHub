/**
 * AudioAnalyser Stub
 *
 * Platzhalter fuer spaetere echte Audio-Analyse.
 * Aktuell deaktiviert weil createMediaElementSource() das Audio
 * durch den Web Audio Graph leitet und bei suspended AudioContext
 * den Ton blockiert. Zu fragil fuer Production.
 *
 * VU-Meter nutzt stattdessen die Simulation in HiFiVuMeter.svelte.
 */

export function connect() {}
export function ensureConnected() {}
export function getRMS() { return null; }
