// Sprachwahl der Oberfläche an einer Stelle (RAD-71, RAD-90): welche Sprachen vollständig übersetzt sind, welche gilt,
// welche als nächste kommt und das Wählen (sofort gespeichert, gilt für alle Geräte). Genutzt vom Kopf am Rechner
// (Flagge) und von den Einstellungen am Telefon.
import { currentLanguage, onLanguageChange, t } from "./i18n.svelte.js";
import { SPRACHANGEBOT } from "./sprache";
import { server } from "./einstellungen";
import { actions } from "./store.svelte.js";

export interface Sprache { code: string; label: string }

/** die vollständig übersetzten Sprachen, aus lib/sprache.ts (eine Liste für Gerät und Server) */
export const SPRACHEN = SPRACHANGEBOT as Sprache[];

const stand = $state({ code: currentLanguage() as string });
onLanguageChange((code: string) => (stand.code = code));

export function spracheJetzt(): Sprache {
  return SPRACHEN.find((s) => s.code === stand.code) ?? SPRACHEN[0];
}

export function spracheDanach(): Sprache {
  return SPRACHEN[(SPRACHEN.indexOf(spracheJetzt()) + 1) % SPRACHEN.length];
}

export async function spracheWaehlen(code: string): Promise<void> {
  if (code === stand.code) return;
  try {
    await server.sofortSpeichern("language", code);
  } catch (f) {
    actions.showToast((f as Error).message || t("common.fehler"), "error");
  }
}
