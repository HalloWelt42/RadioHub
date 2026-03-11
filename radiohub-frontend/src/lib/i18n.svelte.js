/**
 * Reaktiver i18n-Wrapper für Svelte 5
 *
 * Nutzt einen $state-Counter, der bei Sprachwechsel hochgezählt wird.
 * Dadurch werden alle Template-Stellen, die t() aufrufen, neu evaluiert.
 *
 * Nutzung:
 *   import { t } from '../../lib/i18n.svelte.js';
 *   {t('nav.tuner')}
 */
import { t as rawT, setLanguage, currentLanguage, availableLanguages, onLanguageChange } from './i18n.js';

// Reaktiver Counter - bei Sprachwechsel wird _v erhöht -> Svelte re-rendert
let _v = $state(0);
onLanguageChange(() => { _v++; });

/**
 * Reaktive Übersetzungsfunktion.
 * Liest intern _v, dadurch entsteht eine Svelte-Dependency.
 */
export function t(key, params) {
  void _v;
  return rawT(key, params);
}

export { setLanguage, currentLanguage, availableLanguages, onLanguageChange };
