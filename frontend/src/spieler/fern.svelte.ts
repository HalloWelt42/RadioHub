// Steuermodus (RAD-96): dieses Gerät steuert ein anderes desselben Kontos. Gewählt wird es am Umschalter; solange es gewählt
// ist, gehen Tasten und Lautstärke dorthin, und was man in einer Liste antippt, spielt dort. Ist das Gerät gerade nicht
// erreichbar, bleibt es gewählt und die Tasten ruhen, damit nie aus Versehen hier etwas losgeht. Der Wecker und die
// Medientasten dieses Geräts gehören immer diesem Gerät (sie gehen nicht über diese Wege).
import { actions, umleitungSetzen } from "../lib/store.svelte.js";
import { t } from "../lib/i18n.svelte.js";
import { geraete } from "./geraete.svelte";
import { kompakt, type Fernaktion, type RadioPaket, type RadioZustand } from "./geraetepaket";

/** so oft geht die Lautstärke beim Ziehen höchstens hinaus */
const LAUTSTAERKE_MS = 120;

class Fernsteuerung {
  /** das gesteuerte Gerät (Fenster); null: dieses Gerät */
  zielId = $state<string | null>(null);
  private gemerkterName = $state("");
  ziel = $derived(geraete.andere.find((g) => g.id === this.zielId) ?? null);
  aktiv = $derived(this.zielId !== null);
  erreichbar = $derived(this.ziel !== null);
  name = $derived(this.ziel?.name ?? this.gemerkterName);
  zustand = $derived<RadioZustand | null>(this.ziel?.zustand ?? null);
  private wartend: number | null = null;
  private uhr: ReturnType<typeof setTimeout> | null = null;

  waehlen(id: string | null): void {
    this.zielId = id;
    this.gemerkterName = geraete.andere.find((g) => g.id === id)?.name ?? "";
  }

  befehl(aktion: Fernaktion, wert: number | null = null): void {
    if (this.ziel) geraete.befehlen(this.ziel.id, aktion, wert);
  }

  /** beim Ziehen gebündelt, der letzte Wert kommt immer an */
  lautstaerke(wert: number): void {
    this.wartend = wert;
    if (this.uhr !== null) return;
    this.lautstaerkeSenden();
    this.uhr = setTimeout(() => { this.uhr = null; this.lautstaerkeSenden(); }, LAUTSTAERKE_MS);
  }

  private lautstaerkeSenden(): void {
    if (this.wartend === null) return;
    this.befehl("lautstaerke", this.wartend);
    this.wartend = null;
  }

  /** Antippen in einer Liste: dort spielen statt hier; liefert false, wenn hier gespielt werden soll */
  uebernimmt(paket: RadioPaket): boolean {
    if (!this.aktiv) return false;
    if (!this.ziel) {
      actions.showToast(t("telefon.fernWeg", { name: this.name }), "error");
      return true;
    }
    geraete.geben(this.ziel.id, paket);
    actions.showToast(t("telefon.fernGestartet", { name: this.name }), "success");
    return true;
  }
}

export const fern = new Fernsteuerung();

/** die Tasten des Spielers für das gesteuerte Gerät (dieselben Namen wie die Steuerung des Telefons) */
export const fernsteuerung = {
  umschalten: () => fern.befehl("umschalten"),
  stoppen: () => fern.befehl("stopp"),
  naechster: () => fern.befehl("weiter"),
  voriger: () => fern.befehl("vorher"),
  vor: (s: number) => fern.befehl("vor", s),
  zurueck: (s: number) => fern.befehl("zurueck", s),
};

umleitungSetzen((art: RadioPaket["art"], quelle: unknown, podcast: unknown = null, stelle = 0) => {
  if (!fern.aktiv) return false;
  if (art === "sender") return fern.uebernimmt({ art, sender: kompakt(quelle), stelle: 0 });
  if (art === "folge") return fern.uebernimmt({ art, folge: kompakt(quelle), podcast: kompakt(podcast), stelle: stelle || Number((quelle as { resume_position?: number }).resume_position) || 0 });
  return fern.uebernimmt({ art, aufnahme: kompakt(quelle), stelle });
});
