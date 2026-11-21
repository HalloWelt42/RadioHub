// Sprache der Oberfläche je Gerät, wo kein Server sie für alle Geräte hält (Basic, RAD-28): gemerkt im Browser, ohne
// eigene Wahl die des Browsers, sofern RadioHub sie vollständig kann, sonst Deutsch. Angeboten werden nur vollständig
// übersetzte Sprachen; die übrigen kämen sonst halb englisch daher.
import { availableLanguages, setLanguage } from "./i18n.js";

const SCHLUESSEL = "radiohub_sprache";

export const SPRACHANGEBOT = availableLanguages.filter((l) => (l as { vollstaendig?: boolean }).vollstaendig);
const bekannt = (code: string | null | undefined): code is string => !!code && SPRACHANGEBOT.some((l) => l.code === code);

export function geraetesprache(): string {
  try {
    const gemerkt = localStorage.getItem(SCHLUESSEL);
    if (bekannt(gemerkt)) return gemerkt;
  } catch {
    // ohne Speicher des Browsers gilt die des Browsers
  }
  const browser = navigator.language?.slice(0, 2).toLowerCase();
  return bekannt(browser) ? browser : "de";
}

export function geraetespracheSetzen(code: string): void {
  if (!bekannt(code)) return;
  try {
    localStorage.setItem(SCHLUESSEL, code);
  } catch {
    // gilt dann nur bis zum Neuladen
  }
  void setLanguage(code);
}

export function geraetespracheAnwenden(): void {
  void setLanguage(geraetesprache());
}
