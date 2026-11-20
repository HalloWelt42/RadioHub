<script lang="ts">
  // Einstellungen > Radio (Entwurf mockups/radio-filter/regeln.html, RAD-7): Pfad und Reiter über dem Rollfeld.
  // Ausschlussregeln, ausgeblendete Sender, Länder der Seitenleiste, Werbeerkennung und Abgleich sind neu gebaut; die
  // Kategorien bleiben die bisherigen. Der Reiter steht in der Adresse (/einstellungen/radio/<reiter>); frühere Adressen
  // (filter, sender) führen zum passenden neuen Reiter. Welche Reiter es gibt, sagt die Senderquelle (Webversion: ohne
  // Werbeerkennung, Abgleich und Kategorien, dafür Eigene Daten als Datei).
  import { t } from "../../lib/i18n.svelte.js";
  import { actions, appState } from "../../lib/store.svelte.js";
  import { senderquelle } from "../../lib/radio";
  import RegelnReiter from "../radio/einstellungen/RegelnReiter.svelte";
  import AusgeblendetReiter from "../radio/einstellungen/AusgeblendetReiter.svelte";
  import LaenderReiter from "../radio/einstellungen/LaenderReiter.svelte";
  import WerbungReiter from "../radio/einstellungen/WerbungReiter.svelte";
  import AbgleichReiter from "../radio/einstellungen/AbgleichReiter.svelte";
  import DateiReiter from "../radio/einstellungen/DateiReiter.svelte";
  import SetupKategorien from "./SetupKategorien.svelte";

  const REITER = [
    { id: "regeln", symbol: "fa-filter-circle-xmark" },
    { id: "ausgeblendet", symbol: "fa-eye-slash" },
    { id: "laender", symbol: "fa-earth-europe" },
    ...(senderquelle.faehig.werbung ? [{ id: "werbung", symbol: "fa-rectangle-ad" }] : []),
    ...(senderquelle.faehig.abgleich ? [{ id: "abgleich", symbol: "fa-arrows-rotate" }] : []),
    ...(senderquelle.faehig.kategorien ? [{ id: "kategorien", symbol: "fa-folder" }] : []),
    ...(senderquelle.faehig.datei ? [{ id: "datei", symbol: "fa-box-archive" }] : []),
  ] as const;
  const FRUEHER: Record<string, string> = { filter: "regeln", sender: "werbung" };

  const gewuenscht = $derived((appState.routeSegments as string[])[1] ?? "");
  const reiter = $derived(REITER.some((r) => r.id === gewuenscht) ? gewuenscht : FRUEHER[gewuenscht] ?? "regeln");

  // frühere und fehlende Reiter in der Adresse richtigstellen
  $effect(() => {
    if (appState.activeTab === "settings" && (appState.routeSegments as string[])[0] === "radio" && gewuenscht !== reiter) {
      actions.navigateTo(`/einstellungen/radio/${reiter}`, { replace: true });
    }
  });
</script>

<div class="rh-ohne-zoom rh-einst-haupt">
  <div class="rh-einst-kopf">
    <div class="rh-pfad"><span>{t("radio.einst.einstellungen")}</span><i class="fa-solid fa-chevron-right"></i><span>{t("radio.einst.radio")}</span></div>
    <div class="reiterleiste" role="tablist" aria-label={t("radio.einst.radio")}>
      {#each REITER as r (r.id)}
        <button type="button" role="tab" class:aktiv={reiter === r.id} aria-selected={reiter === r.id}
                onclick={() => actions.navigateTo(`/einstellungen/radio/${r.id}`)}><i class="fa-solid {r.symbol}"></i>{t(`radio.einst.reiter.${r.id}`)}</button>
      {/each}
    </div>
  </div>
  <div class="rh-einst-rollt">
    {#if reiter === "regeln"}<RegelnReiter />
    {:else if reiter === "ausgeblendet"}<AusgeblendetReiter />
    {:else if reiter === "laender"}<LaenderReiter />
    {:else if reiter === "werbung"}<WerbungReiter />
    {:else if reiter === "abgleich"}<AbgleichReiter />
    {:else if reiter === "datei"}<DateiReiter />
    {:else if reiter === "kategorien"}<section class="rh-reiter"><div class="rh-alt"><SetupKategorien /></div></section>
    {/if}
  </div>
</div>
