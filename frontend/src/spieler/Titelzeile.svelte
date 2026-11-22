<script lang="ts">
  // Titelzeile unter dem Balken des Zeitversatzes (RAD-46, Entwurf puffer.html Zustand 1): der Titel an der Stelle, die
  // man hört, mit Vorheriger und Nächster Titel und dem Knopf zur Großansicht des Puffers (/radio/puffer).
  import { t } from "../lib/i18n.svelte.js";
  import * as sfx from "../lib/uiSounds.js";
  import { actions } from "../lib/store.svelte.js";
  import { formatTimeShort } from "../lib/formatters.js";
  import { naechster, vorheriger } from "../lib/radio/abschnitte";
  import { puffer } from "./puffer.svelte";

  let { gesperrt = false }: { gesperrt?: boolean } = $props();

  const a = $derived(puffer.laufend);
  const stelle = $derived(puffer.stelle);
  const kannZurueck = $derived(stelle !== null && vorheriger(puffer.abschnitte, stelle) !== null);
  const kannVor = $derived(stelle !== null && naechster(puffer.abschnitte, stelle) !== null);
  const name = (x: NonNullable<typeof a>) => (x.art === "werbung" ? t("puffer.werbung") : x.art === "einschub" ? t("puffer.einschub") : x.titel);
</script>

<div class="rh-titelzeile">
  <button class="knopf" type="button" title={t("puffer.titelZurueckHilfe")} aria-label={t("puffer.titelZurueckHilfe")} disabled={gesperrt || !kannZurueck}
    onmouseenter={sfx.hover} onclick={() => { puffer.vorher(); sfx.click(); }}><i class="fa-solid fa-backward-step"></i>{t("puffer.titelZurueck")}</button>
  <span class="rh-titelzeile-jetzt">
    {#if a && stelle !== null}
      <b title={a.titel}>{name(a)}</b>
      <span class="rh-zahl">{t("puffer.vonLaenge", { a: formatTimeShort(Math.max(0, stelle - a.von)), b: formatTimeShort(a.bis - a.von) })}{a.laufend ? ` · ${t("puffer.laeuft")}` : ""}</span>
    {:else}
      <span class="rh-still">{t("puffer.ohneTitel")}</span>
    {/if}
  </span>
  <button class="knopf" type="button" title={t("puffer.titelVorHilfe")} aria-label={t("puffer.titelVorHilfe")} disabled={gesperrt || !kannVor}
    onmouseenter={sfx.hover} onclick={() => { puffer.weiter(); sfx.click(); }}>{t("puffer.titelVor")}<i class="fa-solid fa-forward-step"></i></button>
  <button class="knopf" type="button" title={t("puffer.pufferHilfe")} onmouseenter={sfx.hover}
    onclick={() => { actions.navigateTo("/radio/puffer"); sfx.click(); }}><i class="fa-solid fa-list-ul"></i>{t("puffer.puffer")}</button>
</div>
