<script lang="ts">
  // Einstellungen > Ablage (RAD-135): zuerst die Endablage, die Kellerwolke mit ihrem Platz; dort landet alles Dauerhafte. Darunter der
  // Datenordner (RAD-11): wo Datenbank und Zwischenstände lokal liegen und was belegt ist, nur zur Anzeige
  // (Pfade setzt das Ausrollen; ein Pfad aus der Oberfläche verschob früher nichts und startete mit leerer Datenbank).
  import { api } from "../../lib/api.js";
  import { t } from "../../lib/i18n.svelte.js";
  import Karte from "./Karte.svelte";

  interface Zone { path: string; label: string; used_bytes: number; free_bytes: number; total_bytes: number; file_count: number }

  let zonen = $state<Record<string, Zone> | null>(null);
  interface Endablage { wurzel: string; verbunden: boolean; meldung: string; frei_bytes: number | null; gesamt_bytes: number | null }
  let wolke = $state<Endablage | null>(null);
  let fehler = $state("");
  $effect(() => { api.getAblageZustand().then((r: Endablage) => (wolke = r)).catch(() => undefined); });
  $effect(() => { api.getStorageZones().then((r: { zones: Record<string, Zone> }) => (zonen = r.zones)).catch((f: Error) => (fehler = f.message)); });

  const GB = 1024 ** 3, TB = 1024 ** 4;
  const tb = (b: number) => (b / TB).toLocaleString("de-DE", { maximumFractionDigits: 1 });
  const wolkeBelegt = $derived(wolke?.gesamt_bytes && wolke.frei_bytes != null ? 1 - wolke.frei_bytes / wolke.gesamt_bytes : null);
  const gb = (b: number) => (b / GB).toLocaleString("de-DE", { maximumFractionDigits: b < 10 * GB ? 2 : 0 });
  const db = $derived(zonen?.database);
  const puffer = $derived(zonen?.cache);
  const belegt = $derived(db ? db.total_bytes - db.free_bytes : 0);
</script>

{#if wolke}
  <Karte titel={t("einstellungen.ablage.endablage")} symbol="fa-cloud" hinweis={t("einstellungen.ablage.endHinweis")}>
    {#snippet kopf()}<span class="rh-geltung fest">{wolke?.verbunden ? t("telefon.ablageVerbunden") : t("telefon.ablageGetrennt")}</span>{/snippet}
    <div class="rh-ablage">
      <code class="rh-pfadwert">{wolke.wurzel}</code>
      {#if wolke.frei_bytes != null && wolke.gesamt_bytes}
        <div class="ak-geraet rh-bestand" data-bauform="inspektor">
          <span class="ak-schraube lo" style="--dreh:20deg"></span><span class="ak-schraube ro" style="--dreh:60deg"></span>
          <span class="ak-schraube lu" style="--dreh:-40deg"></span><span class="ak-schraube ru" style="--dreh:35deg"></span>
          <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="gruen" text={tb(wolke.frei_bytes)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.tbFrei")}</span></div>
          <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={tb(wolke.gesamt_bytes)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.tbGesamt")}</span></div>
        </div>
        <div class="rh-belegung"><span style:width="{Math.max(2, Math.round((wolkeBelegt ?? 0) * 100))}%"></span></div>
      {:else if wolke.meldung}<p class="rh-still">{wolke.meldung}</p>{/if}
    </div>
  </Karte>
{/if}
<Karte titel={t("einstellungen.ablage.datenordner")} symbol="fa-hard-drive" hinweis={t("einstellungen.ablage.hinweis")}>
  {#snippet kopf()}
    <span class="rh-geltung fest" title={t("einstellungen.geltung.festHilfe")}><i class="fa-solid fa-lock"></i>{t("einstellungen.ablage.festHilfe")}</span>
  {/snippet}
  {#if fehler}<p class="rh-still">{fehler}</p>{/if}
  {#if db}
    <div class="rh-ablage">
      <code class="rh-pfadwert">{db.path}</code>
      <div class="ak-geraet rh-bestand" data-bauform="inspektor">
        <span class="ak-schraube lo" style="--dreh:10deg"></span><span class="ak-schraube ro" style="--dreh:70deg"></span>
        <span class="ak-schraube lu" style="--dreh:-30deg"></span><span class="ak-schraube ru" style="--dreh:45deg"></span>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={gb(db.used_bytes)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.gb", { name: db.label })}</span></div>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="gruen" text={gb(puffer?.used_bytes ?? 0)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.gb", { name: puffer?.label ?? "" })}</span></div>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="bernstein" text={(db.file_count).toLocaleString("de-DE")}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.dateien")}</span></div>
        <div class="rh-bestand-feld"><ak-segmente art="7" stellen="5" farbe="weiss" text={gb(db.free_bytes)}></ak-segmente><span class="ak-etikett">{t("einstellungen.ablage.frei")}</span></div>
      </div>
      <div class="rh-belegung" title={t("einstellungen.ablage.belegt", { belegt: gb(belegt), gesamt: gb(db.total_bytes) })}>
        <span style:width="{db.total_bytes ? Math.max(2, Math.round((belegt / db.total_bytes) * 100)) : 0}%"></span></div>
    </div>
  {/if}
</Karte>
