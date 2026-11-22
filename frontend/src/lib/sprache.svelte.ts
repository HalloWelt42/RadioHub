// Sprachwahl der Oberfläche an einer Stelle (RAD-71, RAD-90): welche Sprachen vollständig übersetzt sind, welche gilt
// und das Wählen (sofort gespeichert: mit Server für alle Geräte, in Basic im Browser). Genutzt vom Kopf am Rechner
// (Flagge) und von den Einstellungen am Telefon.
import { currentLanguage, onLanguageChange, t } from "./i18n.svelte.js";
import { geraetespracheSetzen, SPRACHANGEBOT } from "./sprache";
import { EINSTELLUNGEN } from "$ziel/einstellungen";
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


export async function spracheWaehlen(code: string): Promise<void> {
  if (code === stand.code) return;
  // ohne Server (Basic) gilt die Sprache dieses Geräts und bleibt im Browser (RAD-99: vorher nach dem Neuladen wieder
  // die alte); mit Server für alle Geräte
  if (!EINSTELLUNGEN.server) return geraetespracheSetzen(code);
  try {
    await server.sofortSpeichern("language", code);
  } catch (f) {
    actions.showToast((f as Error).message || t("common.fehler"), "error");
  }
}
