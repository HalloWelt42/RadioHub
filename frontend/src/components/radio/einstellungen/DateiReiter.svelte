<script lang="ts">
  // Reiter Eigene Daten (Webversion, RAD-4, Entscheidung 27): Favoriten, Bewertungen, Regeln, Sperren, Freigaben und
  // Länder der Seitenleiste liegen nur in diesem Browser. Sichern legt sie als Datei ab; Einspielen prüft eine Datei
  // erst, zeigt in der Rückfrage, was sie ersetzt, und übernimmt sie nur nach ausdrücklicher Bestätigung (Vorgabe 9).
  import { Rueckfrage } from "appkern-oberflaeche";
  import { t } from "../../../lib/i18n.svelte.js";
  import { actions } from "../../../lib/store.svelte.js";
  import { senderquelle } from "../../../lib/radio";
  import { zahl } from "../../../lib/radio/anzeige";
  import type { Einspielbericht } from "../../../lib/radio/quelle";

  let wahl = $state<HTMLInputElement>();
  let inhalt = $state<string | null>(null);
  let dateiname = $state("");
  let bericht = $state<Einspielbericht | null>(null);
  let arbeitet = $state(false);
  let fehler = $state("");

  const tag = () => new Date().toISOString().slice(0, 10);

  async function sichern() {
    fehler = "";
    try {
      const text = await senderquelle.sichern!();
      const adresse = URL.createObjectURL(new Blob([text], { type: "application/json" }));
      const a = document.createElement("a");
      a.href = adresse;
      a.download = `radiohub-eigene-daten-${tag()}.json`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(adresse), 1000);
      actions.showToast(t("radio.datei.gesichert"), "success");
    } catch (f) {
      fehler = (f as Error).message;
    }
  }

  async function gewaehlt(e: Event) {
    fehler = "";
    bericht = null;
    const datei = (e.currentTarget as HTMLInputElement).files?.[0];
    (e.currentTarget as HTMLInputElement).value = "";
    if (!datei) return;
    dateiname = datei.name;
    try {
      inhalt = await datei.text();
      bericht = await senderquelle.pruefen!(inhalt);
    } catch (f) {
      inhalt = null;
      fehler = t("radio.datei.ungueltig", { meldung: (f as Error).message });
    }
  }

  async function einspielen() {
    if (!inhalt) return;
    arbeitet = true;
    try {
      const b = await senderquelle.einspielen!(inhalt);
      actions.showToast(t("radio.datei.eingespielt", { n: zahl(b.favoriten), r: zahl(b.regeln) }), "success");
      inhalt = null;
      bericht = null;
    } catch (f) {
      fehler = (f as Error).message;
    } finally {
      arbeitet = false;
    }
  }

  const hinweis = $derived(bericht ? t("radio.datei.ersetzt", {
    datei: dateiname, favoriten: zahl(bericht.favoriten), bewertungen: zahl(bericht.bewertungen), regeln: zahl(bericht.regeln),
    sperren: zahl(bericht.sperren), freigaben: zahl(bericht.freigaben),
  }) : "");
</script>

<section class="rh-reiter">
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-box-archive"></i>{t("radio.datei.titel")}</h2>
      <span class="rh-still">{t("radio.datei.erklaerung")}</span></div>
    <div class="rh-knoepfe">
      <button class="knopf primaer" type="button" onclick={sichern}><i class="fa-solid fa-download"></i>{t("radio.datei.sichern")}</button>
      <button class="knopf" type="button" onclick={() => wahl?.click()}><i class="fa-solid fa-upload"></i>{t("radio.datei.einspielen")}</button>
      <input bind:this={wahl} type="file" accept="application/json,.json" hidden onchange={gewaehlt} />
    </div>
    {#if bericht}
      <Rueckfrage frage={t("radio.datei.frage")} {hinweis} knopf={t("radio.datei.ersetzen")} beschaeftigt={arbeitet}
                  onabbrechen={() => { bericht = null; inhalt = null; }} onja={einspielen} />
    {/if}
    {#if fehler}<p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{fehler}</span></p>{/if}
  </div>
</section>
