// Wirkung der Server-Einstellungen im laufenden Programm (RAD-11), an einer Stelle: beim Start (store.initConfig) und
// nach jedem Speichern. Vorher las der Rückblick der Puffer-Aufnahme seinen Wert nur, wenn die Einstellungen offen
// gewesen waren.
import { setLanguage } from "../i18n.js";
import { appState } from "../store.svelte.js";
import { setEnabled } from "../uiSounds.js";

export function wirkungen(werte: Record<string, unknown>): void {
  if (typeof werte.language === "string") setLanguage(werte.language);
  if (typeof werte.ui_click_sounds === "boolean") setEnabled(werte.ui_click_sounds);
  if (typeof werte.hls_rec_lookback_minutes === "number") appState.hlsRecLookbackMinutes = werte.hls_rec_lookback_minutes;
}
