<script lang="ts">
  // RadioHub nach der Anmeldung: am Rechner Kopf, Bereich und Abspielleiste (Kanzel), am Telefon die eigene Ansicht
  // (quer die Weckeransicht). Radio ist neu gebaut (RAD-7), die Kanzel ebenso (RAD-8, wächst über die Marken der
  // Schriftstufen), Podcasts, Aufnahmen mit Schnitt (RAD-17) und Einstellungen (RAD-11) auch; alle lesen die Marken
  // direkt.
  import Kanzel from "./spieler/Kanzel.svelte";
  import { tasteDerApp } from "./schale/tastatur";
  import RadioAnsicht from "./components/radio/RadioAnsicht.svelte";
  import AufnahmenAnsicht from "./components/aufnahmen/AufnahmenAnsicht.svelte";
  import PodcastAnsicht from "./components/podcast/PodcastAnsicht.svelte";
  import SettingsTab from "./components/SettingsTab.svelte";
  import Telefon from "./components/telefon/Telefon.svelte";
  import Kopf from "./schale/Kopf.svelte";
  import Meldung from "./schale/Meldung.svelte";
  import { appState, actions } from "./lib/store.svelte.js";
  import { t } from "./lib/i18n.svelte.js";
  import { api } from "./lib/api.js";
  import * as router from "./lib/router.js";
  import { geraet } from "./lib/geraet.svelte.js";
  import { starten as aktualisierungStarten } from "./lib/aktualisierung.svelte.js";
  import { werbesprungStarten } from "./spieler/werbesprung.svelte";
  import { radiowerbungStarten } from "./spieler/radiowerbung.svelte";
  import { pufferStarten } from "./spieler/puffer.svelte";

  let online = $state<boolean | null>(null);
  let ablage = $state<{ verbunden: boolean; meldung?: string } | null>(null);   // Stand der Ablage (Kellerwolke)

  // Adresse und Bereich (Zurück und Vor im Browser; alte #-Adressen und die Wurzel leitet der Router um)
  $effect(() => {
    const anfang = router.init((info: { tab: string; segments: string[] }) => {
      appState.activeTab = info.tab;
      appState.routeSegments = info.segments;
    });
    appState.activeTab = anfang.tab;
    appState.routeSegments = anfang.segments;
  });

  // Dienst erreichbar, Einstellungen des Radios, Stand der Ablage
  $effect(() => {
    api.health().then(() => {
      online = true;
      actions.initConfig();
      api.getAblage().then((a: { verbunden: boolean; meldung?: string }) => (ablage = a)).catch(() => (ablage = null));
    }).catch(() => {
      actions.showToast(t("toast.backendOffline"), "error");
      online = false;
    });
  });

  // Werbung in Folgen überspringen (RAD-32), am Rechner und am Telefon, nur in PRO
  werbesprungStarten();
  radiowerbungStarten();
  pufferStarten();

  // Neue Fassung erkennen; neu geladen wird nur auf Wunsch über den Hinweis (RAD-20)
  $effect(() => {
    aktualisierungStarten(appState);
  });

  // Interne Links in Texten (Rechtstexte) ohne Neuladen öffnen
  function internerLink(e: MouseEvent) {
    const a = (e.target as Element | null)?.closest?.("a.md-link-internal");
    if (!a || e.ctrlKey || e.metaKey || e.shiftKey) return;
    e.preventDefault();
    actions.navigateTo(a.getAttribute("href"));
  }

  // Tastatur am Rechner (lib/tastatur.ts): die Ziffern wählen die Bereiche in der Reihenfolge der Navigation
  const BEREICHE = ["radio", "recordings", "podcasts", "settings"] as const;
  function taste(e: KeyboardEvent) {
    if (!geraet.telefon) tasteDerApp(e, BEREICHE);
  }
</script>

<svelte:window onkeydown={taste} onclick={internerLink} />

{#if geraet.telefon}
  <Telefon />
{:else}
  <div class="rh-app">
    <Kopf {online} {ablage} bereiche={[...BEREICHE]} />
    <main class="rh-mitte">
      {#if appState.activeTab === "radio" || appState.activeTab === "wecker"}
        <RadioAnsicht />
      {:else if appState.activeTab === "recordings"}
        <AufnahmenAnsicht />
      {:else if appState.activeTab === "podcasts"}
        <PodcastAnsicht />
      {:else if appState.activeTab === "settings"}
        <SettingsTab bereichszahl={BEREICHE.length} />
      {/if}
    </main>
    <Kanzel />
  </div>
  <Meldung />
{/if}
