// Von einer Aufnahme zu ihrem Sender (RAD-145): er spielt, und die Aufnahme ist das Ziel: was man dort aufnimmt oder aus dem Puffer
// sichert, kommt hinten an sie. Das Ziel gilt, solange dieser Sender läuft, bis man es löst (Hinweis in schale/Meldung).
import { tick } from "svelte";
import { actions, appState } from "../lib/store.svelte.js";
import { t } from "../lib/i18n.svelte.js";
import { geraet } from "../lib/geraet.svelte.js";
import { filterzustand, senderquelle } from "../lib/radio";
import type { Aufnahme } from "../lib/aufnahmen";

export async function zumSender(a: Aufnahme): Promise<void> {
  const spielt = (appState.currentStation as { uuid?: string } | null)?.uuid === a.senderUuid;
  if (appState.isRecording && !spielt) return actions.showToast(t("aufnahmenAnsicht.erstBeenden"), "error");
  const e = await senderquelle.sender(a.senderUuid).catch(() => null);
  if (!e) return actions.showToast(t("aufnahmenAnsicht.senderWeg"), "error");
  appState.aufnahmeziel = { id: a.id, sender: a.sender, senderUuid: a.senderUuid, beginn: a.beginn };
  actions.navigateTo("/radio");
  if (!geraet.telefon) {
    await tick();
    filterzustand.oeffnen(a.senderUuid);
  }
  if (!spielt || !appState.isPlaying) await actions.playStationFromList(await senderquelle.wiedergabe(e));
}

export function zielLoesen(): void {
  appState.aufnahmeziel = null;
}
