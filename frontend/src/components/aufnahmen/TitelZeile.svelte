<script lang="ts">
  // Zeile eines Titels einer Aufnahme: Nummer, Titel (gesperrt markiert), ab wann, Länge, Größe; Hören, Laden,
  // Schneiden, Sperren, Löschen. Löschen fragt vorher und nennt die Größe; der letzte Titel nimmt die Aufnahme mit.
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { groesse, zeit } from "../../lib/aufnahmen/anzeige";
  import type { Titel } from "../../lib/aufnahmen";

  let { titel: x, spielt, gesperrt, letzter, datei, fest = false, imGange = false, laeuft = false, kannSchneiden, kannVerwalten, onhoeren, onschneiden, onsperren, onloeschen }: {
    titel: Titel;
    spielt: boolean;
    gesperrt: boolean;
    /** die Aufnahme wird noch fein geschnitten: hören und laden, ändern erst danach */
    fest?: boolean;
    /** die Aufnahme läuft noch: nur ansehen */
    imGange?: boolean;
    /** das begonnene Stück der laufenden Aufnahme (rote Leuchte, Länge wächst) */
    laeuft?: boolean;
    letzter: boolean;
    datei: string;
    kannSchneiden: boolean;
    kannVerwalten: boolean;
    onhoeren: () => void;
    onschneiden: () => void;
    onsperren: () => void;
    onloeschen: () => Promise<void>;
  } = $props();

  let fragt = $state(false);
  let loescht = $state(false);

  async function loeschen() {
    loescht = true;
    try { await onloeschen(); fragt = false; } finally { loescht = false; }
  }
</script>

<article class="rh-sender rh-aufnahme rh-a-titel" class:spielt class:laeuft data-pfad={x.pfad}>
  <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
  <div class="rh-sender-kern" onclick={() => { if (!imGange) onhoeren(); }}>
    <span class="rh-a-nr">{String(x.nr).padStart(2, "0")}</span>
    <div class="name"><b>{x.titel}</b>
      {#if gesperrt}<div class="meta"><span class="rh-geltung fest" title={t("aufnahmenAnsicht.gesperrtHilfe")}>{t("aufnahmenAnsicht.gesperrt")}</span></div>{/if}</div>
    <div class="rh-a-titelzahl rh-zahl">{zeit(x.start)}</div>
    <div class="laenge">{zeit(x.dauer)}</div>
    <div class="laenge rh-a-groesse">{laeuft ? "" : groesse(x.groesse)}</div>
    <!-- svelte-ignore a11y_click_events_have_key_events, a11y_no_static_element_interactions -->
    <div class="rh-aktionen rh-a-aktionen" onclick={(e) => e.stopPropagation()}>
      {#if !imGange}
      <button class="rund" type="button" title={t("aufnahmenAnsicht.abHier")} aria-label={t("aufnahmenAnsicht.abHier")} onclick={onhoeren}><i class="fa-solid {spielt ? 'fa-volume-high' : 'fa-play'}"></i></button>
      <a class="rund" href={datei} download title={t("aufnahmenAnsicht.laden")} aria-label={t("aufnahmenAnsicht.laden")}><i class="fa-solid fa-download"></i></a>
      {#if kannSchneiden && !fest}<button class="rund" type="button" title={t("aufnahmenAnsicht.schneiden")} aria-label={t("aufnahmenAnsicht.schneiden")} onclick={onschneiden}><i class="fa-solid fa-scissors"></i></button>{/if}
      {#if kannVerwalten && !fest}
        <button class="rund" class:an={gesperrt} type="button" aria-pressed={gesperrt} title={gesperrt ? t("aufnahmenAnsicht.entsperren") : t("aufnahmenAnsicht.sperren")}
                aria-label={gesperrt ? t("aufnahmenAnsicht.entsperren") : t("aufnahmenAnsicht.sperren")} onclick={onsperren}><i class="fa-solid {gesperrt ? 'fa-eye' : 'fa-eye-slash'}"></i></button>
        <button class="rund" type="button" title={t("aufnahmenAnsicht.loeschen")} aria-label={t("aufnahmenAnsicht.loeschen")} onclick={() => (fragt = true)}><i class="fa-solid fa-trash-can rh-loeschen"></i></button>
      {/if}
      {/if}
    </div>
  </div>
  {#if fragt}
    <div class="rh-a-frage">
      <Rueckfrage frage={`${t("aufnahmenAnsicht.titelLoeschenFrage", { name: x.titel, mb: groesse(x.groesse) })}${letzter ? ` ${t("aufnahmenAnsicht.letzterTitel")}` : ""}`}
                  knopf={t("aufnahmenAnsicht.loeschen")} beschaeftigt={loescht} onabbrechen={() => (fragt = false)} onja={() => void loeschen()} />
    </div>
  {/if}
</article>
