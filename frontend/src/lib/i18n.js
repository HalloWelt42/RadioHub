/**
 * RadioHub i18n v2 - Reaktives Übersetzungssystem mit 20 Sprachen
 *
 * Nutzung:
 *   import { t, setLanguage, currentLanguage } from './i18n.js';
 *   t('nav.tuner')           -> 'TUNER'
 *   t('toast.recGestartet')  -> 'Aufnahme gestartet'
 *   setLanguage('en')        -> Wechselt auf Englisch
 *
 * Fallback-Kette: aktuelle Sprache -> Englisch -> Deutsch -> Key
 */
import de from './locales/de.js';
import en from './locales/en.js';

// Locale-Dateien werden lazy geladen. Nur DE + EN sind initial da.
// Weitere Sprachen können später als Dateien ergänzt werden.
const locales = { de, en };

// Reaktiver State (kein Svelte-Import nötig - einfaches Observer-Pattern)
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
 * Sprache wechseln (mit Lazy-Loading für nicht-geladene Locales)
 */
export async function setLanguage(lang) {
  const entry = availableLanguages.find(l => l.code === lang);
  if (!entry) {
    console.warn(`i18n: Unbekannte Sprache "${lang}", Fallback auf "de"`);
    lang = 'de';
  }
  if (lang === _lang) return;

  // Lazy-Load: Locale nachladen wenn noch nicht vorhanden
  if (!locales[lang]) {
    try {
      const mod = await import(`./locales/${lang}.js`);
      locales[lang] = mod.default;
    } catch (e) {
      console.warn(`i18n: Locale "${lang}" nicht ladbar, Fallback auf EN/DE`);
    }
  }

  _lang = lang;
  _translations = locales[lang] || {};
  // Alle Listener benachrichtigen
  for (const fn of _listeners) {
    try { fn(lang); } catch (e) { /* ignore */ }
  }
}

/**
 * Listener für Sprachwechsel registrieren
 * @returns Unsubscribe-Funktion
 */
export function onLanguageChange(fn) {
  _listeners.add(fn);
  return () => _listeners.delete(fn);
}

/**
 * Wert in verschachteltem Objekt per Dot-Notation lesen
 */
function resolve(obj, parts) {
  let result = obj;
  for (const part of parts) {
    if (result && typeof result === 'object' && part in result) {
      result = result[part];
    } else {
      return undefined;
    }
  }
  return typeof result === 'string' ? result : undefined;
}

/**
 * Übersetzung abrufen (Dot-Notation)
 * Fallback-Kette: aktuelle Sprache -> EN -> DE -> Key
 *
 * @param {string} key - z.B. 'nav.tuner' oder 'toast.recGestartet'
 * @param {Object} params - Optionale Platzhalter {hours: 6} für '{hours}'
 * @returns {string}
 */
export function t(key, params = null) {
  const parts = key.split('.');

  // 1. Aktuelle Sprache
  let result = resolve(_translations, parts);
  // 2. Fallback: Englisch
  if (result === undefined && _lang !== 'en') {
    result = resolve(locales.en, parts);
  }
  // 3. Fallback: Deutsch
  if (result === undefined && _lang !== 'de') {
    result = resolve(locales.de, parts);
  }
  // 4. Key zurückgeben
  if (result === undefined) return key;

  // Platzhalter ersetzen
  if (params) {
    return result.replace(/\{(\w+)\}/g, (_, name) =>
      name in params ? String(params[name]) : `{${name}}`
    );
  }

  return result;
}

/**
 * Verfügbare Sprachen - 20 Sprachen mit Flaggen
 */
export const availableLanguages = [
  { code: 'de', label: 'Deutsch', flag: '\u{1F1E9}\u{1F1EA}' },
  { code: 'en', label: 'English', flag: '\u{1F1EC}\u{1F1E7}' },
  { code: 'fr', label: 'Fran\u00e7ais', flag: '\u{1F1EB}\u{1F1F7}' },
  { code: 'es', label: 'Espa\u00f1ol', flag: '\u{1F1EA}\u{1F1F8}' },
  { code: 'it', label: 'Italiano', flag: '\u{1F1EE}\u{1F1F9}' },
  { code: 'pt', label: 'Portugu\u00eas', flag: '\u{1F1F5}\u{1F1F9}' },
  { code: 'nl', label: 'Nederlands', flag: '\u{1F1F3}\u{1F1F1}' },
  { code: 'pl', label: 'Polski', flag: '\u{1F1F5}\u{1F1F1}' },
  { code: 'cs', label: '\u010Ce\u0161tina', flag: '\u{1F1E8}\u{1F1FF}' },
  { code: 'sk', label: 'Sloven\u010Dina', flag: '\u{1F1F8}\u{1F1F0}' },
  { code: 'da', label: 'Dansk', flag: '\u{1F1E9}\u{1F1F0}' },
  { code: 'sv', label: 'Svenska', flag: '\u{1F1F8}\u{1F1EA}' },
  { code: 'no', label: 'Norsk', flag: '\u{1F1F3}\u{1F1F4}' },
  { code: 'fi', label: 'Suomi', flag: '\u{1F1EB}\u{1F1EE}' },
  { code: 'hu', label: 'Magyar', flag: '\u{1F1ED}\u{1F1FA}' },
  { code: 'ro', label: 'Rom\u00e2n\u0103', flag: '\u{1F1F7}\u{1F1F4}' },
  { code: 'tr', label: 'T\u00fcrk\u00e7e', flag: '\u{1F1F9}\u{1F1F7}' },
  { code: 'ru', label: '\u0420\u0443\u0441\u0441\u043A\u0438\u0439', flag: '\u{1F1F7}\u{1F1FA}' },
  { code: 'ja', label: '\u65E5\u672C\u8A9E', flag: '\u{1F1EF}\u{1F1F5}' },
  { code: 'zh', label: '\u4E2D\u6587', flag: '\u{1F1E8}\u{1F1F3}' }
];
