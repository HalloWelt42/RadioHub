/**
 * RadioHub i18n - Einfaches reaktives Übersetzungssystem
 *
 * Nutzung:
 *   import { t, setLanguage, currentLanguage } from './i18n.js';
 *   t('nav.tuner')           -> 'TUNER'
 *   t('toast.recGestartet')  -> 'Aufnahme gestartet'
 *   setLanguage('en')        -> Wechselt auf Englisch
 */
import de from './locales/de.js';
import en from './locales/en.js';

const locales = { de, en };

// Reaktiver State (kein Svelte-Import noetig - einfaches Observer-Pattern)
let _lang = 'de';
let _translations = locales.de;
const _listeners = new Set();

/**
 * Aktuelle Sprache abfragen
 */
export function currentLanguage() {
  return _lang;
}

/**
 * Sprache wechseln
 */
export function setLanguage(lang) {
  if (!locales[lang]) {
    console.warn(`i18n: Unbekannte Sprache "${lang}", Fallback auf "de"`);
    lang = 'de';
  }
  if (lang === _lang) return;
  _lang = lang;
  _translations = locales[lang];
  // Alle Listener benachrichtigen
  for (const fn of _listeners) {
    try { fn(lang); } catch (e) { /* ignore */ }
  }
}

/**
 * Listener fuer Sprachwechsel registrieren
 * @returns Unsubscribe-Funktion
 */
export function onLanguageChange(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

/**
 * Übersetzung abrufen (Dot-Notation)
 * Fallback: Key selbst zurueckgeben
 *
 * @param {string} key - z.B. 'nav.tuner' oder 'toast.recGestartet'
 * @param {Object} params - Optionale Platzhalter {hours: 6} fuer '{hours}'
 * @returns {string}
 */
export function t(key, params = null) {
  const parts = key.split('.');
  let result = _translations;

  for (const part of parts) {
    if (result && typeof result === 'object' && part in result) {
      result = result[part];
    } else {
      // Fallback: Deutsch versuchen
      let fallback = locales.de;
      for (const p of parts) {
        if (fallback && typeof fallback === 'object' && p in fallback) {
          fallback = fallback[p];
        } else {
          return key; // Nicht gefunden -> Key zurueck
        }
      }
      result = fallback;
      break;
    }
  }

  if (typeof result !== 'string') return key;

  // Platzhalter ersetzen
  if (params) {
    return result.replace(/\{(\w+)\}/g, (_, name) =>
      name in params ? String(params[name]) : `{${name}}`
    );
  }

  return result;
}

/**
 * Verfuegbare Sprachen
 */
export const availableLanguages = [
  { code: 'de', label: 'Deutsch', flag: 'DE' },
  { code: 'en', label: 'English', flag: 'EN' }
];
