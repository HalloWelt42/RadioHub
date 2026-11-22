<script lang="ts">
  // Kopf eines Abos am Telefon (Entwurf telefon-podcasts.html, Zustand 3): Bild, Beschreibung, Zahlen; drei Schalter
  // (Neue speichern, Werbung überspringen, Neue Folgen prüfen) gleich breit mit Symbol, Aktualisieren und Abbestellen mit
  // Rückfrage gleich breit (RAD-101); darunter die Sortierung der Folgen.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { textAus } from "../../../lib/podcasts/anzeige";
  import type { Abo, Podcastsortierung } from "../../../lib/podcasts";
  import AboBild from "../../podcast/AboBild.svelte";
  import Langtext from "../../radio/Langtext.svelte";
  import Schalter from "../../bausteine/Schalter.svelte";

  let { abo, sortierung, arbeitet, kannSpeichern, kannWerbung, onaktualisieren, onauto, onabbestellen, onsortieren, onwerbung }: {
    abo: Abo;
    sortierung: Podcastsortierung;
    arbeitet: boolean;
    kannSpeichern: boolean;
    /** Werbestellen gibt es nur in der vollen App (RAD-102) */
    kannWerbung: boolean;
    onaktualisieren: () => void;
    onauto: (an: boolean) => void;
    onabbestellen: () => Promise<void>;
    onsortieren: (s: Podcastsortierung) => void;
    onwerbung: (teil: { ueberspringen?: boolean; pruefen?: boolean }) => void;
  } = $props();

  let fragt = $state(false);
  const SORT: Podcastsortierung[] = ["neu", "alt", "laenge"];
  const SORT_SYMBOL: Record<Podcastsortierung, string> = { neu: "fa-arrow-down-wide-short", alt: "fa-arrow-up-wide-short", titel: "fa-arrow-down-a-z", laenge: "fa-hourglass-half" };
</script>

<section class="tp-abokopf">
  <AboBild {abo} gross />
  <div>
    {#if abo.beschreibung}<Langtext text={textAus(abo.beschreibung)} klasse="tp-beschreibung" />{/if}
    <div class="tf-meta"><span><b>{abo.folgen}</b> {t("podcastAnsicht.folgen")}</span><span><b>{abo.ungehoert}</b> {t("podcastAnsicht.ungehoert")}</span>
      {#if kannSpeichern}<span title={t("podcastAnsicht.telefon.gespeichertHilfe")}><i class="fa-solid fa-cloud"></i> <b>{abo.gespeichert}/{abo.folgen}</b></span>{/if}</div>
  </div>
  <!-- Einstellungen als drei gleich breite Schalter mit Symbol und kurzem Wort, darunter die beiden Aktionen gleich
       breit (RAD-101, Wahl A); die ausführliche Erklärung steht im Hinweis -->
  {#if kannSpeichern || kannWerbung}
  <div class="tp-schalter">
    {#if kannSpeichern}<Schalter an={abo.autoLaden} symbol="fa-cloud-arrow-down" text={t("podcastAnsicht.telefon.kurzSpeichern")}
                                hilfe={t("podcastAnsicht.neueSpeichernHilfe")} onwechsel={onauto} />{/if}
    {#if kannWerbung}
    <Schalter an={abo.werbungUeberspringen} farbe="bernstein" symbol="fa-ban" text={t("podcastAnsicht.telefon.kurzWerbung")}
              hilfe={t("podcastAnsicht.werbung.aboUeberspringenHilfe")} onwechsel={(an) => onwerbung({ ueberspringen: an })} />
    <Schalter an={abo.werbungPruefen} farbe="bernstein" symbol="fa-magnifying-glass" text={t("podcastAnsicht.telefon.kurzPruefen")}
              hilfe={t("podcastAnsicht.werbung.aboPruefenHilfe")} onwechsel={(an) => onwerbung({ pruefen: an })} />
    {/if}
  </div>
  {/if}
  <div class="tp-abo-aktionen">
    <button class="knopf" type="button" disabled={arbeitet} onclick={onaktualisieren}><i class="fa-solid fa-rotate" class:fa-spin={arbeitet}></i>{t("podcastAnsicht.aktualisieren")}</button>
    <button class="knopf" type="button" onclick={() => (fragt = true)}><i class="fa-solid fa-trash-can rh-loeschen"></i>{t("podcastAnsicht.abbestellen")}</button>
  </div>
  {#if fragt}
    <div class="tp-frage"><Rueckfrage frage={t("podcastAnsicht.telefon.abbestellenFrage", { name: abo.titel })} hinweis={t("podcastAnsicht.telefon.abbestellenHinweis")}
                knopf={t("podcastAnsicht.abbestellen")} onabbrechen={() => (fragt = false)} onja={() => { fragt = false; void onabbestellen(); }} /></div>
  {/if}
</section>
<!-- Sortierung als gleich breiter Umschalter über die volle Breite, wie Hell, Dunkel und System (RAD-101); der Name
     steht nur noch für Vorleser da -->
<div class="rh-wahl tp-sort"><div class="segment" role="group" aria-label={t("podcastAnsicht.telefon.sortierung")}>
  {#each SORT as s (s)}<button type="button" class:aktiv={sortierung === s} aria-pressed={sortierung === s} onclick={() => onsortieren(s)}><i
    class="fa-solid {SORT_SYMBOL[s]}" aria-hidden="true"></i>{t(`podcastAnsicht.telefon.sort_${s}`)}</button>{/each}
</div></div>

