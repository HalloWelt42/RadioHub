<script lang="ts">
  // RadioHub nach der Anmeldung: am Rechner Kopf, Bereich und Abspielleiste (Kanzel), am Telefon die eigene Ansicht
  // (quer die Weckeransicht). Radio ist neu gebaut (RAD-7), die Kanzel ebenso (RAD-8, wächst über die Marken der
  // Schriftstufen); Aufnahmen, Podcasts und Einstellungen sind die bisherigen, sie stehen in .rh-alt und wachsen mit der
  // Schriftstufe als Ganzes, bis sie neu gebaut sind (styles/bruecke.css).
  import Kanzel from "./spieler/Kanzel.svelte";
  import { tasteDerApp } from "./schale/tastatur";
  import RadioAnsicht from "./components/radio/RadioAnsicht.svelte";
  import RecordingsTab from "./components/RecordingsTab.svelte";
  import PodcastsTab from "./components/PodcastsTab.svelte";
  import SettingsTab from "./components/SettingsTab.svelte";
  import Telefon from "./components/telefon/Telefon.svelte";
  import Kopf from "./schale/Kopf.svelte";
  import Meldung from "./schale/Meldung.svelte";
  import { appState, actions } from "./lib/store.svelte.js";
  import { t } from "./lib/i18n.svelte.js";
  import { api } from "./lib/api.js";
  import * as router from "./lib/router.js";
  import { geraet } from "./lib/geraet.svelte.js";
  import { starten as aktualisierungStarten, versuchen as aktualisierungVersuchen } from "./lib/aktualisierung.svelte.js";
  import { zeit } from "./lib/telefon/zeitansage.svelte.js";

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

  // Neue Fassung erkennen und im nächsten ruhigen Moment wechseln (nie während Wiedergabe, Aufnahme oder Ansage)
  $effect(() => {
    aktualisierungStarten(appState, () => zeit.laeuft);
  });
  $effect(() => {
    void appState.isPlaying; void appState.isPaused; void appState.activeTab; void appState.routeSegments; void zeit.laeuft;
    aktualisierungVersuchen();
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
    <!-- die neue Radio-Ansicht liest die Marken direkt; nur die alten Bereiche wachsen als Ganzes (rh-alt) -->
    <main class="rh-mitte" class:rh-alt={appState.activeTab !== "radio" && appState.activeTab !== "wecker"}>
      {#if appState.activeTab === "radio" || appState.activeTab === "wecker"}
        <RadioAnsicht />
      {:else if appState.activeTab === "recordings"}
        <RecordingsTab />
      {:else if appState.activeTab === "podcasts"}
        <PodcastsTab />
      {:else if appState.activeTab === "settings"}
        <SettingsTab />
      {/if}
    </main>
    <Kanzel />
  </div>
  <Meldung />
{/if}
