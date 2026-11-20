<script lang="ts">
  // Langer Fließtext, auf drei Zeilen gekürzt; der Rest klappt auf und zu (RAD-27, Nutzer 21.11.2026: "große texte
  // kürzen auf 3 zeilen und den rest ein und ausklappbar machen"). Der Knopf erscheint nur, wenn der Text wirklich
  // länger ist; gemessen wird am gekürzten Absatz, auch wenn sich die Breite oder die Schriftgröße ändert.
  import { t } from "../../lib/i18n.svelte.js";

  let { text, zeilen = 3, klasse = "" }: { text: string; zeilen?: number; klasse?: string } = $props();

  let offen = $state(false);
  let laenger = $state(false);
  let absatz: HTMLParagraphElement | undefined = $state();

  $effect(() => {
    const el = absatz;
    void text;
    if (!el || offen) return;
    const messen = () => { laenger = el.scrollHeight > el.clientHeight + 1; };
    messen();
    const beobachter = new ResizeObserver(messen);
    beobachter.observe(el);
    return () => beobachter.disconnect();
  });
</script>

<div class="rh-langtext {klasse}">
  <p bind:this={absatz} class:gekuerzt={!offen} style:--rh-zeilen={zeilen}>{text}</p>
  {#if laenger || offen}
    <button class="knopf still rh-mehr" type="button" aria-expanded={offen} onclick={() => (offen = !offen)}>
      <i class="fa-solid {offen ? 'fa-chevron-up' : 'fa-chevron-down'}"></i>{offen ? t("radio.langtextWeniger") : t("radio.langtextMehr")}</button>
  {/if}
</div>
