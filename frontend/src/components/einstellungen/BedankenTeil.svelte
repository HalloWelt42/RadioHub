<script lang="ts">
  // Einstellungen > Allgemein > Bedanken (RAD-11): Spendenseite und drei Adressen mit Bildcode und Kopieren.
  import { kopieren } from "appkern-oberflaeche";
  import { t } from "../../lib/i18n.svelte.js";
  import { actions } from "../../lib/store.svelte.js";
  import { SPENDENADRESSEN, SPENDENSEITE } from "../../lib/ausgabe";
  import Karte from "./Karte.svelte";

  let gewaehlt = $state<string | null>(null);
  const adresse = $derived(SPENDENADRESSEN.find((a) => a.kuerzel === gewaehlt));

  async function adresseKopieren(text: string) {
    await kopieren(text);
    actions.showToast(t("einstellungen.bedanken.kopiert"), "success");
  }
</script>

<Karte titel={t("einstellungen.bedanken.titel")} symbol="fa-heart">
  <p class="rh-still">{t("einstellungen.bedanken.text")}</p>
  <div class="rh-dank">
    <a class="knopf primaer" href={SPENDENSEITE} target="_blank" rel="noopener"><i class="fa-solid fa-mug-hot"></i>{t("einstellungen.bedanken.seite")}</a>
    {#each SPENDENADRESSEN as a (a.kuerzel)}
      <button class="knopf" type="button" class:aktiv={gewaehlt === a.kuerzel} aria-pressed={gewaehlt === a.kuerzel}
              onclick={() => (gewaehlt = gewaehlt === a.kuerzel ? null : a.kuerzel)}><i class={a.symbol}></i>{a.kuerzel}</button>
    {/each}
  </div>
  {#if adresse}
    <div class="rh-dank-adresse">
      <img src="{import.meta.env.BASE_URL}{adresse.bild}" alt="{adresse.kuerzel}: {t('einstellungen.bedanken.adresse')}" width="160" height="160" />
      <div><span class="ak-etikett">{adresse.kuerzel} · {t("einstellungen.bedanken.adresse")}</span><code class="rh-pfadwert">{adresse.adresse}</code>
        <button class="knopf" type="button" onclick={() => void adresseKopieren(adresse.adresse)}><i class="fa-solid fa-copy"></i>{t("einstellungen.bedanken.kopieren")}</button></div>
    </div>
  {/if}
</Karte>
