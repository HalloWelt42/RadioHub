<script lang="ts">
  // Einstellungen > Ablage > Datenordner (RAD-11): wo Datenbank und Puffer liegen und was belegt ist, nur zur Anzeige
  // (Pfade setzt das Ausrollen; ein Pfad aus der Oberfläche verschob früher nichts und startete mit leerer Datenbank).
  import { api } from "../../lib/api.js";
  import { t } from "../../lib/i18n.svelte.js";
  import Karte from "./Karte.svelte";

  interface Zone { path: string; label: string; used_bytes: number; free_bytes: number; total_bytes: number; file_count: number }

  let zonen = $state<Record<string, Zone> | null>(null);
  let fehler = $state("");
  $effect(() => { api.getStorageZones().then((r: { zones: Record<string, Zone> }) => (zonen = r.zones)).catch((f: Error) => (fehler = f.message)); });

  const GB = 1024 ** 3;
  const gb = (b: number) => (b / GB).toLocaleString("de-DE", { maximumFractionDigits: b < 10 * GB ? 2 : 0 });
  const db = $derived(zonen?.database);
  const puffer = $derived(zonen?.cache);
  const belegt = $derived(db ? db.total_bytes - db.free_bytes : 0);
</script>

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
