<script lang="ts">
  // RadioHub nach der Anmeldung: am Rechner Kopf, Bereich und Abspielleiste, am Telefon die eigene Ansicht (quer die
  // Weckeransicht). Radio ist neu gebaut (RAD-7); Aufnahmen, Podcasts, Einstellungen und der Spieler sind die bisherigen,
  // sie stehen in .rh-alt und wachsen mit der Schriftstufe als Ganzes, bis sie neu gebaut sind (styles/bruecke.css).
  import HiFiPlayer from "./components/HiFiPlayer.svelte";
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

  // Tastatur am Rechner: Leertaste spielt oder hält an, S beendet, Pfeile für Lautstärke und Sender, M stumm, 1 bis 4
  // wählen den Bereich. Bei laufender Aufnahme sind Anhalten, Beenden und Senderwechsel gesperrt.
  function taste(e: KeyboardEvent) {
    if (geraet.telefon) return;
    const ziel = e.target as HTMLElement;
    if (ziel.tagName === "INPUT" || ziel.tagName === "TEXTAREA" || ziel.tagName === "SELECT" || ziel.isContentEditable) return;
    const aufnahme = appState.isRecording;
    switch (e.key) {
      case " ":
        e.preventDefault();
        if (aufnahme) break;
        if (appState.playerMode === "direct") actions.stop();          // ein direkter Strom lässt sich nur beenden
        else if (appState.playerMode !== "none") actions.togglePause();
        break;
      case "s":
        if (!aufnahme && !e.ctrlKey && !e.metaKey) actions.stop();
        break;
      case "ArrowUp":
        e.preventDefault();
        actions.setVolume(Math.min(100, appState.volume + 5));
        break;
      case "ArrowDown":
        e.preventDefault();
        actions.setVolume(Math.max(0, appState.volume - 5));
        break;
      case "ArrowLeft":
        e.preventDefault();
        if (!aufnahme) actions.navigatePrev();
        break;
      case "ArrowRight":
        e.preventDefault();
        if (!aufnahme) actions.navigateNext();
        break;
      case "m":
        if (!e.ctrlKey && !e.metaKey) actions.setVolume(appState.volume > 0 ? 0 : 70);
        break;
      case "1": actions.setTab("radio"); break;
      case "2": actions.setTab("recordings"); break;
      case "3": actions.setTab("podcasts"); break;
      case "4": actions.setTab("settings"); break;
    }
  }
</script>

<svelte:window onkeydown={taste} onclick={internerLink} />

{#if geraet.telefon}
  <Telefon />
{:else}
  <div class="rh-app">
    <Kopf {online} {ablage} />
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
    <div class="rh-alt"><HiFiPlayer /></div>
  </div>
  <Meldung />
{/if}
