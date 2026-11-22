<script lang="ts">
  // Bedienung rechts im Kopf (Nutzer 22.11.2026, RAD-71): ohne Tafel, alles mit einem Klick. Ein Knopf für das Thema
  // schaltet reihum Hell, Dunkel, System und zeigt das geltende Symbol; Schrift kleiner und größer, die Sprache als Flagge (ein Klick schaltet zur nächsten vollständig übersetzten) und Abmelden. Alles sind
  // gewöhnliche Knöpfe (rund); das gewählte Thema und die gewählte Sprache tragen die Akzentfarbe. Die Vorlage wählt man
  // in den Einstellungen unter Darstellung. Die Sprache gilt für alle Geräte und wird sofort gespeichert.
  import { abmelden, ohneAnmeldung, Rueckfrage, sitzung } from "appkern-oberflaeche";
  import { darstellung, darstellungSetzen, schriftAmRand, schriftSchritt } from "../lib/darstellung.svelte";
  import { availableLanguages, currentLanguage, onLanguageChange, t } from "../lib/i18n.svelte.js";
  import { server } from "../lib/einstellungen";
  import { actions } from "../lib/store.svelte.js";
  import Flagge from "./Flagge.svelte";

  let { konto: mitKonto }: {
    /** PRO mit Anmeldung: Abmelden oder Gerät trennen */
    konto: boolean;
  } = $props();

  const THEMEN = [["hell", "fa-sun"], ["dunkel", "fa-moon"], ["system", "fa-display"]] as const;
  const themaJetzt = $derived(Math.max(0, THEMEN.findIndex(([thema]) => thema === darstellung.thema)));
  const themaDanach = $derived(THEMEN[(themaJetzt + 1) % THEMEN.length][0]);
  const SPRACHEN = availableLanguages.filter((s: { vollstaendig?: boolean }) => s.vollstaendig) as { code: string; label: string }[];

  let sprache = $state<string>(currentLanguage());
  $effect(() => onLanguageChange((code: string) => (sprache = code)));
  const spracheJetzt = $derived(SPRACHEN.find((s) => s.code === sprache) ?? SPRACHEN[0]);
  const spracheDanach = $derived(SPRACHEN[(SPRACHEN.indexOf(spracheJetzt) + 1) % SPRACHEN.length]);

  async function spracheWaehlen(code: string) {
    if (code === sprache) return;
    try {
      await server.sofortSpeichern("language", code);
    } catch (f) {
      actions.showToast((f as Error).message || t("common.fehler"), "error");
    }
  }

  // Konto: Abmelden (Passwort) sofort, ein gekoppeltes Gerät erst nach Rückfrage trennen
  const konto = $derived(sitzung.konto);
  const geraet = $derived(!!konto?.geraet);
  let fragen = $state(false);
  let laeuft = $state(false);
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

<div class="rh-kopf-bedienung">
  <button class="rund" type="button"
          title={t("schale.themaWechsel", { jetzt: t(`schale.thema_${THEMEN[themaJetzt][0]}`), danach: t(`schale.thema_${themaDanach}`) })}
          aria-label={t("schale.themaWechsel", { jetzt: t(`schale.thema_${THEMEN[themaJetzt][0]}`), danach: t(`schale.thema_${themaDanach}`) })}
          onclick={() => darstellungSetzen({ thema: themaDanach })}><i class="fa-solid {THEMEN[themaJetzt][1]}"></i></button>
  <div class="rh-kopf-gruppe" role="group" aria-label={t("schale.schrift")}>
    <button class="rund" type="button" title={t("schale.kleiner")} aria-label={t("schale.kleiner")} disabled={schriftAmRand(-1)}
            onclick={() => schriftSchritt(-1)}><i class="fa-solid fa-minus"></i></button>
    <button class="rund" type="button" title={t("schale.groesser")} aria-label={t("schale.groesser")} disabled={schriftAmRand(1)}
            onclick={() => schriftSchritt(1)}><i class="fa-solid fa-plus"></i></button>
  </div>
  {#if SPRACHEN.length > 1}
    <button class="rund" type="button" title={t("schale.spracheWechsel", { jetzt: spracheJetzt.label, danach: spracheDanach.label })}
            aria-label={t("schale.spracheWechsel", { jetzt: spracheJetzt.label, danach: spracheDanach.label })}
            onclick={() => void spracheWaehlen(spracheDanach.code)}><Flagge sprache={spracheJetzt.code} /></button>
  {/if}
  {#if mitKonto && !ohneAnmeldung()}
    {#if geraet}
      <button class="rund" type="button" title={t("schale.trennenVon", { name: konto?.name ?? "" })} aria-label={t("schale.trennen")}
              disabled={fragen} onclick={() => (fragen = true)}><i class="fa-solid fa-link-slash"></i></button>
    {:else}
      <button class="rund" type="button" title={t("schale.abmeldenVon", { name: konto?.name ?? "" })} aria-label={t("schale.abmelden")}
              disabled={laeuft} onclick={los}><i class="fa-solid fa-right-from-bracket"></i></button>
    {/if}
  {/if}
</div>
{#if fragen}
  <Rueckfrage frage={t("schale.trennenFrage")} hinweis={t("schale.trennenHinweis")} knopf={t("schale.trennen")} beschaeftigt={laeuft}
              onabbrechen={() => (fragen = false)} onja={los} />
{/if}
