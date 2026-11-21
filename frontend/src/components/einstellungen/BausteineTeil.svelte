<script lang="ts">
  // Bausteine der Zeitansage in der gewählten Stimme (RAD-11): wie viele da sind und Erzeugen der fehlenden (nur wo das
  // Bauziel es kann). Nach dem Speichern einer anderen Stimme fehlen sie, bis sie erzeugt sind.
  import { zeitbausteine } from "$ziel/telefon";
  import { t } from "../../lib/i18n.svelte.js";
  import { stand as zeitStand } from "../../lib/telefon/zeitansage.svelte.js";
  import type { Bausteinstand } from "../../lib/telefon/weckerablage";

  let stand = $state<Bausteinstand | null>(null);
  let laeuft = $state(false);

  function abfragen() {
    zeitStand().then((s: Bausteinstand) => { stand = s; laeuft = !!s.erzeugung?.laeuft; if (laeuft) setTimeout(abfragen, 3000); })
      .catch(() => (stand = null));
  }
  $effect(() => { abfragen(); });

  async function erzeugen() {
    laeuft = true;
    await zeitbausteine.erzeugen();
    setTimeout(abfragen, 1500);
  }

  const da = $derived(stand ? stand.bausteine.length - stand.fehlend.length : 0);
</script>

<div class="rh-e-zeile">
  <div class="rh-e-beschreibung"><div class="rh-e-name"><b>{t("einstellungen.stimme.bausteine")}</b></div>
    <p>{t("einstellungen.stimme.bausteineHilfe")}{#if stand?.erzeugung?.meldung} <span class="rh-e-pruefung">{stand.erzeugung.meldung}</span>{/if}</p></div>
  <div class="rh-e-wert rh-bausteine">
    {#if stand}
      <ak-segmente art="7" stellen="4" farbe={stand.fehlend.length ? "bernstein" : "gruen"} text={String(da)}></ak-segmente>
      <span class="rh-still">{t("einstellungen.stimme.von", { n: stand.bausteine.length })}</span>
      {#if zeitbausteine.faehig.erzeugen}
        <button class="knopf" type="button" disabled={!stand.fehlend.length || laeuft}
                title={stand.fehlend.length ? t("einstellungen.stimme.erzeugenHilfe") : t("einstellungen.stimme.vollstaendig")} onclick={() => void erzeugen()}>
          <i class="fa-solid {laeuft ? 'fa-spinner fa-spin' : 'fa-wand-magic-sparkles'}"></i>{laeuft ? t("einstellungen.stimme.laeuft") : t("einstellungen.stimme.erzeugen")}</button>
      {/if}
    {/if}
  </div>
</div>
