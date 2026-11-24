<script lang="ts">
  // Reiter Abgleich (Vorgabe 4): der Abgleich mit dem Senderverzeichnis läuft jede Nacht als Auftrag des Appkerns; hier
  // stehen der letzte Lauf und die Uhrzeit, und er lässt sich sofort anstoßen. Ein laufender Auftrag zeigt Schritt und
  // Fortschritt (die Liste aller Aufträge führt der Appkern).
  import { onMount } from "svelte";
  import { t } from "../../../lib/i18n.svelte.js";
  import { abgleichlauf as lauf } from "../../../lib/radio/abgleichlauf.svelte";

  const stand = $derived(lauf.stand);
  const auftrag = $derived(lauf.auftrag);
  const zeit = (iso: string | null) => (iso ? new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" }) : t("radio.einst.nochNie"));

  onMount(() => void lauf.laden());
</script>

<section class="rh-reiter">
  <div class="karte rh-karte">
    <div class="rh-karte-kopf"><h2><i class="fa-solid fa-arrows-rotate"></i>{t("radio.einst.abgleichTitel")}</h2>
      <span class="rh-still">{t("radio.einst.abgleichHilfe")}</span></div>
    <dl class="rh-werte">
      <dt>{t("radio.einst.letzterLauf")}</dt><dd>{stand ? zeit(stand.zuletzt) : t("radio.laedt")}{#if stand?.ueberfaellig} <span class="stand-pille warn">{t("radio.abgleichUeberfaellig")}</span>{/if}</dd>
      <dt>{t("radio.einst.uhrzeit")}</dt><dd>{stand ? (stand.uhrzeit ? t("radio.einst.jedeNacht", { uhrzeit: stand.uhrzeit }) : t("radio.einst.keineUhrzeit")) : ""}</dd>
    </dl>
    {#if auftrag}
      <div class="rh-auftrag" aria-live="polite">
        <div class="rh-auftrag-zeile"><b>{auftrag.titel}</b><span class="stand-pille" class:laeuft={lauf.offen} class:fertig={auftrag.zustand === "fertig"}
              class:warn={auftrag.zustand === "fehler"}>{t(`radio.einst.zustand.${auftrag.zustand}`)}</span></div>
        {#if lauf.offen}
          <div class="balken"><span style="width:{Math.round((auftrag.fortschritt ?? 0) * 100)}%"></span></div>
          <div class="rh-auftrag-zeile"><span>{auftrag.schritt}</span>{#if auftrag.fortschritt != null}<span class="rh-zahl">{Math.round(auftrag.fortschritt * 100)} %</span>{/if}</div>
        {:else if auftrag.fehler}<span>{auftrag.fehler}</span>{/if}
      </div>
    {/if}
    {#if lauf.fehler}<p class="hinweis-band"><i class="fa-solid fa-triangle-exclamation"></i><span>{lauf.fehler}</span></p>{/if}
    <div class="rh-knoepfe" style="margin-top:14px">
      <button class="knopf primaer" type="button" disabled={lauf.offen} onclick={() => lauf.starten()}><i class="fa-solid fa-play"></i>{t("radio.einst.jetztAbgleichen")}</button>
    </div>
  </div>
</section>
