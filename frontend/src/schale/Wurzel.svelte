<script lang="ts">
  // Wurzel der Oberfläche: Start der Sitzung über den Appkern (Konto der Kellerwolke, Schlüssel radiohub_sitzung im
  // Browser), dann je nach Stand "App antwortet nicht", erste Einrichtung, Anmeldung mit Passwort oder Koppeln mit Code
  // (Bausteine des Appkerns) und schließlich RadioHub. Die Darstellung gilt da schon (Skript im Kopf der Startseite).
  import { onMount } from "svelte";
  import { Anmeldung, AppWeg, Einrichtung, hole, sitzung, sitzungStarten, token } from "appkern-oberflaeche";
  import App from "../App.svelte";
  import { sitzungVerbinden } from "../lib/sitzung";
  import { t } from "../lib/i18n.svelte.js";

  // Lesezugang (Keks für Ton, Bilder und Ereignisströme, die der Browser ohne eigenen Kopf holt): der Appkern richtet
  // ihn beim Anmelden ein; die Weckeransicht am Nachttisch lädt tagelang nicht neu, darum hier alle zwölf Stunden neu.
  const ZUGANG_ERNEUERN_MS = 12 * 3600 * 1000;
  const zugang = () => hole("/anmeldung/zugang", { method: "POST" });

  // Die alte Datenschicht (lib/api.js) fragt mit dem Token des Appkerns; weist der Server die Sitzung ab, prüft eine
  // Anfrage des Appkerns sie: ist sie vorbei, zeigt der Appkern die Anmeldung
  sitzungVerbinden({ token, abgewiesen: () => void zugang().catch(() => {}) });

  onMount(() => {
    void sitzungStarten();
  });

  $effect(() => {
    if (!sitzung.angemeldet) return;
    const takt = setInterval(() => void zugang().catch(() => {}), ZUGANG_ERNEUERN_MS);
    return () => clearInterval(takt);
  });
</script>

{#if !sitzung.geladen}
  <div class="rh-laedt">{t("schale.laedt")}</div>
{:else if !sitzung.app}
  <AppWeg ganz nochmal={sitzungStarten} />
{:else if sitzung.app.einrichtung_noetig}
  <Einrichtung />
{:else if !sitzung.angemeldet}
  <Anmeldung />
{:else}
  <App />
{/if}

<style>
  .rh-laedt { block-size: 100%; display: grid; place-items: center; color: var(--text-3); }
</style>
