<script lang="ts">
  // Knopf "Geräte" im Kopf (RAD-18, Wahl C): zeigt, wie viele andere Geräte offen sind, und blinkt ruhig, solange auf
  // einem davon etwas spielt. Ein Klick öffnet darunter die Geräteliste des Appkerns mit Holen und Dorthin.
  import { Geraeteliste } from "appkern-oberflaeche";
  import { t } from "../lib/i18n.svelte.js";
  import { appState } from "../lib/store.svelte.js";
  import { geraete, geraeteTexte, geraeteZeile } from "../spieler/geraete.svelte";

  let offen = $state(false);
  let rahmen = $state<HTMLElement>();
  const zahl = $derived(geraete.andere.length);
  const spielen = $derived(geraete.spielenWoanders.length);
  const hilfe = $derived(spielen ? t("geraete.knopfSpielt", { n: spielen }) : t("geraete.knopf"));

  $effect(() => {
    if (!offen) return;
    const weg = (e: Event) => { if (!rahmen?.contains(e.target as Node)) offen = false; };
    const taste = (e: KeyboardEvent) => { if (e.key === "Escape") offen = false; };
    document.addEventListener("pointerdown", weg);
    document.addEventListener("keydown", taste);
    return () => { document.removeEventListener("pointerdown", weg); document.removeEventListener("keydown", taste); };
  });
</script>

<div class="rh-geraete" bind:this={rahmen}>
  <button class="rund rh-geraete-knopf" class:blinkt={spielen > 0} type="button" title={hilfe} aria-label={hilfe}
          aria-expanded={offen} onclick={() => (offen = !offen)}>
    <i class="fa-solid fa-tower-broadcast"></i>
    {#if zahl}<span class="rh-geraete-zahl">{zahl}</span>{/if}
  </button>
  {#if offen}
    <div class="rh-geraete-feld">
      <Geraeteliste uebergabe={geraete} zeile={geraeteZeile} texte={geraeteTexte()}
                    hierSpielt={appState.isPlaying || appState.isPaused} onzu={() => (offen = false)} />
    </div>
  {/if}
</div>
