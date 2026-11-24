<script lang="ts">
  // Zeile einer Audiodatei der Kellerwolke: Symbol, Name mit Ordner und Datum, Format, Größe; Hören, Schneiden
  // (Ergebnis als neue Datei daneben), aufs Gerät laden.
  import { t } from "../../lib/i18n.svelte.js";
  import { format, groesse } from "../../lib/aufnahmen/anzeige";
  import type { Wolkendatei } from "../../lib/aufnahmen";

  let { datei, spielt, ordner, laden, onhoeren, onschneiden }: {
    datei: Wolkendatei;
    spielt: boolean;
    ordner: string;
    laden: string;
    onhoeren: () => void;
    onschneiden: () => void;
  } = $props();
</script>

<article class="rh-sender rh-aufnahme" class:spielt data-pfad={datei.pfad}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={onhoeren}>
    <span class="rh-a-dateisymbol"><i class="fa-solid fa-file-audio"></i></span>
    <div class="name"><b>{datei.name}</b>
      <div class="meta"><span>{ordner}</span>{#if datei.geaendert}<span>{new Date(datei.geaendert).toLocaleDateString("de-DE")}</span>{/if}</div></div>
    <div class="rh-a-titelzahl">{format(datei.name)}</div>
    <div class="laenge"></div>
    <div class="laenge rh-a-groesse">{groesse(datei.groesse)}</div>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="rh-aktionen rh-a-aktionen" onclick={(e) => e.stopPropagation()}>
      <button class="rund" type="button" title={t("aufnahmenAnsicht.hoeren")} aria-label={t("aufnahmenAnsicht.hoeren")} onclick={onhoeren}><i class="fa-solid {spielt ? 'fa-volume-high' : 'fa-play'}"></i></button>
      <button class="rund" type="button" title="{t('aufnahmenAnsicht.schneiden')}: {t('aufnahmenAnsicht.wolkeNeben')}" aria-label={t("aufnahmenAnsicht.schneiden")} onclick={onschneiden}><i class="fa-solid fa-scissors"></i></button>
      <a class="rund" href={laden} download title={t("aufnahmenAnsicht.laden")} aria-label={t("aufnahmenAnsicht.laden")}><i class="fa-solid fa-download"></i></a>
    </div>
  </div>
</article>
