<script lang="ts">
  // Kopf der laufenden Aufnahme (Entwurf aufnahmen.html): Sender mit blinkendem Licht, wie (direkt oder aus dem Puffer
  // mit Rückblick) und wohin, die live erkannten Titel (gesperrte blass), Lücken in der Entwickleransicht, die Uhr als
  // Segmentanzeige und "Aufnahme beenden". Die Daten liefert der Abspielmotor (appState), nicht die Liste.
  import { t } from "../../lib/i18n.svelte.js";
  import { appState, actions } from "../../lib/store.svelte.js";
  import { zeit } from "../../lib/aufnahmen/anzeige";
  import type { Aufnahme } from "../../lib/aufnahmen";
  import Logo from "../radio/Logo.svelte";

  let { aufnahme: a, ziel }: { aufnahme: Aufnahme; ziel: string } = $props();

  const titel = $derived((appState.recordingIcyEntries as { title: string; t: number; ignored?: boolean }[]) ?? []);
  const luecken = $derived(((appState.recordingEvents as { type: string }[]) ?? []).filter((e) => e.type === "gap_start").length);
  const uhr = $derived(zeit(appState.recordingElapsed as number).padStart(7, "0"));
  const start = $derived(new Date(a.beginn).getTime());
  const wann = (ms: number) => new Date(start + ms).toLocaleTimeString("de-DE");
</script>

<section class="rh-abo-kopf rh-a-kopf rh-a-laeuft">
  <Logo uuid={a.senderUuid} name={a.sender} logo="" />
  <div class="rh-abo-text">
    <h2>{t("aufnahmenAnsicht.laeuft", { sender: a.sender })}</h2>
    <p class="rh-still">{t("aufnahmenAnsicht.laeuftSeit", { zeit: new Date(a.beginn).toLocaleTimeString("de-DE") })} ·
      {appState.recordingVorlaufS >= 60 ? t("aufnahmenAnsicht.rueckblick", { n: Math.round(appState.recordingVorlaufS / 60) }) : t("aufnahmenAnsicht.direkt")} ·
      {t("aufnahmenAnsicht.nach", { name: ziel })}
      {#if appState.devMode && luecken} · <span class="rh-a-warn"><i class="fa-solid fa-triangle-exclamation"></i>{t("aufnahmenAnsicht.luecken", { n: luecken })}</span>{/if}</p>
    {#if titel.length}
      <ol class="rh-live-titel">
        {#each titel as x, i (i)}
          <li class:gesperrt={x.ignored}><span class="rh-zahl">{wann(x.t)}</span>{x.title}{#if x.ignored}<span class="rh-geltung fest" title={t("aufnahmenAnsicht.gesperrtHilfe")}>{t("aufnahmenAnsicht.gesperrt")}</span>{/if}</li>
        {/each}
      </ol>
    {:else}
      <p class="rh-still">{t("aufnahmenAnsicht.nochKeineTitel")}</p>
    {/if}
  </div>
  <div class="ak-geraet rh-a-uhr" data-bauform="inspektor">
    <span class="ak-schraube lo" style="--dreh:20deg"></span><span class="ak-schraube ro" style="--dreh:-30deg"></span>
    <ak-segmente art="7" stellen="7" farbe="rot" text={uhr}></ak-segmente><span class="ak-etikett">{t("aufnahmenAnsicht.uhr")}</span>
  </div>
  <div class="rh-detail-knoepfe rh-abo-knoepfe">
    <button class="knopf gefahr" type="button" onclick={() => void actions.stopRecording()}><i class="fa-solid fa-stop"></i>{t("aufnahmenAnsicht.beenden")}</button>
    <span class="rh-still"><i class="fa-solid fa-lock"></i> {t("aufnahmenAnsicht.gesperrtWaehrend")}</span>
  </div>
</section>
