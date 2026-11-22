<script lang="ts">
  // Eine Ausschlussregel (Entwurf regeln.html): Leuchte an oder aus, Art, Titel und Erklärung, betroffene Sender und davon
  // Favoriten, Schalter, Entfernen. Entfernen fragt erst mit der Folgenvorschau (so viele Sender werden wieder sichtbar,
  // Beispiele) über die Rückfrage der Schale (Vorgabe 9).
  import { Rueckfrage } from "appkern-oberflaeche";
  import Schalter from "../../bausteine/Schalter.svelte";
  import { t } from "../../../lib/i18n.svelte.js";
  import { actions } from "../../../lib/store.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { REGEL_SYMBOL, zahl } from "../../../lib/radio/anzeige";
  import type { Regel, RegelFolgen } from "../../../lib/radio/typen";

  let { regel, neu = false, onschalten, onentfernt }: {
    regel: Regel;
    neu?: boolean;
    onschalten: (r: Regel) => void;
    onentfernt: (r: Regel, wiederSichtbar: number) => void;
  } = $props();

  let folgen = $state<RegelFolgen | null>(null);
  let fragt = $state(false);
  let arbeitet = $state(false);
  let fehler = $state("");

  async function fragen() {
    fehler = "";
    fragt = true;
    folgen = null;
    try {
      folgen = await senderquelle.folgen(regel.id);
    } catch (f) {
      fehler = (f as Error).message;
    }
  }

  async function entfernen() {
    arbeitet = true;
    try {
      const a = await senderquelle.entfernen(regel.id);
      fragt = false;
      onentfernt(regel, a.wieder_sichtbar);
    } catch (f) {
      fehler = (f as Error).message;
    } finally {
      arbeitet = false;
    }
  }

  const hinweis = $derived(!folgen ? t("radio.laedt")
    : (regel.an ? t("radio.einst.folgenSichtbar", { n: zahl(folgen.wieder_sichtbar) }) : t("radio.einst.folgenAus"))
      + (folgen.beispiele.length ? ` ${t("radio.einst.etwa", { namen: folgen.beispiele.slice(0, 3).map((b) => b.name.trim()).join(", ") })}` : "")
      + ` ${t("radio.einst.folgenNeue")}`);
</script>

<div class="rh-regel" class:aus={!regel.an} class:neu>
  <span class="rh-regel-art" title={t(`radio.einst.art.${regel.art}`)}><i class="fa-solid {REGEL_SYMBOL[regel.art]}"></i></span>
  <span class="rh-regel-text"><b>{regel.titel}</b><span>{t(`radio.einst.art.${regel.art}`)}: {regel.erklaerung}{#if neu}{` · ${t("radio.einst.geradeAngelegt")}`}{/if}</span></span>
  <span class="rh-regel-zahl"><b>{zahl(regel.betroffen)}</b>{t("radio.einst.senderFavoriten", { n: zahl(regel.favoriten) })}</span>
  <Schalter an={regel.an} text={regel.an ? t("einstellungen.an") : t("einstellungen.aus")}
            hilfe={regel.an ? t("radio.einst.ausschaltenHilfe", { n: zahl(regel.nur_diese) }) : t("radio.einst.einschalten")}
            onwechsel={() => onschalten(regel)} />
  {#if regel.art === "einzeln"}
    <!-- einzeln ausgeblendete Sender sind keine Regel zum Entfernen: freigegeben wird je Sender (RAD-28) -->
    <a class="knopf" href="/einstellungen/radio/ausgeblendet" title={t("radio.einst.einzelnHilfe")}
       onclick={(e) => { e.preventDefault(); actions.navigateTo("/einstellungen/radio/ausgeblendet"); }}><i class="fa-solid fa-eye"></i>{t("radio.einst.einzelnFreigeben")}</a>
  {:else}
    <button class="knopf gefahr" type="button" onclick={fragen} disabled={fragt}><i class="fa-solid fa-trash"></i>{t("radio.entfernen")}</button>
  {/if}
  {#if fragt}
    <Rueckfrage frage={t("radio.einst.entfernenFrage")} {hinweis} knopf={t("radio.einst.endgueltigEntfernen")}
                beschaeftigt={arbeitet || !folgen} onabbrechen={() => (fragt = false)} onja={entfernen} />
  {/if}
  {#if fehler}<p class="rh-still">{fehler}</p>{/if}
</div>
