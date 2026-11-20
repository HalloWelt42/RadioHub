<script lang="ts">
  // Wurzel der Webversion (RAD-4, Entscheidung 27): nur Radio, ohne Backend und ohne Anmeldung. Am Rechner Kopf mit
  // Radio und Einstellungen, die Radio-Ansicht oder Einstellungen > Radio und die Kanzel; am Telefon die Telefonansicht
  // mit Radio und Wecker (Weckansicht quer, Wecker im Speicher des Browsers, RAD-15). Dieselben Bausteine wie die volle App; was fehlt, blenden sie über die Fähigkeiten der Senderquelle
  // und des Wiedergabewegs selbst aus.
  import Kanzel from "../spieler/Kanzel.svelte";
  import RadioAnsicht from "../components/radio/RadioAnsicht.svelte";
  import SetupRadio from "../components/setup/SetupRadio.svelte";
  import Telefon from "../components/telefon/Telefon.svelte";
  import Kopf from "./Kopf.svelte";
  import Meldung from "./Meldung.svelte";
  import { appState, actions } from "../lib/store.svelte.js";
  import * as router from "../lib/router.js";
  import { geraet } from "../lib/geraet.svelte.js";
  import { tasteDerApp } from "./tastatur";

  const BEREICHE = ["radio", "settings"] as const;
  const TELEFON = { podcasts: false, wecker: true, backend: false };

  // Adresse und Bereich (Zurück und Vor im Browser); es gibt Radio, Einstellungen > Radio und am Telefon den Wecker
  $effect(() => {
    const anfang = router.init((info: { tab: string; segments: string[] }) => {
      appState.activeTab = info.tab;
      appState.routeSegments = info.segments;
    });
    appState.activeTab = anfang.tab;
    appState.routeSegments = anfang.segments;
  });
  $effect(() => {
    const tab = appState.activeTab as string;
    const wecker = tab === "wecker" && geraet.telefon && TELEFON.wecker;
    if (tab !== "radio" && tab !== "settings" && !wecker) actions.navigateTo("/radio", { replace: true });
    else if (tab === "settings" && (appState.routeSegments as string[])[0] !== "radio") actions.navigateTo("/einstellungen/radio/regeln", { replace: true });
  });

  function taste(e: KeyboardEvent) {
    if (!geraet.telefon) tasteDerApp(e, BEREICHE);
  }
</script>

<svelte:window onkeydown={taste} />

{#if geraet.telefon}
  <Telefon angebot={TELEFON} />
{:else}
  <div class="rh-app">
    <Kopf bereiche={[...BEREICHE]} ausgabe="basic" />
    <main class="rh-mitte">
      {#if appState.activeTab === "settings"}
        <div class="rh-web-einst"><SetupRadio /></div>
      {:else}
        <RadioAnsicht />
      {/if}
    </main>
    <Kanzel />
  </div>
  <Meldung />
{/if}

<style>
  /* ohne Leiste der Bereiche (nur Radio): Pfad, Reiter und Karten als eine Spalte mittig, so breit wie die Karten
     (Nutzer 20.11.2026: "einstellungenleiste ist völlig dezentral") */
  .rh-web-einst { min-height: 0; min-width: 0; display: flex; justify-content: center; padding: 14px var(--rh-rand) 0; }
  .rh-web-einst :global(.rh-einst-haupt) { flex: 0 1 1280px; }
</style>
