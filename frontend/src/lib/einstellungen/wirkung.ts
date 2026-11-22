// Wirkung der Server-Einstellungen im laufenden Programm (RAD-11), an einer Stelle: beim Start (store.initConfig) und
// nach jedem Speichern. Vorher las der Rückblick der Puffer-Aufnahme seinen Wert nur, wenn die Einstellungen offen
// gewesen waren.
import { setLanguage } from "../i18n.js";

export function wirkungen(werte: Record<string, unknown>): void {
  if (typeof werte.language === "string") setLanguage(werte.language);
}
