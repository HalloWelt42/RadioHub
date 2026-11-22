<script lang="ts">
  // Zeile einer Aufnahme (Entwurf aufnahmen.html): Licht (blau spielt, rot nimmt auf, bernstein abgebrochen), Logo,
  // Sender mit Datum und Ordner, Titelzahl, Länge, Größe; Hören, Schneiden, Titel zeigen.
  import { t } from "../../lib/i18n.svelte.js";
  import { datum, groesse, zeit } from "../../lib/aufnahmen/anzeige";
  import type { Aufnahme } from "../../lib/aufnahmen";
  import Logo from "../radio/Logo.svelte";

  let { aufnahme: a, ordner, spielt, laufendeSekunden, kannSchneiden, onwaehlen, onhoeren, onschneiden }: {
    aufnahme: Aufnahme;
    ordner: string;
    spielt: boolean;
    /** nur während sie aufnimmt: die laufende Zeit */
    laufendeSekunden: number | null;
    kannSchneiden: boolean;
    onwaehlen: () => void;
    onhoeren: () => void;
    onschneiden: () => void;
  } = $props();

  const laeuft = $derived(a.status === "laeuft");
  const warn = $derived(a.status === "abgebrochen" || a.status === "unterbrochen");
</script>

<article class="rh-sender rh-aufnahme" class:spielt class:laeuft>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={onwaehlen}>
    <Logo uuid={a.senderUuid} name={a.sender} logo="" />
    <div class="name"><b>{a.sender}</b>
      <div class="meta"><span>{datum(a.beginn)}</span><span>{ordner}</span>
        {#if warn}<span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>{t(`aufnahmenAnsicht.${a.status}`)}</span>{/if}</div></div>
    <div class="rh-a-titelzahl">{a.titelzahl}</div>
    <div class="laenge">{zeit(laufendeSekunden ?? a.dauer)}</div>
    <div class="laenge rh-a-groesse">{a.groesse ? groesse(a.groesse) : "-"}</div>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="rh-aktionen rh-a-aktionen" onclick={(e) => e.stopPropagation()}>
      {#if !laeuft}
        <button class="rund" type="button" title={t("aufnahmenAnsicht.hoeren")} aria-label={t("aufnahmenAnsicht.hoeren")} onclick={onhoeren}><i class="fa-solid fa-play"></i></button>
        {#if kannSchneiden}<button class="rund" type="button" title={t("aufnahmenAnsicht.schneiden")} aria-label={t("aufnahmenAnsicht.schneiden")} onclick={onschneiden}><i class="fa-solid fa-scissors"></i></button>{/if}
      {/if}
      <button class="rund" type="button" title={t("aufnahmenAnsicht.titelZeigen")} aria-label={t("aufnahmenAnsicht.titelZeigen")} onclick={onwaehlen}><i class="fa-solid fa-chevron-right"></i></button>
    </div>
  </div>
</article>
