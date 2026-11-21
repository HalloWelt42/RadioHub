<script lang="ts">
  // Wurzel der Webversion (RAD-4, Entscheidung 27): nur Radio, ohne Backend und ohne Anmeldung. Am Rechner Kopf mit
  // Radio und Einstellungen, die Radio-Ansicht oder die Einstellungen und die Kanzel; am Telefon die Telefonansicht
  // mit Radio und Wecker (Weckansicht quer, Wecker im Speicher des Browsers, RAD-15). Dieselben Bausteine wie die volle App; was fehlt, blenden sie über die Fähigkeiten der Senderquelle
  // und des Wiedergabewegs selbst aus.
  import Kanzel from "../spieler/Kanzel.svelte";
  import RadioAnsicht from "../components/radio/RadioAnsicht.svelte";
  import EinstellungenSeite from "../components/einstellungen/EinstellungenSeite.svelte";
  import Telefon from "../components/telefon/Telefon.svelte";
  import Kopf from "./Kopf.svelte";
  import Meldung from "./Meldung.svelte";
  import { appState, actions } from "../lib/store.svelte.js";
  import * as router from "../lib/router.js";
  import { geraet } from "../lib/geraet.svelte.js";
  import { tasteDerApp } from "./tastatur";
  import { starten as aktualisierungStarten } from "../lib/aktualisierung.svelte.js";

  const BEREICHE = ["radio", "settings"] as const;
  const TELEFON = { podcasts: false, wecker: true, backend: false };

  // Adresse und Bereich (Zurück und Vor im Browser); es gibt Radio, die Einstellungen (ohne Server: Allgemein,
  // Darstellung, Radio, Wecker und Zeitansage, RAD-11) und am Telefon den Wecker
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
  });

  // Neue Fassung erkennen; neu geladen wird nur auf Wunsch über den Hinweis (RAD-20)
  $effect(() => { aktualisierungStarten(appState); });

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
        <EinstellungenSeite bereichszahl={BEREICHE.length} />
      {:else}
        <RadioAnsicht />
      {/if}
    </main>
    <Kanzel />
  </div>
  <Meldung />
{/if}
