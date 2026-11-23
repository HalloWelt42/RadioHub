// Das Mitlesen eines Senders an- und ausschalten (RAD-129, RAD-133), ein Weg für den Steckbrief am Rechner und für Liste und Spieler
// am Telefon: es braucht den laufenden Sender im Zeitversatz, spielt er nicht, startet ihn die Ansicht.
import { actions } from "../lib/store.svelte.js";
import { senderquelle } from "../lib/radio";
import { mitlesen } from "../lib/radio/mitlesen.svelte";
import type { SpracheKurz } from "../lib/radio/typen";
import { puffer } from "./puffer.svelte";

interface Sender { uuid: string; sprachen: SpracheKurz[] }

class Mitlesetaste {
  /** am Telefon steht das Mitlesefeld an der Stelle der Liste; geschlossen läuft das Mitlesen weiter */
  offen = $state(false);

  /** einmal je Ansicht: fragt, ob das Mitlesen eingerichtet ist */
  pruefen(): void {
    if (senderquelle.faehig.mitlesen) void mitlesen.pruefen();
  }

  get kann(): boolean {
    return senderquelle.faehig.mitlesen && mitlesen.eingerichtet === true;
  }

  /** `starten` spielt den Sender; gerufen nur, wenn er noch nicht im Zeitversatz läuft */
  schalten(e: Sender, an: boolean, spielt: boolean, starten: () => void): void {
    if (!an) return void mitlesen.beenden();
    if (!spielt || !puffer.aktiv) starten();
    mitlesen.starten(e.uuid, e.sprachen).catch((f: Error) => actions.showToast(f.message, "error"));
  }

  /** nach einem Ende fortsetzen, der gelesene Text bleibt */
  async weiter(e: Sender, spielt: boolean, starten: () => void): Promise<void> {
    if (!spielt || !puffer.aktiv) starten();
    await mitlesen.starten(e.uuid, e.sprachen, true);
  }
}

export const mitlesetaste = new Mitlesetaste();
