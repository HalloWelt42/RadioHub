<script lang="ts">
  // Konto in der Darstellung: wer angemeldet ist, Abmelden (Passwort) oder Gerät trennen (gekoppeltes Telefon, danach
  // neu koppeln) mit Rückfrage des Appkerns, dazu die Fassung. Abmelden und Trennen führt die Sitzung des Appkerns.
  import { abmelden, ohneAnmeldung, Rueckfrage, sitzung } from "appkern-oberflaeche";
  import { t } from "../lib/i18n.svelte.js";

  let fragen = $state(false);
  let laeuft = $state(false);
  const konto = $derived(sitzung.konto);
  const geraet = $derived(!!konto?.geraet);

  async function los() {
    laeuft = true;
    try {
      await abmelden();
    } finally {
      laeuft = false;
      fragen = false;
    }
  }
</script>

<div class="rh-wahl">
  <h3>{t("schale.konto")}</h3>
  <div class="rh-konto">
    <span class="rh-konto-name">{konto?.name ?? ""}<br /><span class="rh-still">{ohneAnmeldung() ? t("schale.ohneAnmeldung")
      : geraet ? t("schale.gekoppelt") : t("schale.mitPasswort")} · {t("schale.fassung")} {__APP_FASSUNG__}</span></span>
    {#if !ohneAnmeldung()}
      {#if geraet}
        <button class="knopf" type="button" onclick={() => (fragen = true)} disabled={fragen}><i class="fa-solid fa-link-slash"></i>{t("schale.trennen")}</button>
      {:else}
        <button class="knopf" type="button" onclick={los} disabled={laeuft}><i class="fa-solid fa-right-from-bracket"></i>{t("schale.abmelden")}</button>
      {/if}
    {/if}
    {#if fragen}
      <Rueckfrage frage={t("schale.trennenFrage")} hinweis={t("schale.trennenHinweis")} knopf={t("schale.trennen")} beschaeftigt={laeuft}
                  onabbrechen={() => (fragen = false)} onja={los} />
    {/if}
  </div>
</div>
